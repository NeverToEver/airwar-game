
from .base_buff import Buff, BuffResult


class ExtraLifeBuff(Buff):
    def apply(self, player) -> BuffResult:
        player.max_health += 50
        player.health += 30
        return BuffResult(
            name='Extra Life',
            notification='REWARD: Extra Life',
            color=(100, 255, 150)
        )

    def get_name(self) -> str:
        return 'Extra Life'

    def get_color(self) -> tuple:
        return (100, 255, 150)


class RegenerationBuff(Buff):
    def apply(self, player) -> BuffResult:
        return BuffResult(
            name='Regeneration',
            notification='REWARD: Regeneration',
            color=(150, 255, 100)
        )

    def get_name(self) -> str:
        return 'Regeneration'

    def get_color(self) -> tuple:
        return (150, 255, 100)


class LifestealBuff(Buff):
    def apply(self, player) -> BuffResult:
        return BuffResult(
            name='Lifesteal',
            notification='REWARD: Lifesteal',
            color=(255, 100, 150)
        )

    def get_name(self) -> str:
        return 'Lifesteal'

    def get_color(self) -> tuple:
        return (255, 100, 150)


class ShieldBuff(Buff):
    def apply(self, player) -> BuffResult:
        return BuffResult(
            name='Shield',
            notification='REWARD: Shield',
            color=(200, 100, 255)
        )

    def get_name(self) -> str:
        return 'Shield'

    def get_color(self) -> tuple:
        return (200, 100, 255)


class ArmorBuff(Buff):
    def __init__(self):
        self.level = 0

    def apply(self, player) -> BuffResult:
        self.level += 1
        return BuffResult(
            name='Armor',
            notification='REWARD: Armor',
            color=(150, 150, 180)
        )

    def get_name(self) -> str:
        return 'Armor'

    def get_color(self) -> tuple:
        return (150, 150, 180)


class EvasionBuff(Buff):
    def __init__(self):
        self.level = 0

    def apply(self, player) -> BuffResult:
        self.level += 1
        return BuffResult(
            name='Evasion',
            notification='REWARD: Evasion',
            color=(100, 200, 255)
        )

    def get_name(self) -> str:
        return 'Evasion'

    def get_color(self) -> tuple:
        return (100, 200, 255)


class BarrierBuff(Buff):
    def apply(self, player) -> BuffResult:
        player.max_health += 50
        player.health += 50
        return BuffResult(
            name='Barrier',
            notification='REWARD: Barrier',
            color=(100, 150, 200)
        )

    def get_name(self) -> str:
        return 'Barrier'

    def get_color(self) -> tuple:
        return (100, 150, 200)


class PowerShotBuff(Buff):
    def apply(self, player) -> BuffResult:
        player.bullet_damage = int(player.bullet_damage * 1.25)
        return BuffResult(
            name='Power Shot',
            notification='REWARD: Power Shot',
            color=(255, 80, 80)
        )

    def get_name(self) -> str:
        return 'Power Shot'

    def get_color(self) -> tuple:
        return (255, 80, 80)


class RapidFireBuff(Buff):
    def apply(self, player) -> BuffResult:
        player.fire_cooldown = max(1, int(player.fire_cooldown * 0.8))
        return BuffResult(
            name='Rapid Fire',
            notification='REWARD: Rapid Fire',
            color=(255, 200, 100)
        )

    def get_name(self) -> str:
        return 'Rapid Fire'

    def get_color(self) -> tuple:
        return (255, 200, 100)


class PiercingBuff(Buff):
    def __init__(self):
        self.level = 0

    def apply(self, player) -> BuffResult:
        self.level += 1
        return BuffResult(
            name='Piercing',
            notification='REWARD: Piercing',
            color=(200, 200, 100)
        )

    def get_name(self) -> str:
        return 'Piercing'

    def get_color(self) -> tuple:
        return (200, 200, 100)


class SpreadShotBuff(Buff):
    def __init__(self):
        self.level = 0

    def apply(self, player) -> BuffResult:
        self.level += 1
        return BuffResult(
            name='Spread Shot',
            notification='REWARD: Spread Shot',
            color=(255, 150, 100)
        )

    def get_name(self) -> str:
        return 'Spread Shot'

    def get_color(self) -> tuple:
        return (255, 150, 100)


class ExplosiveBuff(Buff):
    def __init__(self):
        self.level = 0

    def apply(self, player) -> BuffResult:
        self.level += 1
        return BuffResult(
            name='Explosive',
            notification='REWARD: Explosive',
            color=(255, 100, 50)
        )

    def get_name(self) -> str:
        return 'Explosive'

    def get_color(self) -> tuple:
        return (255, 100, 50)


class ShotgunBuff(Buff):
    def __init__(self):
        self.level = 0

    def apply(self, player) -> BuffResult:
        self.level += 1
        return BuffResult(
            name='Shotgun',
            notification='REWARD: Shotgun Mode',
            color=(255, 120, 200)
        )

    def get_name(self) -> str:
        return 'Shotgun'

    def get_color(self) -> tuple:
        return (255, 120, 200)


class LaserBuff(Buff):
    def __init__(self):
        self.level = 0

    def apply(self, player) -> BuffResult:
        self.level += 1
        return BuffResult(
            name='Laser',
            notification='REWARD: Laser Mode',
            color=(100, 200, 255)
        )

    def get_name(self) -> str:
        return 'Laser'

    def get_color(self) -> tuple:
        return (100, 200, 255)


class SpeedBoostBuff(Buff):
    def apply(self, player) -> BuffResult:
        return BuffResult(
            name='Speed Boost',
            notification='REWARD: Speed Boost',
            color=(100, 255, 200)
        )

    def get_name(self) -> str:
        return 'Speed Boost'

    def get_color(self) -> tuple:
        return (100, 255, 200)


class MagnetBuff(Buff):
    def apply(self, player) -> BuffResult:
        return BuffResult(
            name='Magnet',
            notification='REWARD: Magnet',
            color=(255, 255, 100)
        )

    def get_name(self) -> str:
        return 'Magnet'

    def get_color(self) -> tuple:
        return (255, 255, 100)


class SlowFieldBuff(Buff):
    def apply(self, player) -> BuffResult:
        return BuffResult(
            name='Slow Field',
            notification='REWARD: Slow Field',
            color=(150, 150, 255)
        )

    def get_name(self) -> str:
        return 'Slow Field'

    def get_color(self) -> tuple:
        return (150, 150, 255)
