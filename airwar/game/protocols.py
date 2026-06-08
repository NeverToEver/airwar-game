"""Shared Protocol definitions for game managers.

Canonical Protocols for dependency injection across BulletManager,
BossManager, MilestoneManager, UIManager, GameLoopManager, etc.
Each file should import from here instead of defining its own copy.

Phase 2 also adds cross-layer contracts used by the UI and the
entities (input source, buff factory, game-constants view). See the
"Cross-layer contracts" section near the bottom.
"""

from collections.abc import Callable
from typing import Protocol, runtime_checkable


class PlayerProtocol(Protocol):
    """Player interface used across all managers."""

    def update(self) -> None: ...
    def auto_fire(self) -> None: ...
    def cleanup_inactive_bullets(self) -> None: ...
    def get_bullets(self) -> list: ...
    def remove_bullet(self, bullet) -> None: ...
    def get_weapon_status(self) -> dict: ...
    def get_boost_status(self) -> dict: ...

    bullet_damage: float
    fire_interval: int
    is_controls_locked: bool
    health: int
    max_health: int

    @property
    def active(self) -> bool: ...


class GameControllerProtocol(Protocol):
    """Game controller interface used across managers."""

    @property
    def state(self): ...
    def is_playing(self) -> bool: ...
    def update(self, player, has_regen: bool) -> None: ...
    def on_enemy_killed(self, score: int) -> None: ...
    def on_boss_killed(self, score: int) -> None: ...
    def show_notification(self, message: str) -> None: ...
    def get_next_threshold(self) -> float: ...
    def get_next_progress(self) -> int: ...
    @property
    def difficulty_manager(self): ...


class GameRendererProtocol(Protocol):
    """Game renderer interface used by GameLoopManager and UIManager."""

    def render(self, surface, state, entities) -> None: ...
    def update_death_animation(self) -> None: ...


class SpawnControllerProtocol(Protocol):
    """Spawn controller interface used by GameLoopManager and BulletManager."""

    def update(self, score: int, slow_factor: float, player_pos: tuple | None = None) -> bool: ...
    def balance_for_player_dps(self, player_dps: float) -> None: ...
    def spawn_boss(self, cycle_count: int, bullet_damage: float, player_dps: float | None = None): ...
    def cleanup(self) -> None: ...
    @property
    def enemies(self) -> list: ...
    @property
    def boss(self): ...
    @property
    def enemy_bullets(self) -> list: ...


class RewardSystemProtocol(Protocol):
    """Reward system interface used across managers."""

    @property
    def slow_factor(self) -> float: ...
    @property
    def unlocked_buffs(self) -> list[str]: ...
    @property
    def explosive_level(self) -> int: ...
    @property
    def piercing_level(self) -> int: ...
    def apply_lifesteal(self, player, score: int) -> None: ...


class BulletManagerProtocol(Protocol):
    """Bullet manager interface used by GameLoopManager."""

    def update_all(self) -> None: ...
    def cleanup(self) -> None: ...
    def clear_enemy_bullets(self, include_clear_immune: bool = False) -> None: ...


class BossManagerProtocol(Protocol):
    """Boss manager interface used by GameLoopManager."""

    def update(self, player) -> None: ...
    def on_boss_hit(self, score: int) -> None: ...
    def on_boss_killed(self) -> None: ...
    @property
    def boss(self): ...


class CollisionControllerProtocol(Protocol):
    """Collision controller interface used by GameLoopManager."""

    def check_all_collisions(self, **kwargs) -> None: ...
    def set_explosion_callback(self, callback) -> None: ...


class RewardSelectorProtocol(Protocol):
    """Protocol for reward selector input methods."""

    def handle_input(self, event) -> None: ...
    @property
    def visible(self) -> bool: ...


class GiveUpDetectorProtocol(Protocol):
    """Protocol for give-up detector methods."""

    def update(self, delta: float) -> None: ...
    def is_active(self) -> bool: ...
    def get_progress(self) -> float: ...


class GiveUpUIProtocol(Protocol):
    """Protocol for give-up UI methods."""

    def show(self) -> None: ...
    def hide(self) -> None: ...
    def update_progress(self, progress: float) -> None: ...
    def render(self, surface) -> None: ...


# ---------------------------------------------------------------------------
# Cross-layer contracts (Phase 2)
#
# These break the entity/config/ui -> game.systems / game.constants
# dependency cycle by giving the lower layers a structural contract to
# depend on instead of a concrete import.
# ---------------------------------------------------------------------------


@runtime_checkable
class InputSourceProtocol(Protocol):
    """Duck-typed input source for the player.

    The :class:`airwar.entities.player.Player` only needs to read input
    state; it should not need to know whether the source is the live
    Pygame handler, a recording, or a unit-test stub. The real
    :class:`airwar.input.input_handler.PygameInputHandler` already
    matches this protocol structurally.
    """

    def get_movement_direction(self): ...
    def is_pause_pressed(self) -> bool: ...
    def is_boost_pressed(self) -> bool: ...
    def is_boost_just_pressed(self) -> bool: ...
    def is_precision_pressed(self) -> bool: ...
    def is_precision_just_pressed(self) -> bool: ...


@runtime_checkable
class BuffFactoryProtocol(Protocol):
    """Single-method protocol — the UI only needs ``create_buff(name)``."""

    def __call__(self, name: str) -> object: ...


# Convenience callable alias for the common case.
BuffFactory = Callable[[str], object]


@runtime_checkable
class RequisitionConstantsProtocol(Protocol):
    """Subset of ``GAME_CONSTANTS.REQUISITION`` accessed by the UI."""

    REPAIR_COST: int
    RECHARGE_COST: int


