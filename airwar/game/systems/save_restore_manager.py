"""Save restore orchestration for GameScene dependencies."""

from airwar.config import BOOST_CONFIG, VALID_DIFFICULTIES, get_screen_height, get_screen_width
from airwar.game.constants import GAME_CONSTANTS
from airwar.game.managers.game_controller import normalize_score
from airwar.game.systems.talent_balance_manager import TalentBalanceManager


class SaveRestoreManager:
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

        game_controller.state.score = normalize_score(save_data.score)
        game_controller.state.kill_count = max(0, save_data.kill_count)
        game_controller.state.boss_kill_count = max(0, save_data.boss_kill_count)
        game_controller.state.requisition_points = max(0, getattr(save_data, 'requisition_points', 0))
        game_controller.milestone_index = save_data.cycle_count
        game_controller.cycle_count = save_data.cycle_count

        # Sync difficulty BEFORE buff re-apply so base stats match the saved difficulty
        saved_diff = save_data.difficulty if save_data.difficulty in VALID_DIFFICULTIES else 'medium'
        game_controller.state.difficulty = saved_diff
        game_controller.state.username = save_data.username
        game_controller.state.score_multiplier = GAME_CONSTANTS.get_difficulty_multiplier(saved_diff)

        # Re-sync difficulty-dependent subsystems to match restored difficulty
        game_controller.difficulty_manager.set_difficulty(saved_diff)
        game_controller.reward_system.set_difficulty(saved_diff)
        game_controller.health_system.set_difficulty(saved_diff)
        spawn_controller.set_difficulty(saved_diff)

        # Sync player boost config to the restored difficulty
        boost_cfg = BOOST_CONFIG[saved_diff]
        player.boost_max = boost_cfg['max_boost']
        player.boost_current = boost_cfg['max_boost']
        player.boost_recovery_rate = boost_cfg['recovery_rate']
        player.boost_speed_mult = boost_cfg['speed_mult']
        player.boost_recovery_delay = boost_cfg['recovery_delay']
        player.boost_recovery_ramp = boost_cfg['recovery_ramp']

        # Restore difficulty scaling so enemy stats scale correctly after load
        if game_controller.difficulty_manager:
            game_controller.difficulty_manager.set_boss_kill_count(save_data.boss_kill_count)

        reward_system.unlocked_buffs = save_data.unlocked_buffs
        self._restore_buff_levels(save_data.buff_levels)
        self._restore_earned_buff_levels(getattr(save_data, "earned_buff_levels", {}))
        if getattr(save_data, "talent_loadout", None):
            reward_system.talent_loadout = dict(save_data.talent_loadout)
        reward_system.capture_player_baselines(player)
        self._restore_talent_loadout_effects()
        player.health = min(max(1, save_data.player_health), player.max_health)

        if save_data.is_in_mothership:
            self._restore_to_mothership_state()
        else:
            sw = get_screen_width()
            sh = get_screen_height()
            player.rect.x = max(0, min(save_data.player_x, sw - player.rect.width))
            player.rect.y = max(0, min(save_data.player_y, sh - player.rect.height))

        game_controller.state.entrance_animation = False
        game_controller.state.entrance_timer = 0

    def _restore_buff_levels(self, buff_levels: dict) -> None:
        """Restore buff levels from save data.

        Handles both legacy short-name keys (piercing_level, etc.)
        and current proper buff names (Piercing, etc.).
        """
        if not self._reward_system or not buff_levels:
            return
        legacy_map = {
            'piercing_level': 'Piercing', 'spread_level': 'Spread Shot',
            'explosive_level': 'Explosive', 'armor_level': 'Armor',
            'evasion_level': 'Evasion', 'rapid_fire_level': 'Rapid Fire',
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

    def _restore_to_mothership_state(self) -> None:
        """Restore mothership state with player docked inside."""
        if not self._player:
            return
        if self._mother_ship_integrator:
            self._mother_ship_integrator.force_docked_state()
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
