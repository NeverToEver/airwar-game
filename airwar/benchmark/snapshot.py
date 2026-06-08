"""Frozen state reading of a running game.

A :class:`GameSnapshot` captures everything a test could possibly want
to assert about the game's current state.  It is intentionally a
``frozen=True`` dataclass with only primitive types -- tests should be
able to diff two snapshots with a single ``==`` and serialize them
to JSON without bespoke encoders.

Field sources are layered:

* **Always populated** (no game coupling): ``frame``, ``scene_name``,
  ``timestamp``.
* **Populated when GameScene is active**: player state, score, boss
  state, lock layers, entity counts.  These come from
  :func:`take_snapshot` which inspects the live scene via duck typing
  -- missing attributes are reported as ``None`` rather than raising.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Any


# -- Snapshot dataclass ----------------------------------------------------


@dataclass(frozen=True)
class GameSnapshot:
    """A single frame's view of the game's state.

    All fields are primitives or tuples of primitives; equality is
    structural so ``snap_a == snap_b`` Just Works.

    Attributes:
        frame: Monotonic frame counter (0-indexed from benchmark start).
        scene_name: Name of the currently active scene
            (``"welcome"``, ``"game"``, ``"pause"``, ``"death"``...).
        timestamp: Wall-clock seconds since the benchmark started.
        player_alive: ``True`` iff the player is in the ALIVE state.
        player_dying: ``True`` iff the player is in the DYING state.
        player_health: Player HP (0..max).  ``None`` if no player.
        player_max_health: Player max HP.  ``None`` if no player.
        player_position: ``(x, y)`` of the player center, or ``None``.
        player_substate: Player alive-substate name
            (``"NORMAL"``, ``"BOOSTING"``, ``"DASHING"``, ...).
        score: Current game score.  ``None`` outside GameScene.
        boss_state: Boss HSM name (``"ENTERING"``, ``"ENRAGE"``, ...).
        active_lock_layers: Tuple of active :class:`LockLayer` names.
        enemy_count: Number of active enemies.
        player_bullet_count: Number of active player bullets.
        enemy_bullet_count: Number of active enemy bullets.
        is_paused: ``True`` iff the game is paused.
        is_invincible: ``True`` iff the player is invincible.
        extra: Catch-all dict for scenario-specific fields that the
            standard snapshot doesn't cover (e.g. ammo_count, buff ids).
    """

    frame: int
    scene_name: str
    timestamp: float
    player_alive: bool | None = None
    player_dying: bool | None = None
    player_health: float | None = None
    player_max_health: float | None = None
    player_position: tuple[float, float] | None = None
    player_substate: str | None = None
    score: int | None = None
    boss_state: str | None = None
    active_lock_layers: tuple[str, ...] = field(default_factory=tuple)
    enemy_count: int | None = None
    player_bullet_count: int | None = None
    enemy_bullet_count: int | None = None
    is_paused: bool | None = None
    is_invincible: bool | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict form (positions as lists)."""
        d = asdict(self)
        if self.player_position is not None:
            d["player_position"] = list(self.player_position)
        return d

    def has_nan(self) -> bool:
        """Return ``True`` iff any numeric field is NaN/inf.

        Used by the invariant suite to catch silent numerical
        corruption (e.g. divide-by-zero in enemy spawn coordinates).
        """
        for x in (self.player_health, self.player_max_health):
            if x is not None and (math.isnan(x) or math.isinf(x)):
                return True
        if self.player_position is not None:
            for v in self.player_position:
                if math.isnan(v) or math.isinf(v):
                    return True
        for v in self.extra.values():
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                return True
        return False


# -- Snapshot capture ------------------------------------------------------


def _safe_call(obj, attr: str, *args, default=None):
    """Call ``obj.attr(*args)`` if it's callable, else read it; ``default`` on any error.

    Handles the property-vs-method ambiguity: some game attributes
    are decorated with ``@property`` (return a value) while others
    are zero-arg methods (e.g. ``paused()``).  We try the call
    first; if that fails because the value isn't callable, fall
    back to attribute access.
    """
    if obj is None:
        return default
    val = getattr(obj, attr, None)
    if val is None:
        return default
    if callable(val):
        try:
            return val(*args)
        except Exception:
            return default
    # Plain attribute / @property already resolved to a value.
    return val


