"""Homecoming coordinator — thin orchestrator over detector, sequence,
and three base-station sub-components (state, talent, resupply).

Phase 5-γ split: extracted ``HomecomingBaseState``,
:class:`BaseTalentOrchestrator`, and :class:`BaseResupplyService` from
this module. The coordinator now owns only the sequence-lifecycle
plumbing (on_requested, on_complete, on_orbital_strike,
on_departure_complete, leave_base, the lock-manager wiring, and the
failure-mode gate).
"""

from enum import Enum

from airwar.config import get_screen_height, get_screen_width
from airwar.game.constants import GAME_CONSTANTS, PlayerConstants
from airwar.game.systems.base_resupply_service import BaseResupplyService
from airwar.game.systems.base_talent_orchestrator import BaseTalentOrchestrator
from airwar.game.systems.homecoming_base_state import HomecomingBaseState
from airwar.game.systems.lock_manager import LockLayer, LockRequest


# F03 S8: explicit FailureMode enum replacing the legacy
# ``_can_request -> bool`` contract. Callers that need a reason can
# use ``_can_request_with_reason`` to receive one of these values.
class FailureMode(Enum):
    """Why a Homecoming request was rejected (or OK)."""

    OK = "ok"
    NO_CONTROLLER = "no_controller"
    NO_PLAYER = "no_player"
    NO_SEQUENCE = "no_sequence"
    BASE_PENDING = "base_pending"
    NOT_PLAYING = "not_playing"
    PAUSED = "paused"
    SEQUENCE_ACTIVE = "sequence_active"