@runtime_checkable
class GameConstantsProtocol(Protocol):
    """Subset of ``GAME_CONSTANTS`` accessed by the UI."""

    REQUISITION: RequisitionConstantsProtocol


@runtime_checkable
class DifficultyManagerProtocol(Protocol):
    """Subset of ``DifficultyManager`` accessed by the UI panel."""

    def get_current_difficulty(self) -> object: ...


# ---------------------------------------------------------------------------
# F06 I3 / Phase 5-α: GameSceneProtocol split into 8 focused sub-protocols
#
# The historical ``GameSceneProtocol`` mixed 8 unrelated concerns
# (score / cycle / pause / buffs / difficulty / player access /
# notifications / homecoming / lifecycle). Tests that only need one
# domain were forced to mock the whole surface. Each sub-protocol is
# now its own ``@runtime_checkable`` contract so a fake can implement
# only what it uses. ``GameSceneProtocol`` itself is preserved as a
# union of the 8 sub-protocols for callers/tests that want the full
# GameScene contract.
#
# Zero behavioral change: the original protocol had no production
# caller and was never imported by any test. The split is a pure
# refactor of the contract definition.
# ---------------------------------------------------------------------------


@runtime_checkable
class IScoreProvider(Protocol):
    """Score / kill-count surface of GameScene."""

    def set_score(self, value: int) -> None: ...
    def add_score(self, amount: int) -> None: ...
    def add_kill(self) -> None: ...
    def add_boss_kill(self) -> None: ...
    def get_kill_count(self) -> int: ...
    def get_boss_kill_count(self) -> int: ...


@runtime_checkable
class ICycleProvider(Protocol):
    """Cycle counter and save/load surface of GameScene."""

    def set_cycle_count(self, value: int) -> None: ...
    def restore_from_save(self, save_data) -> None: ...
    def create_save_data(self): ...
    def is_game_over(self) -> bool: ...


@runtime_checkable
class IPauseProvider(Protocol):
    """Pause / resume surface of GameScene."""

    def pause(self) -> None: ...
    def resume(self) -> None: ...
    def paused(self) -> bool: ...
    def consume_pause_request(self) -> bool: ...


@runtime_checkable
class IBuffProvider(Protocol):
    """Unlocked-buff surface of GameScene."""

    def unlocked_buffs(self) -> list: ...


@runtime_checkable
class IDifficultyProvider(Protocol):
    """Difficulty get/set surface of GameScene."""

    def set_difficulty(self, value: str) -> None: ...
    def difficulty(self) -> str: ...


@runtime_checkable
class IPlayerAccessProvider(Protocol):
    """Player / boss / enemy accessor surface of GameScene."""

    def player(self) -> object: ...
    def get_boss(self): ...
    def get_enemies(self) -> list: ...
    def clear_boss(self) -> None: ...


@runtime_checkable
class INotificationProvider(Protocol):
    """Notification surface of GameScene."""

    def show_notification(self, message: str) -> None: ...


@runtime_checkable
class IHomecomingProvider(Protocol):
    """Homecoming / mothership query surface of GameScene."""

    def is_homecoming_active(self) -> bool: ...
    def is_homecoming_locked(self) -> bool: ...
    def is_homecoming_complete(self) -> bool: ...
    def event_bus(self) -> object: ...
    def is_mothership_docked(self) -> bool: ...


@runtime_checkable
class IGameLifecycleProvider(Protocol):
    """Scene-lifecycle surface (update / render / events / enter / exit)."""

    def update(self, *args, **kwargs) -> None: ...
    def render(self, surface) -> None: ...
    def handle_events(self, event) -> None: ...
    def enter(self, **kwargs) -> None: ...
    def exit(self) -> None: ...


@runtime_checkable
class GameSceneProtocol(
    IScoreProvider,
    ICycleProvider,
    IPauseProvider,
    IBuffProvider,
    IDifficultyProvider,
    IPlayerAccessProvider,
    INotificationProvider,
    IHomecomingProvider,
    IGameLifecycleProvider,
    Protocol,
):
    """Full structural protocol for the public surface of GameScene.

    Composes 8 focused sub-protocols (``IScoreProvider``,
    ``ICycleProvider``, ``IPauseProvider``, ``IBuffProvider``,
    ``IDifficultyProvider``, ``IPlayerAccessProvider``,
    ``INotificationProvider``, ``IHomecomingProvider``,
    ``IGameLifecycleProvider``). Tests that only need one domain
    should depend on the sub-protocol directly so the mock surface
    stays narrow; depend on ``GameSceneProtocol`` only when the full
    GameScene contract is required.
    """


# Real class attributes so ``hasattr(GameSceneProtocol, 'score')`` returns True.
# Kept on the union so both forms (``getattr(GameSceneProtocol, 'score')`` and
# isinstance checks via the sub-protocols) continue to work.
GameSceneProtocol.score = 0
GameSceneProtocol.cycle_count = 0
GameSceneProtocol.difficulty = "medium"
GameSceneProtocol.unlocked_buffs = []


# ---------------------------------------------------------------------------
# F06 I4: LockRequestProtocol — runtime_checkable contract for LockRequest
# ---------------------------------------------------------------------------


@runtime_checkable
class LockRequestProtocol(Protocol):
    """Structural contract for :class:`airwar.game.systems.lock_manager.LockRequest`.

    F06 I4: this Protocol lets the LockManager be tested with a duck-typed
    mock object (``isinstance(req, LockRequestProtocol) == True``) instead
    of having to import the concrete ``LockRequest`` dataclass.
    """

    invincible: bool
    lock_controls: bool
    is_paused: bool
    is_silent_invincible: bool
    invincibility_duration: int
