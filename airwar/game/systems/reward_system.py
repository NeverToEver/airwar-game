import random
from typing import List, Dict
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
    def __init__(self):
        self.unlocked_buffs: List[str] = []
        self.active_buffs: Dict[str, Buff] = {}
        self.pending_reward = None

        self.piercing_level: int = 0
        self.spread_level: int = 0
        self.explosive_level: int = 0
        self.armor_level: int = 0
        self.evasion_level: int = 0
        self.magnet_range: int = 0
        self.slow_factor: float = 1.0

    def generate_options(self, cycle_count: int, unlocked_buffs: list) -> List[Dict]:
        options = []
        categories = list(REWARD_POOL.keys())

        for _ in range(3):
            cat = random.choice(categories)
            rewards = REWARD_POOL[cat]

            if cat == 'offense' and cycle_count > 2:
                rewards = [r for r in rewards if r['name'] not in ['Spread Shot', 'Explosive']]

            reward = random.choice(rewards)
            attempts = 0
            while reward in options and attempts < 10:
                reward = random.choice(rewards)
                attempts += 1

            options.append(reward)

        return options

    def apply_reward(self, reward: Dict, player) -> str:
        name = reward['name']

        if name in self.unlocked_buffs:
            return self._upgrade_buff(name, player)

        try:
            buff = create_buff(name)
            result = buff.apply(player)

            self.unlocked_buffs.append(name)
            self.active_buffs[name] = buff

            if name == 'Piercing':
                self.piercing_level += 1
            elif name == 'Spread Shot':
                self.spread_level += 1
            elif name == 'Explosive':
                self.explosive_level += 1
            elif name == 'Armor':
                self.armor_level += 1
            elif name == 'Evasion':
                self.evasion_level += 1
            elif name == 'Slow Field':
                self.slow_factor = 0.8

            return result.notification
        except ValueError:
            return f"REWARD: {name}"

    def _upgrade_buff(self, name: str, player) -> str:
        if name == 'Power Shot':
            player.bullet_damage = int(player.bullet_damage * 1.25)
        elif name == 'Rapid Fire':
            player.fire_cooldown = max(1, int(player.fire_cooldown * 0.8))
        elif name == 'Piercing':
            self.piercing_level += 1
        elif name == 'Spread Shot':
            self.spread_level += 1
        elif name == 'Explosive':
            self.explosive_level += 1

        return f"UPGRADED: {name}"

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
        self.piercing_level = 0
        self.spread_level = 0
        self.explosive_level = 0
        self.armor_level = 0
        self.evasion_level = 0
        self.magnet_range = 0
        self.slow_factor = 1.0