class HomecomingCoordinator:
    """Coordinates homecoming detection, base operations, and departure.

    After Phase 5-γ, this class is a thin facade over 5 sub-components:

    - ``_detector`` / ``_sequence`` / ``_ui`` / ``_base_talent_console`` —
      injected dependencies (sequence + UI are passed in; detector +
      console are too).
    - ``_base_state`` (:class:`HomecomingBaseState`) — owns the
      ``_base_pending`` flag and the per-tick mission sync.
    - ``_talent_orchestrator`` (:class:`BaseTalentOrchestrator`) —
      owns the :class:`TalentBalanceManager` and the click → action
      dispatch table.
    - ``_resupply`` (:class:`BaseResupplyService`) — pure
      transactional logic for repair / recharge / combined refill.
    """

    PERMANENT_INVINCIBILITY_FRAMES = (
        GAME_CONSTANTS.PERSISTENCE.PERMANENT_INVINCIBILITY_FRAMES
    )  # Sentinel: effectively infinite invincibility

    def __init__(
        self,
        detector,
        sequence,
        ui,
        base_talent_console,
    ):
        self._detector = detector
        self._sequence = sequence
        self._ui = ui
        self._base_talent_console = base_talent_console

        # Phase 5-γ: extract the three base sub-components. Each takes
        # ``self`` (the coordinator) for inversion-of-control — they
        # can call back into coordinator-owned logic (e.g.
        # ``leave_base`` from the orchestrator's CONTINUE branch, or
        # ``_resupply`` from the orchestrator's RESUPPLY branch).
        self._base_state = HomecomingBaseState()
        self._talent_orchestrator = BaseTalentOrchestrator(self, base_talent_console)
        self._resupply = BaseResupplyService(self)

        # Persisted across all sub-components via ``set_save_fn``.
        self._last_save_fn = None

    # --- Public queries ---

    def is_active(self) -> bool:
        return bool(self._sequence and self._sequence.is_active())

    def is_locked(self) -> bool:
        return self.is_active() or self._base_state.is_pending()

    def is_base_pending(self) -> bool:
        return self._base_state.is_pending()

    def get_base_talent_console(self):
        return self._base_talent_console

    def get_talent_balance_manager(self):
        return self._talent_orchestrator.get_talent_balance_manager()

    def get_ui(self):
        return self._ui

    def get_detector(self):
        return self._detector

    def get_sequence(self):
        return self._sequence

    def get_missions(self):
        if self._base_talent_console:
            return self._base_talent_console.get_missions()
        return []

    # --- Property shims (Phase 5-γ backward compat) ---

    @property
    def _base_pending(self) -> bool:
        """Backward-compat shim: tests write ``coordinator._base_pending = True``.

        See :attr:`HomecomingBaseState.is_pending` for the real
        state; this property is preserved to avoid touching 5 test
        sites (see ``test_homecoming.py`` lines 384, 443, 496, 544,
        684).

        47 模糊点 F.I2 (Phase 6 §6.2): this property setter is
        **test-only**. Production code must use the public API
        :meth:`is_base_pending` to read the state and the
        :class:`HomecomingBaseState` lifecycle (``enter_base`` /
        ``exit_base``) to mutate it. Direct ``coordinator._base_pending = ...``
        writes from production code are prohibited because they
        bypass the failure-mode gate (``_can_request_with_reason``)
        and the lock-manager handshake.
        """
        return self._base_state.is_pending()

    @_base_pending.setter
    def _base_pending(self, value: bool) -> None:
        self._base_state.set_pending(bool(value))

    @property
    def _talent_balance_manager(self):
        """Backward-compat shim: tests write ``coordinator._talent_balance_manager = ...``.

        47 模糊点 F.I2 (Phase 6 §6.2): this property setter is
        **test-only**. Production code must use the public API
        :meth:`get_talent_balance_manager` to read the manager. The
        manager is created lazily by
        :meth:`BaseTalentOrchestrator.ensure_talent_balance_manager`
        during the homecoming on-complete callback; direct
        ``coordinator._talent_balance_manager = ...`` writes from
        production code are prohibited because they bypass the
        reward-system dependency injection.
        """
        return self._talent_orchestrator._talent_balance_manager

    @_talent_balance_manager.setter
    def _talent_balance_manager(self, value) -> None:
        self._talent_orchestrator._talent_balance_manager = value

    # --- Update ---

    def update(
        self,
        game_controller,
        player,
        lock_manager,
        bullet_manager,
        spawn_controller,
        game_loop_manager,
        notification_manager,
    ):
        if not self._detector or not self._sequence:
            return

        if self._sequence.is_active():
            self._sequence.update(player)
            if player and self._sequence.is_active():
                self._set_protection(True, lock_manager, game_controller)
            return

        can_use = self._can_request(game_controller, player)
        self._detector.update(GAME_CONSTANTS.TIMING.FIXED_DELTA_TIME, enabled=can_use)

        if self._ui:
            if self._detector.is_active():
                self._ui.show()
                self._ui.update_progress(self._detector.get_progress())
            else:
                self._ui.hide()

    def update_base(self, game_controller, notification_manager):
        """Update base console and claim completed mission rewards."""
        return self._base_state.update_base(game_controller, self._base_talent_console, notification_manager)

    def sync_mission_progress(self, game_controller, survival_frames):
        """Keep mission progress in sync with actual game state."""
        return self._base_state.sync_mission_progress(game_controller, self._base_talent_console, survival_frames)

    # --- Callbacks ---

    def on_requested(self, game_controller, player, lock_manager, bullet_manager, notification_manager):
        if not self._can_request(game_controller, player):
            return
        if self._ui:
            self._ui.hide()
        if bullet_manager:
            bullet_manager.clear_enemy_bullets(include_clear_immune=True)
        if player:
            for bullet in player.get_bullets():
                bullet.active = False
            player.cleanup_inactive_bullets()
        self._set_protection(True, lock_manager, game_controller)
        started = self._sequence.start(player, get_screen_width(), get_screen_height())
        if started and notification_manager:
            notification_manager.show("返航航线已锁定")

    def on_complete(self, game_controller, player, lock_manager, notification_manager, reward_system):
        self._base_state.enter_base()
        self._talent_orchestrator.ensure_talent_balance_manager(reward_system)
        self._set_protection(True, lock_manager, game_controller)
        if notification_manager:
            notification_manager.show("已进入基地整备")

    def on_orbital_strike(self, spawn_controller, game_loop_manager, player, notification_manager):
        self._clear_hostiles(spawn_controller, game_loop_manager, player)
        if notification_manager:
            notification_manager.show("轨道导弹清场完成")

    def on_departure_complete(
        self, game_controller, player, lock_manager, spawn_controller, game_loop_manager, notification_manager
    ):
        self._base_state.exit_base()
        if self._sequence:
            self._sequence.reset()
        if self._detector:
            self._detector.reset()
        if self._ui:
            self._ui.hide()
        self._set_protection(False, lock_manager, game_controller)
        self._start_return_entrance(game_controller, player, lock_manager)
        if notification_manager:
            notification_manager.show("已返回战场")

    # --- Base operations (forwarders) ---

    def repair_at_base(self, game_controller, player, notification_manager):
        return self._resupply.repair_at_base(game_controller, player, notification_manager)

    def recharge_at_base(self, game_controller, player, notification_manager):
        return self._resupply.recharge_at_base(game_controller, player, notification_manager)

    def resupply_at_base(self, game_controller, player, notification_manager):
        return self._resupply.resupply_at_base(game_controller, player, notification_manager)

    def handle_console_click(
        self,
        pos,
        game_controller,
        player,
        lock_manager,
        spawn_controller,
        game_loop_manager,
        notification_manager,
        reward_system,
    ):
        return self._talent_orchestrator.handle_console_click(
            pos,
            game_controller,
            player,
            lock_manager,
            spawn_controller,
            game_loop_manager,
            notification_manager,
            reward_system,
        )

    def leave_base(
        self, game_controller, player, lock_manager, spawn_controller, game_loop_manager, notification_manager
    ):
        self._talent_orchestrator._invoke_save()
        self._base_state.exit_base()
        if self._ui:
            self._ui.hide()
        self._set_protection(True, lock_manager, game_controller)
        started = False
        if self._sequence:
            started = self._sequence.start_departure(
                player,
                get_screen_width(),
                get_screen_height(),
                on_complete_callback=lambda: self.on_departure_complete(
                    game_controller, player, lock_manager, spawn_controller, game_loop_manager, notification_manager
                ),
                on_orbital_strike_callback=lambda: self.on_orbital_strike(
                    spawn_controller, game_loop_manager, player, notification_manager
                ),
            )
        if not started:
            self.on_departure_complete(
                game_controller, player, lock_manager, spawn_controller, game_loop_manager, notification_manager
            )
            return
        if notification_manager:
            notification_manager.show("基地弹射程序启动")

    def _handle_action(
        self,
        action,
        game_controller,
        player,
        lock_manager,
        spawn_controller,
        game_loop_manager,
        notification_manager,
        reward_system,
    ):
        """Backward-compat forwarder (test-only).

        Test code in ``test_homecoming.py`` calls
        ``coordinator._handle_action(...)`` directly. After Phase 5-γ
        the real dispatcher lives on
        :attr:`_talent_orchestrator`.
        """
        return self._talent_orchestrator._handle_action(
            action,
            game_controller,
            player,
            lock_manager,
            spawn_controller,
            game_loop_manager,
            notification_manager,
            reward_system,
        )

    def set_save_fn(self, fn):
        """Set the save function for base loadout persistence.

        Forwards to :meth:`BaseTalentOrchestrator.set_save_fn` and
        :meth:`BaseResupplyService.set_save_fn` so each sub-component
        can persist independently.
        """
        self._last_save_fn = fn
        self._talent_orchestrator.set_save_fn(fn)
        self._resupply.set_save_fn(fn)

    # --- Private helpers (stay on coordinator) ---

    def _can_request(self, game_controller, player) -> bool:
        """Backward-compatible bool wrapper around :meth:`_can_request_with_reason`.

        Returns True if the homecoming request can be issued. For
        diagnostics, prefer the reason-returning variant.
        """
        return self._can_request_with_reason(game_controller, player) == FailureMode.OK

    def _can_request_with_reason(self, game_controller, player) -> FailureMode:
        """F03 S8: Return :class:`FailureMode` describing why a request is
        rejected (or ``FailureMode.OK`` when allowed).

        Use this in preference to ``_can_request`` when a diagnostic
        log or user-facing message is needed.
        """
        if not game_controller:
            return FailureMode.NO_CONTROLLER
        if not player:
            return FailureMode.NO_PLAYER
        if not self._sequence:
            return FailureMode.NO_SEQUENCE
        if self._base_state.is_pending():
            return FailureMode.BASE_PENDING
        if not game_controller.is_playing():
            return FailureMode.NOT_PLAYING
        if game_controller.state.is_paused:
            return FailureMode.PAUSED
        if self._sequence and self._sequence.is_active():
            return FailureMode.SEQUENCE_ACTIVE
        return FailureMode.OK

    def _set_protection(self, locked, lock_manager, game_controller):
        if not lock_manager:
            return
        if game_controller:
            lock_manager.set_game_state(game_controller.state)
        if locked:
            lock_manager.acquire(
                LockLayer.HOMECOMING,
                LockRequest(
                    invincible=True,
                    lock_controls=True,
                    is_paused=True,
                    is_silent_invincible=True,
                    invincibility_duration=self.PERMANENT_INVINCIBILITY_FRAMES,
                ),
            )
        else:
            lock_manager.release(LockLayer.HOMECOMING)

    def _start_return_entrance(self, game_controller, player, lock_manager):
        if not game_controller or not player:
            return
        # F01 F9: route through the explicit API instead of writing
        # ``state.is_entrance_playing = True`` directly.
        game_controller.start_entrance_animation()
        if lock_manager:
            lock_manager.set_game_state(game_controller.state)
            if player:
                lock_manager.set_player(player)
            lock_manager.apply_transient_state(
                paused=False,
                invincible=True,
                invincibility_duration=GAME_CONSTANTS.PLAYER.INVINCIBILITY_DURATION,
                silent_invincible=False,
            )
        player.rect.x = get_screen_width() // 2 - PlayerConstants.INITIAL_X_OFFSET
        player.rect.y = PlayerConstants.INITIAL_Y

    def _clear_hostiles(self, spawn_controller, game_loop_manager, player):
        if not spawn_controller:
            return
        for enemy in spawn_controller.enemies:
            if getattr(enemy, "active", False) and game_loop_manager:
                game_loop_manager.trigger_boss_death_explosion(
                    enemy.rect.centerx,
                    enemy.rect.centery,
                    max(28, int(enemy.rect.width * 0.7)),
                    max(28, int(enemy.rect.height * 0.7)),
                )
            enemy.active = False
        spawn_controller.enemies.clear()

        boss = spawn_controller.boss
        if boss:
            if game_loop_manager:
                game_loop_manager.trigger_boss_death_explosion(
                    boss.rect.centerx, boss.rect.centery, boss.rect.width, boss.rect.height
                )
            boss.active = False
            spawn_controller.boss = None
            if hasattr(spawn_controller, "reset_boss_timer"):
                spawn_controller.reset_boss_timer()

        if player:
            for bullet in player.get_bullets():
                bullet.active = False
            player.cleanup_inactive_bullets()
