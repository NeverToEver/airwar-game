"""Reward generation and application — buffs unlocked at score milestones."""
import random
from typing import List, Dict, Callable
from ..buffs.buff_registry import create_buff
from ..buffs.base_buff import Buff
from ..constants import GAME_CONSTANTS
from ...config import DIFFICULTY_SETTINGS


REWARD_POOL = {
    'health': [
        {'name': 'Extra Life', 'desc': '最大生命+50, 生命+30', 'icon': '生'},
        {'name': 'Regeneration', 'desc': '每秒恢复2点生命', 'icon': '回'},
        {'name': 'Lifesteal', 'desc': '击杀时恢复10%生命', 'icon': '吸'},
    ],
    'offense': [
        {'name': 'Power Shot', 'desc': '子弹伤害+25%', 'icon': '伤'},
        {'name': 'Rapid Fire', 'desc': '射速+20%', 'icon': '速'},
        {'name': 'Piercing', 'desc': '子弹穿透1个敌人', 'icon': '穿'},
        {'name': 'Spread Shot', 'desc': '一次发射3颗子弹', 'icon': '散'},
        {'name': 'Explosive', 'desc': '子弹造成30范围伤害', 'icon': '爆'},
        {'name': 'Laser', 'desc': '持续激光束攻击', 'icon': '光'},
    ],
    'defense': [
        {'name': 'Armor', 'desc': '受到伤害-15%', 'icon': '甲'},
        {'name': 'Evasion', 'desc': '+20%闪避几率', 'icon': '闪'},
    ],
    'utility': [
        {'name': 'Slow Field', 'desc': '减慢敌人20%速度', 'icon': '缓'},
        {'name': 'Boost Recovery', 'desc': '加速能量恢复+50%', 'icon': '能'},
        {'name': 'Mothership Recall', 'desc': '母舰冷却时间-50%', 'icon': '召'},
    ],
}


