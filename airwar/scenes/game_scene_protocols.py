"""Structural protocol for the GameScene facade.

Provides a single ``GameSceneProtocol`` that captures every attribute
accessed by the GameScene subsystem split classes:

* :class:`airwar.scenes.game_scene_protocol_adapter.IGameSceneAdapter`
* :class:`airwar.scenes.game_scene_event_dispatcher.GameSceneEventDispatcher`
* :class:`airwar.scenes.game_scene_updater.GameSceneUpdater`
* :class:`airwar.scenes.scene_homecoming_dispatcher.SceneHomecomingDispatcher`

Using a protocol avoids the circular imports that would result from
importing the concrete ``GameScene`` class in those modules.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from airwar.entities import Player
    from airwar.game.managers.boss_manager import BossManager
    from airwar.game.managers.bullet_manager import BulletManager
    from airwar.game.managers.collision_controller import CollisionController
    from airwar.game.managers.game_controller import GameController
    from airwar.game.managers.game_loop_manager import GameLoopManager
    from airwar.game.managers.input_coordinator import InputCoordinator
    from airwar.game.managers.milestone_manager import MilestoneManager
    from airwar.game.managers.spawn_controller import SpawnController
    from airwar.game.managers.ui_manager import UIManager
    from airwar.game.mother_ship.event_bus import EventBus
    from airwar.game.rendering.boss_enrage_renderer import BossEnrageRenderer
    from airwar.game.rendering.game_renderer import GameRenderer
    from airwar.game.rendering.haunting_renderer import HauntingRenderer
    from airwar.game.rendering.hud_renderer import HUDRenderer
    from airwar.game.rendering.juice_renderer import JuiceController
    from airwar.game.systems.aim_assist_system import AimAssistSystem
    from airwar.game.systems.game_save_service import GameSaveService
    from airwar.game.systems.lock_manager import LockManager
    from airwar.game.systems.notification_manager import NotificationManager
    from airwar.game.systems.reward_system import RewardSystem
    from airwar.game.systems.save_restore_manager import SaveRestoreManager
    from airwar.ui.aim_crosshair import AimCrosshair
    from airwar.ui.ammo_magazine import AmmoMagazine
    from .game_scene_renderer import GameSceneRenderer
    from airwar.ui.boost_gauge import BoostGauge
    from airwar.ui.pause_button import PauseButtonComponent
    from airwar.ui.reward_selector import RewardSelector
    from airwar.ui.warning_banner import WarningBanner


class GameSceneProtocol(Protocol):
    """Structural type for the GameScene facade used by split components."""

    # Lifecycle / state flags
    running: bool
    tutorial_requested: bool
    settings_requested: bool
    want_to_quit: bool
    show_guest_confirm: bool
    show_delete_confirm: bool
    show_leaderboard: bool
    _pause_requested: bool
    _homecoming_base_pending: bool

    # Game session boundaries
    game_controller: GameController | None
    game_renderer: GameRenderer
    health_system: Any
    reward_system: RewardSystem | None
    hud_renderer: HUDRenderer | None
    notification_manager: NotificationManager | None
    spawn_controller: SpawnController
    collision_controller: CollisionController | None
    player: Player
    _bullet_manager: BulletManager
    _boss_manager: BossManager
    _milestone_manager: MilestoneManager
    _input_coordinator: InputCoordinator
    _ui_manager: UIManager
    _game_loop_manager: GameLoopManager

    # Score / cycle / difficulty
    score: int
    cycle_count: int
    difficulty: str
    unlocked_buffs: list[str]

    # Timing constants
    AUTO_SAVE_INTERVAL_SECONDS: float
    BULLET_CLEAR_DEDUP_FRAMES: int

    # Subsystems referenced by split components
    _aim_assist: AimAssistSystem
    _aim_crosshair: AimCrosshair
    _warning_banner: WarningBanner
    _boost_gauge: BoostGauge
    _ammo_magazine: AmmoMagazine
    _homecoming_coordinator: Any
    _homecoming_dispatcher: Any
    _homecoming_detector: Any
    _homecoming_sequence: Any
    _homecoming_ui: Any
    _base_talent_console: Any
    _talent_balance_manager: Any
    _mother_ship_integrator: Any
    _give_up_detector: Any
    _give_up_ui: Any
    _lock_manager: LockManager
    _haunting_renderer: HauntingRenderer | None
    _juice_controller: JuiceController
    _boss_enrage_renderer: BossEnrageRenderer
    _pause_button: PauseButtonComponent
    _save_restore_manager: SaveRestoreManager
    _save_service: GameSaveService | None
    _scene_renderer: GameSceneRenderer
    _viewport: Any

    def _is_homecoming_active(self) -> bool: ...
    reward_selector: RewardSelector
    event_bus: EventBus | None

    # Mouse interaction mixin surface used by the event dispatcher
    def handle_mouse_motion(self, pos: tuple[int, int]) -> None: ...
    def handle_mouse_click(self, pos: tuple[int, int]) -> bool: ...
    def get_hovered_button(self) -> str | None: ...

    # Facade helpers used by split components
    def _sync_player_aim_target(self) -> None: ...
    def _sync_lock_manager_targets(self) -> None: ...
    def _handle_base_console_click(self, pos: tuple[int, int]) -> bool: ...
    def _handle_button_click(self, button_name: str | None) -> None: ...
    def _update_homecoming(self, delta_seconds: float) -> None: ...
    def _get_logical_mouse_pos(self) -> tuple[float, float]: ...
    def save_snapshot(self, *, force_outside_mothership: bool = False) -> bool: ...


__all__ = ["GameSceneProtocol"]
