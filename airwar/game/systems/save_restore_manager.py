"""Save restore orchestration for GameScene dependencies."""

from airwar.config import BOOST_CONFIG, VALID_DIFFICULTIES, get_screen_height, get_screen_width

from ..constants import GAME_CONSTANTS, normalize_score
from .talent_balance_manager import TalentBalanceManager


class SaveRestoreManager:
    """Handles save/restore of game state via mothership persistence."""

    def __init__(self) -> None:
        self._game_controller = None
        self._player = None
        self._reward_system = None
        self._spawn_controller = None
        self._mother_ship_integrator = None

    def restore(
        self,
        save_data,
        game_controller,
        player,
        reward_system,
        spawn_controller,
        mother_ship_integrator,
    ) -> None:
        if not save_data or not game_controller or not player:
            return

        self._game_controller = game_controller
        self._player = player
        self._reward_system = reward_system
        self._spawn_controller = spawn_controller
        self._mother_ship_integrator = mother_ship_integrator

        if spawn_controller is not None:
            spawn_controller.enemies.clear()
            if hasattr(spawn_controller, "enemy_bullets"):
                spawn_controller.enemy_bullets.clear()
            if hasattr(spawn_controller, "clear_boss"):
                spawn_controller.clear_boss()
            else:
                spawn_controller.boss = None
                if hasattr(spawn_controller, "reset_boss_timer"):
                    spawn_controller.reset_boss_timer()

        game_controller.state.score = normalize_score(save_data.score)
        game_controller.state.kill_count = max(0, save_data.kill_count)
        game_controller.state.boss_kill_count = max(0, save_data.boss_kill_count)
        game_controller.state.requisition_points = max(0, getattr(save_data, "requisition_points", 0))
        game_controller.state.milestone_index = save_data.cycle_count
        game_controller.state.cycle_count = save_data.cycle_count

        # Sync difficulty BEFORE buff re-apply so base stats match the saved difficulty
        saved_diff = save_data.difficulty if save_data.difficulty in VALID_DIFFICULTIES else "medium"
        game_controller.state.difficulty = saved_diff
        game_controller.state.username = save_data.username
        game_controller.state.score_multiplier = GAME_CONSTANTS.get_difficulty_multiplier(saved_diff)

        # Re-sync difficulty-dependent subsystems to match restored difficulty
        if getattr(game_controller, "difficulty_manager", None):
            game_controller.difficulty_manager.set_difficulty(saved_diff)
        if reward_system is not None:
            reward_system.set_difficulty(saved_diff)
        if getattr(game_controller, "health_system", None):
            game_controller.health_system.set_difficulty(saved_diff)
        if spawn_controller is not None:
            spawn_controller.set_difficulty(saved_diff)

        # Sync player boost config to the restored difficulty
        boost_cfg = BOOST_CONFIG[saved_diff]
        for attr, key in (
            ("boost_max", "max_boost"),
            ("boost_current", "max_boost"),
            ("boost_recovery_rate", "recovery_rate"),
            ("boost_speed_mult", "speed_mult"),
            ("boost_recovery_delay", "recovery_delay"),
            ("boost_recovery_ramp", "recovery_ramp"),
        ):
            if hasattr(player, attr):
                setattr(player, attr, boost_cfg[key])

        # Restore difficulty scaling so enemy stats scale correctly after load
        if game_controller.difficulty_manager:
            game_controller.difficulty_manager.set_boss_kill_count(save_data.boss_kill_count)

        if reward_system is not None:
            reward_system.unlocked_buffs = save_data.unlocked_buffs
            self._restore_buff_levels(save_data.buff_levels)
            self._restore_earned_buff_levels(getattr(save_data, "earned_buff_levels", {}))
            if getattr(save_data, "talent_loadout", None):
                reward_system.talent_loadout = dict(save_data.talent_loadout)
            reward_system.capture_player_baselines(player)
        self._restore_talent_loadout_effects()
        player.health = min(max(1, save_data.player_health), player.max_health)

        if save_data.is_in_mothership:
            stay_prog = getattr(save_data, "mothership_stay_progress", 0.0)
            self._restore_to_mothership_state(stay_progress=stay_prog)
        else:
            sw = get_screen_width()
            sh = get_screen_height()
            player.rect.x = max(0, min(save_data.player_x, sw - player.rect.width))
            player.rect.y = max(0, min(save_data.player_y, sh - player.rect.height))
            # Restore COOLDOWN state if saved while cooling down
            ms_state = getattr(save_data, "mothership_state", "idle")
            cd_prog = getattr(save_data, "mothership_cooldown_progress", 0.0)
            if ms_state == "cooldown" and cd_prog > 0 and self._mother_ship_integrator:
                self._mother_ship_integrator._state_machine.restore_cooldown_state(cd_prog)

        game_controller.state.is_entrance_playing = False
        game_controller.state.entrance_timer = 0

    def _restore_buff_levels(self, buff_levels: dict) -> None:
        """Restore buff levels from save data.

        Handles both legacy short-name keys (piercing_level, etc.)
        and current proper buff names (Piercing, etc.).
        """
        if not self._reward_system or not buff_levels:
            return
        legacy_map = {
            "piercing_level": "Piercing",
            "spread_level": "Spread Shot",
            "explosive_level": "Explosive",
            "armor_level": "Armor",
            "evasion_level": "Evasion",
            "rapid_fire_level": "Rapid Fire",
        }
        for key, value in buff_levels.items():
            name = legacy_map.get(key, key)
            if name in self._reward_system.buff_levels:
                self._reward_system.buff_levels[name] = value

    def _restore_earned_buff_levels(self, earned_buff_levels: dict) -> None:
        if not self._reward_system:
            return
        if not earned_buff_levels:
            self._reward_system.earned_buff_levels = dict(self._reward_system.buff_levels)
            return
        for key, value in earned_buff_levels.items():
            if key in self._reward_system.earned_buff_levels:
                self._reward_system.earned_buff_levels[key] = max(0, int(value))

    def _restore_talent_loadout_effects(self) -> None:
        if not self._reward_system or not self._player:
            return
        if not self._reward_system.talent_loadout:
            self._reward_system.reapply_all_effects(self._player)
            return
        manager = TalentBalanceManager(
            self._reward_system.get_earned_buff_levels(),
            self._reward_system.talent_loadout,
        )
        manager.apply_to_reward_system(self._reward_system, self._player)

    def _restore_to_mothership_state(self, stay_progress: float = 0.0) -> None:
        """Restore mothership state with player docked inside."""
        if not self._player:
            return
        if self._mother_ship_integrator:
            self._mother_ship_integrator.force_docked_state(stay_progress=stay_progress)
            docking_pos = self._mother_ship_integrator.get_docking_position()
            self._player.rect.x = docking_pos[0] - self._player.rect.width // 2
            self._player.rect.y = docking_pos[1] - self._player.rect.height // 2
        else:
            screen_w = get_screen_width()
            screen_h = get_screen_height()
            self._player.rect.x = screen_w // 2 - self._player.rect.width // 2
            self._player.rect.y = screen_h // 2

    def _reapply_buff_effects(self) -> None:
        """Re-apply all buff effects after restoring levels from save."""
        if not self._reward_system or not self._player:
            return
        self._reward_system.reapply_all_effects(self._player)
