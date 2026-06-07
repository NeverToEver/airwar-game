"""Scene achievement bridge -- registry, event-bus subscription, and evaluation.

Extracted from :class:`airwar.game.scene_director.SceneDirector` (Phase 4 W-β).
Owns the per-run :class:`AchievementRegistry`, the in-game event-bus
subscription for :data:`EVENT_DOCKING_COMPLETE`, and the final achievement
evaluation pass at game over. Also owns user-stats updates and
leaderboard score submission (both triggered by the death flow).
"""

from __future__ import annotations

import logging

from ...scenes import GameScene
from ...utils.database import DatabaseError
from ..achievements import build_default_registry
from ..mother_ship.event_bus import EVENT_DOCKING_COMPLETE
from ..mother_ship.interfaces import IEventBus


class SceneAchievementBridge:
    """Achievement registry + event-bus subscription + final evaluation.

    All public attributes are read or mutated by the parent
    :class:`SceneDirector`; the director holds a reference to a single
    instance and forwards each achievement method to it.
    """

    def __init__(self, director) -> None:
        self._director = director
        self._logger = logging.getLogger(director.__class__.__name__)

    # -- User stats / leaderboard -----------------------------------------------

    def update_user_stats(self, score: int, kills: int) -> int | None:
        if not self._director._current_user or not self._director._user_db:
            return None
        try:
            user_data = self._director._user_db.get_user_data(self._director._current_user)
            new_high = max(score, user_data.get("high_score", 0))
            self._director._user_db.update_user_data(
                self._director._current_user,
                {
                    "high_score": new_high,
                    "total_kills": user_data.get("total_kills", 0) + kills,
                    "games_played": user_data.get("games_played", 0) + 1,
                },
            )
            return new_high
        except DatabaseError:
            self._logger.warning("Failed to update user stats", exc_info=True)
            return None

    def submit_leaderboard_score(self, score: int) -> int:
        """Record the final score on the local leaderboard.

        Args:
            score: Final score for the just-ended run.

        Returns:
            1-indexed rank if it made the top 10, otherwise ``0``. Returns
            ``0`` when no user is logged in or no database is wired up.
        """
        if not self._director._user_db:
            return 0
        name = self._director._current_user if self._director._current_user else "Guest"
        try:
            return self._director._user_db.submit_score(name, score)
        except DatabaseError:
            self._logger.warning("Failed to submit leaderboard score", exc_info=True)
            return 0

    # -- Achievement registry ---------------------------------------------------

    def create_achievement_registry(self) -> None:
        """Build the per-run :class:`AchievementRegistry` for the current user.

        No-op for guest sessions and when no :class:`UserDB` is wired up.
        On success, builds the default registry, hydrates prior unlocks
        from the user record, and subscribes to the in-game event bus
        (when accessible) so docking events can trigger a re-check.

        Database errors are logged and swallowed; a missing registry
        must never block gameplay.
        """
        if not self._director._current_user or self._director._current_user == "Guest":
            return
        if self._director._user_db is None:
            return
        try:
            registry = build_default_registry(
                user_db=self._director._user_db,
                user_id=self._director._current_user,
            )
            restored = registry.load()
            self._director._achievement_registry = registry
            self._logger.info(
                "AchievementRegistry ready for user=%s (restored=%d)",
                self._director._current_user,
                restored,
            )
        except DatabaseError:
            self._logger.warning("Failed to load achievements", exc_info=True)
            self._director._achievement_registry = None
            return

        # Subscribe to the in-game event bus if GameScene exposes one.
        # If the bus is not yet accessible (scene not initialised), the
        # dock counter still accumulates in this director and the final
        # _evaluate_achievements call at game-over will see the bumped
        # count.
        bus = self.acquire_event_bus()
        if bus is not None:
            try:
                bus.subscribe(EVENT_DOCKING_COMPLETE, self._director._on_mothership_docking_complete)
            except (ValueError, RuntimeError) as exc:  # defensive: cap reached / bus closed
                self._logger.warning("Failed to subscribe to EVENT_DOCKING_COMPLETE: %s", exc)

    def acquire_event_bus(self) -> IEventBus | None:
        """Return the active scene's event bus, or ``None`` if unavailable.

        Looks up the current scene from the scene manager and returns
        its ``event_bus`` attribute when present. Returns ``None``
        when the scene is not a :class:`GameScene` or the property
        has not been wired yet.
        """
        try:
            scene = self._director._scene_manager.get_current_scene()
        except Exception:  # defensive
            return None
        return getattr(scene, "event_bus", None)

    def on_mothership_docking_complete(self, **_kwargs: object) -> None:
        """Event-bus callback: bump the dock counter, then re-check.

        Registered on :data:`EVENT_DOCKING_COMPLETE` so the
        :class:`mothership_dock` achievement can be unlocked at
        runtime. The counter increment is what makes the
        achievement condition reachable in the first place; without
        it, the per-frame :meth:`_evaluate_achievements` pass at
        game-over would always see a zero count.
        """
        self._director._mothership_dock_count += 1
        registry = self._director._achievement_registry
        if registry is None:
            return
        try:
            registry.check_all({"mothership_dock_count": self._director._mothership_dock_count})
        except DatabaseError:
            self._logger.warning("Docking event achievement check failed", exc_info=True)

    def evaluate_achievements(self, game_scene: GameScene) -> list[str]:
        """Run the final achievement check at game over and persist.

        Aggregates the run's score, kill counts, and per-run
        mothership dock counter into a snapshot and passes it to
        the registry. Failures from a missing registry or a
        database error are logged and swallowed; the death-scene
        flow must not depend on achievement persistence.

        Returns:
            The list of achievement IDs unlocked on this call.
            Empty when no registry is wired up.
        """
        registry = self._director._achievement_registry
        if registry is None:
            return []
        snapshot = {
            "score": game_scene.score,
            "kill_count": game_scene.get_kill_count(),
            "boss_kill_count": game_scene.get_boss_kill_count(),
            "mothership_dock_count": self._director._mothership_dock_count,
        }
        try:
            newly = registry.check_all(snapshot)
        except DatabaseError:
            self._logger.warning("Failed to check achievements", exc_info=True)
            return []
        self._director._mothership_dock_count = 0
        return [a.id for a in newly]
