"""Homecoming coordinator — manages the homecoming sequence lifecycle.

Extracted from GameScene to reduce god-class responsibilities.
Handles detection, sequence, base console, talent management, departure.
"""
from airwar.config import get_screen_width, get_screen_height
from airwar.game.constants import PlayerConstants, GAME_CONSTANTS
from airwar.game.systems.talent_balance_manager import TalentBalanceManager
from airwar.game.systems.lock_manager import LockLayer, LockRequest


class HomecomingCoordinator:
    """Coordinates homecoming detection, base operations, and departure."""

    PERMANENT_INVINCIBILITY_FRAMES = 999999  # Sentinel: effectively infinite invincibility

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
        self._talent_balance_manager = None
        self._base_pending = False

    # --- Public queries ---

    def is_active(self) -> bool:
        return bool(self._sequence and self._sequence.is_active())

    def is_locked(self) -> bool:
        return self.is_active() or self._base_pending

    def is_base_pending(self) -> bool:
        return self._base_pending

    def get_base_talent_console(self):
        return self._base_talent_console

    def get_talent_balance_manager(self):
        return self._talent_balance_manager

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

    # --- Update ---

    def update(self, game_controller, player, lock_manager, bullet_manager, spawn_controller, game_loop_manager, notification_manager, save_fn=None):
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
        if not self._base_pending or not self._base_talent_console:
            return
        self._base_talent_console.update()
        for mission in self._base_talent_console.get_missions():
            if mission["done"] and not mission["claimed"]:
                game_controller.state.requisition_points += GAME_CONSTANTS.REQUISITION.MISSION_REWARD
                mission["claimed"] = True
                if notification_manager:
                    notification_manager.show(f"任务完成: {mission['name']} (+{GAME_CONSTANTS.REQUISITION.MISSION_REWARD}RP)")

    def sync_mission_progress(self, game_controller, survival_frames):
        """Keep mission progress in sync with actual game state."""
        if not self._base_talent_console or not game_controller:
            return
        for mission in self._base_talent_console.get_missions():
            if mission["target"] == "kills":
                mission["progress"] = game_controller.state.kill_count
            elif mission["target"] == "survival_time":
                mission["progress"] = survival_frames // 60
            elif mission["target"] == "boss_kills":
                mission["progress"] = game_controller.state.boss_kill_count
            mission["done"] = mission["progress"] >= mission["goal"]

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
        self._base_pending = True
        self._ensure_talent_balance_manager(reward_system)
        self._set_protection(True, lock_manager, game_controller)
        if notification_manager:
            notification_manager.show("已进入基地整备")

    def on_orbital_strike(self, spawn_controller, game_loop_manager, player, notification_manager):
        self._clear_hostiles(spawn_controller, game_loop_manager, player)
        if notification_manager:
            notification_manager.show("轨道导弹清场完成")

    def on_departure_complete(self, game_controller, player, lock_manager, spawn_controller, game_loop_manager, notification_manager):
        self._base_pending = False
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

    # --- Base operations ---

    def repair_at_base(self, game_controller, player, notification_manager):
        cost = GAME_CONSTANTS.REQUISITION.REPAIR_COST
        if not player or not game_controller:
            return
        if game_controller.state.requisition_points < cost:
            return
        if player.health >= player.max_health:
            return
        game_controller.state.requisition_points -= cost
        player.health = player.max_health
        self._save_base_loadout()
        if notification_manager:
            notification_manager.show(f"机体维修完成 (-{cost}RP)")

    def recharge_at_base(self, game_controller, player, notification_manager):
        cost = GAME_CONSTANTS.REQUISITION.RECHARGE_COST
        if not player or not game_controller:
            return
        if game_controller.state.requisition_points < cost:
            return
        if player.boost_current >= player.boost_max:
            return
        game_controller.state.requisition_points -= cost
        player.boost_current = player.boost_max
        self._save_base_loadout()
        if notification_manager:
            notification_manager.show(f"加速燃料补给完成 (-{cost}RP)")

    def resupply_at_base(self, game_controller, player, notification_manager):
        if not player or not game_controller:
            return
        need_health = player.health < player.max_health
        need_boost = hasattr(player, "boost_current") and player.boost_current < player.boost_max
        if not need_health and not need_boost:
            if notification_manager:
                notification_manager.show("机体和燃料已全满，无需补给")
            return
        actual_cost = 0
        if need_health:
            actual_cost += GAME_CONSTANTS.REQUISITION.REPAIR_COST
        if need_boost:
            actual_cost += GAME_CONSTANTS.REQUISITION.RECHARGE_COST
        if game_controller.state.requisition_points < actual_cost:
            if notification_manager:
                notification_manager.show(f"征用点数不足: 需要{actual_cost}RP")
            return
        game_controller.state.requisition_points -= actual_cost
        if need_health:
            player.health = player.max_health
        if need_boost:
            player.boost_current = player.boost_max
        self._save_base_loadout()
        if notification_manager:
            notification_manager.show(f"基地全面补给完成 (-{actual_cost}RP)")

    def handle_console_click(self, pos, game_controller, player, lock_manager, spawn_controller, game_loop_manager, notification_manager, reward_system):
        if not self._base_talent_console or not self._talent_balance_manager:
            return False
        action = self._base_talent_console.handle_mouse_click(pos)
        if action is None:
            return False
        self._handle_action(action, game_controller, player, lock_manager, spawn_controller, game_loop_manager, notification_manager, reward_system)
        return True

    def leave_base(self, game_controller, player, lock_manager, spawn_controller, game_loop_manager, notification_manager):
        self._save_base_loadout()
        self._base_pending = False
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
                    game_controller, player, lock_manager, spawn_controller, game_loop_manager, notification_manager),
                on_orbital_strike_callback=lambda: self.on_orbital_strike(
                    spawn_controller, game_loop_manager, player, notification_manager),
            )
        if not started:
            self.on_departure_complete(game_controller, player, lock_manager, spawn_controller, game_loop_manager, notification_manager)
            return
        if notification_manager:
            notification_manager.show("基地弹射程序启动")

    # --- Private helpers ---

    def _can_request(self, game_controller, player):
        if not game_controller or not player:
            return False
        if not self._sequence or self._base_pending:
            return False
        if not game_controller.is_playing():
            return False
        if game_controller.state.is_paused:
            return False
        return not (self._sequence and self._sequence.is_active())

    def _ensure_talent_balance_manager(self, reward_system):
        if not reward_system:
            return
        reward_system.ensure_earned_levels()
        self._talent_balance_manager = TalentBalanceManager(
            reward_system.get_earned_buff_levels(),
            reward_system.talent_loadout,
        )
        self._apply_talent_loadout(reward_system, None, show_notification=False)

    def _apply_talent_loadout(self, reward_system, player, show_notification=True, notification_manager=None):
        if not self._talent_balance_manager or not reward_system:
            return
        reward_system.apply_effective_levels(
            self._talent_balance_manager.effective_levels(),
            locked_buffs=self._talent_balance_manager.locked_buffs(),
            talent_loadout=self._talent_balance_manager._loadout,
        )
        if player:
            reward_system.reapply_all_effects(player)
        self._save_base_loadout()
        if show_notification and notification_manager:
            notification_manager.show("基地天赋配置已同步")

    def _handle_action(self, action, game_controller, player, lock_manager, spawn_controller, game_loop_manager, notification_manager, reward_system):
        from airwar.ui.base_talent_console import BaseTalentConsoleAction
        if action.kind == BaseTalentConsoleAction.CONTINUE:
            self.leave_base(game_controller, player, lock_manager, spawn_controller, game_loop_manager, notification_manager)
            return
        if action.kind == BaseTalentConsoleAction.RESUPPLY:
            self.resupply_at_base(game_controller, player, notification_manager)
            return
        if action.kind == BaseTalentConsoleAction.REPAIR:
            self.repair_at_base(game_controller, player, notification_manager)
            return
        if action.kind == BaseTalentConsoleAction.RECHARGE:
            self.recharge_at_base(game_controller, player, notification_manager)
            return
        if action.kind == BaseTalentConsoleAction.SELECT_MODULE:
            return
        if action.kind == BaseTalentConsoleAction.SELECT_ROUTE and action.route:
            if self._talent_balance_manager and self._talent_balance_manager.next_option(action.route) is not None:
                self._apply_talent_loadout(reward_system, player, notification_manager=notification_manager)

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
        state = game_controller.state
        state.is_entrance_playing = True
        state.entrance_timer = 0
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
                    enemy.rect.centerx, enemy.rect.centery,
                    max(28, int(enemy.rect.width * 0.7)), max(28, int(enemy.rect.height * 0.7)))
            enemy.active = False
        spawn_controller.enemies.clear()

        boss = spawn_controller.boss
        if boss:
            if game_loop_manager:
                game_loop_manager.trigger_boss_death_explosion(
                    boss.rect.centerx, boss.rect.centery, boss.rect.width, boss.rect.height)
            boss.active = False
            spawn_controller.boss = None
            if hasattr(spawn_controller, "reset_boss_timer"):
                spawn_controller.reset_boss_timer()

        if player:
            for bullet in player.get_bullets():
                bullet.active = False
            player.cleanup_inactive_bullets()

    def _save_base_loadout(self):
        if not hasattr(self, '_last_save_fn') or not self._last_save_fn:
            return False
        return self._last_save_fn()

    def set_save_fn(self, fn):
        """Set the save function for base loadout persistence."""
        self._last_save_fn = fn
