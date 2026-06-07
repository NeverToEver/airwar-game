"""Achievements — minimal player achievement system.

Defines an ``Achievement`` dataclass and an ``AchievementRegistry`` that
evaluates registered achievements against a ``game_state`` snapshot,
persists unlocked IDs into the existing :class:`UserDB`, and optionally
re-checks itself in response to runtime events on the shared event bus.

Design notes
------------
* Achievement conditions are plain callables ``Callable[[Mapping], bool]``
  so callers can pass any snapshot dict — typically ``GameController.state``
  fields plus a ``mothership_dock_count`` counter assembled by the caller.
* ``unlocked_at`` stores an ISO-8601 UTC timestamp string and is the
  source of truth for "already unlocked"; ``check_all`` only returns
  *newly* unlocked achievements per call to keep notifications idempotent.
* Persistence is namespaced under the user record so it shares the
  existing ``users.json`` file rather than introducing a new store.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime

from airwar.game.mother_ship.event_bus import EVENT_DOCKING_COMPLETE
from airwar.game.mother_ship.interfaces import IEventBus
from airwar.utils.database import UserDB

# Field name used to persist unlocked achievement IDs inside the user record.
USER_DATA_FIELD = "achievements"

ConditionFn = Callable[[Mapping[str, object]], bool]


@dataclass
class Achievement:
    """A single achievement with its unlock condition.

    Attributes:
        id: Stable identifier persisted to the user database.
        name_key: i18n key for the display name.
        description_key: i18n key for the description text.
        condition_fn: Predicate evaluated against a ``game_state`` mapping;
            returning ``True`` flags this achievement as unlocked.
        unlocked_at: ISO-8601 UTC timestamp set when the achievement is
            unlocked; ``None`` while still locked.
    """

    id: str
    name_key: str
    description_key: str
    condition_fn: ConditionFn = field(repr=False)
    unlocked_at: str | None = None

    @property
    def is_unlocked(self) -> bool:
        """Whether this achievement has been unlocked."""
        return self.unlocked_at is not None


class AchievementRegistry:
    """Registry that evaluates and persists achievements.

    The registry owns a set of :class:`Achievement` instances, evaluates
    them against caller-provided ``game_state`` snapshots, persists
    unlocked IDs to :class:`UserDB`, and can subscribe to a shared
    :class:`IEventBus` so external events can trigger a re-check.
    """

    def __init__(self, user_db: UserDB | None = None, user_id: str | None = None):
        self._achievements: dict[str, Achievement] = {}
        self._user_db = user_db
        self._user_id = user_id
        self._bound_bus: IEventBus | None = None

    # ---- registration --------------------------------------------------

    def register(self, achievement: Achievement) -> None:
        """Add ``achievement`` to the registry.

        Raises:
            ValueError: If an achievement with the same ID is already
                registered.
        """
        if achievement.id in self._achievements:
            raise ValueError(f"Achievement already registered: {achievement.id}")
        self._achievements[achievement.id] = achievement

    def all(self) -> list[Achievement]:
        """Return all registered achievements in insertion order."""
        return list(self._achievements.values())

    def get(self, achievement_id: str) -> Achievement | None:
        """Return the achievement with ``achievement_id`` or ``None``."""
        return self._achievements.get(achievement_id)

    def unlocked_ids(self) -> list[str]:
        """Return IDs of all currently unlocked achievements."""
        return [a.id for a in self._achievements.values() if a.is_unlocked]

    # ---- evaluation ----------------------------------------------------

    def check_all(self, game_state: Mapping[str, object]) -> list[Achievement]:
        """Evaluate every locked achievement against ``game_state``.

        Returns the list of achievements that became unlocked on this
        call. Achievements that were already unlocked are skipped, so
        repeated invocations with the same state return an empty list
        — making this safe to call once per frame.

        If a :class:`UserDB` and ``user_id`` were supplied at construction,
        the newly unlocked IDs are persisted before returning.
        """
        newly: list[Achievement] = []
        for ach in self._achievements.values():
            if ach.is_unlocked:
                continue
            try:
                triggered = bool(ach.condition_fn(game_state))
            except (KeyError, TypeError, AttributeError):
                # Tolerate partial game_state snapshots without crashing
                # the game loop — a missing field simply means the
                # condition is not yet satisfied.
                triggered = False
            if triggered:
                ach.unlocked_at = _now_iso()
                newly.append(ach)
        if newly and self._user_db is not None and self._user_id is not None:
            self.persist()
        return newly

    # ---- persistence ---------------------------------------------------

    def persist(self) -> bool:
        """Persist unlocked achievement IDs to :class:`UserDB`.

        Returns ``True`` if the database was updated, ``False`` if no
        ``UserDB`` / ``user_id`` is bound or the user record is missing.
        """
        if self._user_db is None or self._user_id is None:
            return False
        payload = {
            ach.id: ach.unlocked_at
            for ach in self._achievements.values()
            if ach.is_unlocked
        }
        return self._user_db.update_user_data(self._user_id, {USER_DATA_FIELD: payload})

    def load(self) -> int:
        """Hydrate ``unlocked_at`` from the user record.

        Returns the number of achievements restored to the unlocked state.
        Achievements present in the database but not registered are
        ignored (forward-compat with future achievement removals).
        """
        if self._user_db is None or self._user_id is None:
            return 0
        record = self._user_db.get_user_data(self._user_id) or {}
        saved = record.get(USER_DATA_FIELD) or {}
        if not isinstance(saved, dict):
            return 0
        restored = 0
        for ach_id, timestamp in saved.items():
            ach = self._achievements.get(ach_id)
            if ach is None:
                continue
            ach.unlocked_at = timestamp if isinstance(timestamp, str) else _now_iso()
            restored += 1
        return restored

    # ---- event-bus integration ----------------------------------------

    def bind_to_event_bus(self, bus: IEventBus, game_state_provider: Callable[[], Mapping[str, object]]) -> None:
        """Subscribe to runtime events that may trigger achievement checks.

        Currently subscribes to :data:`EVENT_DOCKING_COMPLETE` from the
        mothership event bus. The supplied ``game_state_provider`` is
        invoked at event time to produce a fresh snapshot for
        :meth:`check_all`. The integration is intentionally narrow —
        per-frame enemy/boss kill checks are driven by the game loop
        calling :meth:`check_all` directly, not via the bus.
        """
        self._bound_bus = bus

        def _on_docking_complete(**_kwargs: object) -> None:
            self.check_all(game_state_provider())

        bus.subscribe(EVENT_DOCKING_COMPLETE, _on_docking_complete)


# ---------------------------------------------------------------------------
# Default achievements
# ---------------------------------------------------------------------------


def _ge(field_name: str, threshold: int) -> ConditionFn:
    """Build a condition: ``game_state[field_name] >= threshold``."""

    def _check(state: Mapping[str, object]) -> bool:
        value = state.get(field_name, 0)
        return isinstance(value, (int, float)) and value >= threshold

    return _check


def default_achievements() -> list[Achievement]:
    """Return a fresh list of the built-in achievements.

    Each call returns new :class:`Achievement` instances so registries
    do not share mutable ``unlocked_at`` state.
    """
    return [
        Achievement(
            id="first_kill",
            name_key="achievement.first_kill.name",
            description_key="achievement.first_kill.desc",
            condition_fn=_ge("kill_count", 1),
        ),
        Achievement(
            id="score_1k",
            name_key="achievement.score_1k.name",
            description_key="achievement.score_1k.desc",
            condition_fn=_ge("score", 1_000),
        ),
        Achievement(
            id="score_10k",
            name_key="achievement.score_10k.name",
            description_key="achievement.score_10k.desc",
            condition_fn=_ge("score", 10_000),
        ),
        Achievement(
            id="boss_kill",
            name_key="achievement.boss_kill.name",
            description_key="achievement.boss_kill.desc",
            condition_fn=_ge("boss_kill_count", 1),
        ),
        Achievement(
            id="mothership_dock",
            name_key="achievement.mothership_dock.name",
            description_key="achievement.mothership_dock.desc",
            condition_fn=_ge("mothership_dock_count", 1),
        ),
    ]


def build_default_registry(
    user_db: UserDB | None = None,
    user_id: str | None = None,
    extras: Iterable[Achievement] = (),
) -> AchievementRegistry:
    """Return a registry pre-populated with the built-in achievements.

    Args:
        user_db: Optional database used by :meth:`AchievementRegistry.persist`.
        user_id: User record key inside ``user_db``.
        extras: Additional achievements to register after the defaults.
    """
    registry = AchievementRegistry(user_db=user_db, user_id=user_id)
    for ach in default_achievements():
        registry.register(ach)
    for ach in extras:
        registry.register(ach)
    return registry


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(UTC).isoformat(timespec="seconds")
