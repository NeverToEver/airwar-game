import random
from typing import List, Dict, Callable
from airwar.game.buffs.buff_registry import BUFF_REGISTRY, create_buff
from airwar.game.buffs.base_buff import Buff


REWARD_POOL = {
    'health': [
        {'name': 'Extra Life', 'desc': '+50 Max HP, +30 HP', 'icon': 'HP'},
        {'name': 'Regeneration', 'desc': 'Passively heal 2 HP/sec', 'icon': 'REG'},
        {'name': 'Lifesteal', 'desc': '+10% lifesteal on kill', 'icon': 'LST'},
    ],
    'offense': [
        {'name': 'Power Shot', 'desc': '+25% bullet damage', 'icon': 'DMG'},
        {'name': 'Rapid Fire', 'desc': '+20% fire rate', 'icon': 'RPD'},
        {'name': 'Piercing', 'desc': 'Bullets pierce 1 enemy', 'icon': 'PIR'},
        {'name': 'Spread Shot', 'desc': 'Fire 3 bullets at once', 'icon': 'SPD'},
        {'name': 'Explosive', 'desc': 'Bullets deal 30 AoE damage', 'icon': 'EXP'},
        {'name': 'Shotgun', 'desc': 'Fire shotgun spread', 'icon': 'SHT'},
        {'name': 'Laser', 'desc': 'Laser beam attacks', 'icon': 'LSR'},
    ],
    'defense': [
        {'name': 'Shield', 'desc': 'Block next hit', 'icon': 'SHD'},
        {'name': 'Armor', 'desc': '-15% damage taken', 'icon': 'ARM'},
        {'name': 'Evasion', 'desc': '+20% dodge chance', 'icon': 'EVD'},
        {'name': 'Barrier', 'desc': 'Gain 50 temporary HP', 'icon': 'BAR'},
    ],
    'utility': [
        {'name': 'Speed Boost', 'desc': '+15% move speed', 'icon': 'SPD'},
        {'name': 'Magnet', 'desc': '+30% score pickup range', 'icon': 'MAG'},
        {'name': 'Slow Field', 'desc': 'Slow enemies by 20%', 'icon': 'SLO'},
    ],
}


class RewardSystem:
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
            'Shotgun': 0,
            'Laser': 0,
            'Lifesteal': 0,
            'Regeneration': 0,
            'Shield': 0,
            'Extra Life': 0,
            'Barrier': 0,
            'Speed Boost': 0,
            'Magnet': 0,
            'Slow Field': 0,
        }

        self.magnet_range: int = 0
        self.slow_factor: float = 1.0

        from airwar.config import DIFFICULTY_SETTINGS
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

    def generate_options(self, cycle_count: int, unlocked_buffs: list) -> List[Dict]:
        options = []
        categories = list(REWARD_POOL.keys())

        for _ in range(3):
            cat = random.choice(categories)
            rewards = REWARD_POOL[cat]

            if cat == 'offense' and cycle_count > 2:
                rewards = [r for r in rewards if r['name'] not in ['Spread Shot']]

            reward = random.choice(rewards)
            attempts = 0
            while reward in options and attempts < 10:
                reward = random.choice(rewards)
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
            'Shotgun': self._apply_shotgun,
            'Laser': self._apply_laser,
            'Armor': self._apply_armor,
            'Evasion': self._apply_evasion,
            'Slow Field': self._apply_slow_field,
            'Extra Life': self._apply_extra_life,
            'Barrier': self._apply_barrier,
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
        if self.buff_levels.get('Spread Shot', 0) > 0:
            player.activate_shotgun()

    def _apply_explosive(self, player) -> None:
        pass

    def _apply_shotgun(self, player) -> None:
        player.activate_shotgun()

    def _apply_laser(self, player) -> None:
        player.activate_laser(180)

    def _apply_armor(self, player) -> None:
        pass

    def _apply_evasion(self, player) -> None:
        pass

    def _apply_slow_field(self, player) -> None:
        self.slow_factor = 0.8

    def _apply_extra_life(self, player) -> None:
        player.max_health += 50
        player.health = min(player.health + 30, player.max_health)

    def _apply_barrier(self, player) -> None:
        player.max_health += 50
        player.health = player.max_health

    def _increment_stat(self, stat_name: str) -> None:
        current = getattr(self, stat_name, 0)
        setattr(self, stat_name, current + 1)

    def apply_reward(self, reward: Dict, player) -> str:
        name = reward['name']

        if name not in self.buff_levels:
            return f"REWARD: {name}"

        self.buff_levels[name] = self.buff_levels.get(name, 0) + 1

        try:
            buff = create_buff(name)
        except ValueError:
            return f"REWARD: {name}"

        if name not in self.unlocked_buffs:
            self.unlocked_buffs.append(name)
            self.active_buffs[name] = buff

        handler = self._buff_apply_handlers.get(name)
        if handler:
            handler(player)

        return buff.get_notification(self.buff_levels[name])

    def calculate_damage_taken(self, damage: int) -> int:
        if 'Armor' in self.unlocked_buffs:
            return int(damage * 0.85)
        return damage

    def try_dodge(self) -> bool:
        if 'Evasion' in self.unlocked_buffs:
            dodge_chance = 0.2
            if random.random() < dodge_chance:
                return True
        return False

    def apply_lifesteal(self, player, kill_value: int) -> None:
        if 'Lifesteal' in self.unlocked_buffs:
            heal = int(player.max_health * 0.1)
            player.health = min(player.health + heal, player.max_health)

    def do_explosive_damage(self, enemies: list, x: int, y: int, damage: int) -> None:
        if self.explosive_level <= 0:
            return

        for enemy in enemies:
            if enemy.active:
                dist = ((enemy.rect.centerx - x) ** 2 + (enemy.rect.centery - y) ** 2) ** 0.5
                if dist < 60:
                    enemy.take_damage(int(damage * 0.5))

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

        self.magnet_range = 0
        self.slow_factor = 1.0
        self._base_bullet_damage = 50
        self._base_fire_cooldown = 8
        self._buff_apply_handlers = self._init_buff_apply_handlers()