def take_snapshot(game, frame: int, timestamp: float) -> GameSnapshot:
    """Capture a :class:`GameSnapshot` of the current game state.

    Reads the active scene via the scene manager; if it's a
    :class:`GameScene`, pulls player / boss / lock / bullet state.
    Otherwise returns a minimal ``scene_name``-only snapshot.

    Args:
        game: A live :class:`airwar.game.Game` instance.
        frame: Current frame index (caller-supplied).
        timestamp: Seconds since benchmark start (caller-supplied).

    Returns:
        A :class:`GameSnapshot` for the current frame.
    """
    director = getattr(game, "_director", None)
    scene_manager = getattr(director, "_scene_manager", None)
    scene_name = ""
    scene = None
    if scene_manager is not None:
        scene_name = scene_manager.get_current_scene_name() or ""
        scene = scene_manager.get_current_scene()

    # -- Player state ----------------------------------------------------
    player = getattr(scene, "player", None) if scene else None
    player_alive = _safe_call(player, "is_alive")
    player_dying = _safe_call(player, "is_dying")
    player_health = getattr(player, "health", None) if player else None
    player_max_health = getattr(player, "max_health", None) if player else None
    player_substate = _safe_call(player, "alive_substate")
    if player_substate is not None and not isinstance(player_substate, str):
        player_substate = getattr(player_substate, "name", str(player_substate))
    player_pos = None
    if player is not None and getattr(player, "rect", None) is not None:
        rect = player.rect
        player_pos = (float(rect.centerx), float(rect.centery))

    # -- Score -----------------------------------------------------------
    score = _safe_call(scene, "_get_score") if scene else None
    if score is None and getattr(scene, "game_controller", None) is not None:
        score = getattr(scene.game_controller.state, "score", None)

    # -- Boss ------------------------------------------------------------
    # Boss lives on scene.spawn_controller.boss (set by
    # SpawnController.spawn_boss).  Fall back to scene.boss for
    # back-compat with hypothetical wrappers.
    boss_state: str | None = None
    boss = None
    if scene is not None:
        spawn = getattr(scene, "spawn_controller", None)
        if spawn is not None:
            boss = getattr(spawn, "boss", None)
        if boss is None:
            boss = getattr(scene, "boss", None)
    if boss is not None:
        try:
            # The Boss class stores its state machine at ``_state``
            # (private).  Public ``state`` returns a string
            # representation; we want the enum name.
            bsm = getattr(boss, "state_machine", None) or getattr(boss, "_state", None)
            if bsm is not None and hasattr(bsm, "state"):
                raw = getattr(bsm, "state", None)
                if raw is not None:
                    boss_state = getattr(raw, "name", None) or str(raw)
            else:
                raw = _safe_call(boss, "current_state") or getattr(boss, "state", None)
                if raw is not None and not isinstance(raw, str):
                    boss_state = getattr(raw, "name", str(raw))
                else:
                    boss_state = raw
        except Exception:
            boss_state = None

    # -- Lock layers -----------------------------------------------------
    lock_layers: tuple[str, ...] = ()
    lock_mgr = getattr(scene, "_lock_manager", None) if scene else None
    if lock_mgr is not None:
        try:
            lock_layers = tuple(
                sorted(
                    (layer.name for layer in lock_mgr._locks.keys()),  # type: ignore[attr-defined]
                    key=lambda n: -ord(n[0]),
                )
            )
        except Exception:
            lock_layers = ()

    # -- Counts ----------------------------------------------------------
    # Enemies / enemy bullets live on scene.spawn_controller (the game's
    # manager that owns both lists).  Fall back to scene.enemies /
    # scene.bullet_manager for back-compat with hypothetical wrappers.
    enemy_count = None
    player_bullet_count = None
    enemy_bullet_count = None
    enemies_list = None
    enemy_bullets_list = None
    if scene is not None:
        spawn = getattr(scene, "spawn_controller", None)
        if spawn is not None:
            enemies_list = getattr(spawn, "enemies", None)
            enemy_bullets_list = getattr(spawn, "enemy_bullets", None)
        if enemies_list is None:
            enemies_list = getattr(scene, "enemies", None)
        if enemy_bullets_list is None:
            bm = getattr(scene, "bullet_manager", None)
            if bm is not None:
                enemy_bullets_list = getattr(bm, "enemy_bullets", None)
    if enemies_list is not None:
        try:
            enemy_count = sum(1 for e in enemies_list if getattr(e, "active", False))
        except Exception:
            enemy_count = None
    if scene is not None and getattr(scene, "player", None) is not None:
        bullets = _safe_call(scene.player, "get_bullets", default=())
        if bullets is not None:
            player_bullet_count = len(bullets)
    if enemy_bullets_list is not None:
        try:
            enemy_bullet_count = sum(1 for b in enemy_bullets_list if getattr(b, "active", False))
        except Exception:
            enemy_bullet_count = None

    # -- Pause / invincibility -------------------------------------------
    is_paused = _safe_call(scene, "is_paused")
    if is_paused is None:
        is_paused = _safe_call(scene, "paused")
    is_invincible = _safe_call(player, "is_phase_dash_invincible")
    if is_invincible is None and player is not None:
        is_invincible = _safe_call(player, "is_invincible")

    return GameSnapshot(
        frame=frame,
        scene_name=scene_name,
        timestamp=timestamp,
        player_alive=player_alive,
        player_dying=player_dying,
        player_health=player_health,
        player_max_health=player_max_health,
        player_position=player_pos,
        player_substate=player_substate,
        score=score,
        boss_state=boss_state,
        active_lock_layers=lock_layers,
        enemy_count=enemy_count,
        player_bullet_count=player_bullet_count,
        enemy_bullet_count=enemy_bullet_count,
        is_paused=is_paused,
        is_invincible=is_invincible,
    )