class RewardSystem:
    """Reward system — generates and applies milestone buff rewards.

        Manages buff levels, applies buff effects to the player, and generates
        reward options at score milestones. Tracks unlocked buffs and their
        cumulative levels.

        Attributes:
            unlocked_buffs: List of buff names the player has acquired.
            buff_levels: Dict mapping buff names to current level counts.
            active_buffs: Dict of currently active Buff instances.
        """
    REWARD_OPTIONS = 3
    EXPLOSIVE_GATING_BOSS_KILLS = 3
    MAX_RETRY_ATTEMPTS = 10
    EXTRA_LIFE_BONUS_HP = 50
    EXTRA_LIFE_HEAL = 30
    ARMOR_MULTIPLIER = 0.85
    EVASION_CHANCE = 0.2
    LIFESTEAL_FRACTION = 0.1
    EXPLOSIVE_SPLASH_FRACTION = 0.5
    def __init__(self, difficulty: str = 'medium'):
        self.unlocked_buffs: List[str] = []
        self.active_buffs: Dict[str, Buff] = {}
        self.pending_reward = None

        self._base_bullet_damage: int = 50
        self._base_fire_cooldown: int = 8
        self._base_max_health: int = 100

        self.buff_levels: Dict[str, int] = {
            'Power Shot': 0,
            'Rapid Fire': 0,
            'Piercing': 0,
            'Spread Shot': 0,
            'Explosive': 0,
            'Armor': 0,
            'Evasion': 0,
            'Laser': 0,
            'Lifesteal': 0,
            'Regeneration': 0,
            'Extra Life': 0,
            'Slow Field': 0,
            'Boost Recovery': 0,
            'Mothership Recall': 0,
        }

        self.slow_factor: float = 1.0

        settings = DIFFICULTY_SETTINGS.get(difficulty, DIFFICULTY_SETTINGS['medium'])
        self._base_bullet_damage = settings.get('bullet_damage', 50)
        self._base_max_health = settings.get('max_health', 100)

        self._buff_apply_handlers: Dict[str, Callable] = self._init_buff_apply_handlers()

    @property
    def base_bullet_damage(self) -> int:
        return self._base_bullet_damage

    @property
    def base_fire_cooldown(self) -> int:
        return self._base_fire_cooldown

    @property
    def base_max_health(self) -> int:
        return self._base_max_health

    @property
    def piercing_level(self) -> int:
        return self.buff_levels.get('Piercing', 0)

    @piercing_level.setter
    def piercing_level(self, value: int) -> None:
        self.buff_levels['Piercing'] = value

    @property
    def spread_level(self) -> int:
        return self.buff_levels.get('Spread Shot', 0)

    @spread_level.setter
    def spread_level(self, value: int) -> None:
        self.buff_levels['Spread Shot'] = value

    @property
    def laser_level(self) -> int:
        return self.buff_levels.get('Laser', 0)

    @laser_level.setter
    def laser_level(self, value: int) -> None:
        self.buff_levels['Laser'] = value

    @property
    def explosive_level(self) -> int:
        return self.buff_levels.get('Explosive', 0)

    @explosive_level.setter
    def explosive_level(self, value: int) -> None:
        self.buff_levels['Explosive'] = value

    @property
    def armor_level(self) -> int:
        return self.buff_levels.get('Armor', 0)

    @armor_level.setter
    def armor_level(self, value: int) -> None:
        self.buff_levels['Armor'] = value

    @property
    def evasion_level(self) -> int:
        return self.buff_levels.get('Evasion', 0)

    @evasion_level.setter
    def evasion_level(self, value: int) -> None:
        self.buff_levels['Evasion'] = value

    @property
    def rapid_fire_level(self) -> int:
        return self.buff_levels.get('Rapid Fire', 0)

    @rapid_fire_level.setter
    def rapid_fire_level(self, value: int) -> None:
        self.buff_levels['Rapid Fire'] = value

    def generate_options(self, boss_kill_count: int, unlocked_buffs: list) -> List[Dict]:
        options = []
        categories = list(REWARD_POOL.keys())

        # One-shot buffs: binary abilities that have no effect beyond level 1
        ONE_SHOT_BUFFS = {'Spread Shot', 'Explosive', 'Laser'}

        taken_one_shots = ONE_SHOT_BUFFS & set(self.buff_levels.keys())

        for _ in range(self.REWARD_OPTIONS):
            cat = random.choice(categories)
            rewards = REWARD_POOL[cat]

            if cat == 'offense' and boss_kill_count < self.EXPLOSIVE_GATING_BOSS_KILLS:
                rewards = [r for r in rewards if r['name'] not in ['Explosive']]

            # Filter out already-taken one-shot buffs
            available = [r for r in rewards if r['name'] not in taken_one_shots]
            if not available:
                available = rewards  # fallback if all filtered out

            reward = random.choice(available)
            attempts = 0
            while reward in options and attempts < self.MAX_RETRY_ATTEMPTS:
                reward = random.choice(available)
                attempts += 1

            options.append(reward)

        return options

    def _init_buff_apply_handlers(self) -> Dict[str, Callable]:
        return {
            'Power Shot': self._apply_power_shot,
            'Rapid Fire': self._apply_rapid_fire,
            'Piercing': self._apply_piercing,
            'Spread Shot': self._apply_spread_shot,
            'Explosive': self._apply_explosive,
            'Laser': self._apply_laser,
            'Armor': self._apply_armor,
            'Evasion': self._apply_evasion,
            'Slow Field': self._apply_slow_field,
            'Boost Recovery': self._apply_boost_recovery,
            'Mothership Recall': self._apply_mothership_recall,
            'Extra Life': self._apply_extra_life,
        }

    def _apply_power_shot(self, player) -> None:
        level = self.buff_levels.get('Power Shot', 0)
        buff = create_buff('Power Shot')
        player.bullet_damage = buff.calculate_value(self._base_bullet_damage, level)

    def _apply_rapid_fire(self, player) -> None:
        level = self.buff_levels.get('Rapid Fire', 0)
        buff = create_buff('Rapid Fire')
        player.fire_cooldown = buff.calculate_value(self._base_fire_cooldown, level)

    def _apply_piercing(self, player) -> None:
        player.pierce_count = self.buff_levels.get('Piercing', 0)

    def _apply_spread_shot(self, player) -> None:
        if self.buff_levels.get('Spread Shot', 0) == 1:
            player.activate_shotgun()

    def _apply_explosive(self, player) -> None:
        if self.buff_levels.get('Explosive', 0) == 1:
            player.activate_explosive()

    def _apply_laser(self, player) -> None:
        if self.buff_levels.get('Laser', 0) == 1:
            player.activate_laser(GAME_CONSTANTS.REWARD.LASER_DURATION)

    def _apply_armor(self, player) -> None:
        pass

    def _apply_evasion(self, player) -> None:
        pass

    def _apply_slow_field(self, player) -> None:
        self.slow_factor = 0.8

    def _apply_boost_recovery(self, player) -> None:
        buff = create_buff('Boost Recovery')
        buff.apply(player)

    def _apply_mothership_recall(self, player) -> None:
        buff = create_buff('Mothership Recall')
        buff.apply(player)

    def _apply_extra_life(self, player) -> None:
        player.max_health += self.EXTRA_LIFE_BONUS_HP
        player.health = min(player.health + self.EXTRA_LIFE_HEAL, player.max_health)

    def apply_reward(self, reward: Dict, player) -> str:
        name = reward['name']

        if name not in self.buff_levels:
            return f"获得: {name}"

        self.buff_levels[name] = self.buff_levels.get(name, 0) + 1

        try:
            buff = create_buff(name)
        except ValueError:
            return f"获得: {name}"

        if name not in self.unlocked_buffs:
            self.unlocked_buffs.append(name)
            self.active_buffs[name] = buff

        handler = self._buff_apply_handlers.get(name)
        if handler:
            handler(player)

        return buff.get_notification(self.buff_levels[name])

    def calculate_damage_taken(self, damage: int) -> int:
        if 'Armor' in self.unlocked_buffs:
            return int(damage * self.ARMOR_MULTIPLIER)
        return damage

    def try_dodge(self) -> bool:
        if 'Evasion' in self.unlocked_buffs:
            if random.random() < self.EVASION_CHANCE:
                return True
        return False

    def apply_lifesteal(self, player, kill_value: int) -> None:
        if 'Lifesteal' in self.unlocked_buffs:
            heal = int(player.max_health * self.LIFESTEAL_FRACTION)
            player.health = min(player.health + heal, player.max_health)

    def do_explosive_damage(self, enemies: list, x: int, y: int, damage: int) -> None:
        if self.explosive_level <= 0:
            return

        for enemy in enemies:
            if enemy.active:
                dist = ((enemy.rect.centerx - x) ** 2 + (enemy.rect.centery - y) ** 2) ** 0.5
                if dist < GAME_CONSTANTS.REWARD.EXPLOSION_RADIUS:
                    enemy.take_damage(int(damage * self.EXPLOSIVE_SPLASH_FRACTION))

    def get_buff_color(self, name: str) -> tuple:
        if name in self.active_buffs:
            return self.active_buffs[name].get_color()

        try:
            buff = create_buff(name)
            return buff.get_color()
        except ValueError:
            return (255, 255, 255)

    def reset(self) -> None:
        self.unlocked_buffs = []
        self.active_buffs = {}
        self.pending_reward = None

        for key in self.buff_levels:
            self.buff_levels[key] = 0

        self.slow_factor = 1.0
        self._base_bullet_damage = 50
        self._base_fire_cooldown = 8
        self._buff_apply_handlers = self._init_buff_apply_handlers()
