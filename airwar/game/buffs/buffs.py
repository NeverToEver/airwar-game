
from .base_buff import Buff, BuffResult


class ExtraLifeBuff(Buff):
    def calculate_value(self, base_value: int, current_level: int) -> int:
        return base_value + (current_level * 50)

    def calculate_increment(self, base_value: int) -> int:
        return 50

    def apply(self, player) -> BuffResult:
        return BuffResult(
            name='Extra Life',
            notification='REWARD: Extra Life',
            color=(100, 255, 150)
        )

    def get_name(self) -> str:
        return 'Extra Life'

    def get_color(self) -> tuple:
        return (100, 255, 150)

    def get_notification(self, level: int) -> str:
        return 'REWARD: Extra Life'


class RegenerationBuff(Buff):
    def calculate_value(self, base_value: int, current_level: int) -> int:
        return current_level

    def calculate_increment(self, base_value: int) -> int:
        return 1

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

    def get_notification(self, level: int) -> str:
        return 'REWARD: Regeneration'


class LifestealBuff(Buff):
    def calculate_value(self, base_value: int, current_level: int) -> int:
        return current_level

    def calculate_increment(self, base_value: int) -> int:
        return 1

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

    def get_notification(self, level: int) -> str:
        return 'REWARD: Lifesteal'


class ShieldBuff(Buff):
    def calculate_value(self, base_value: int, current_level: int) -> int:
        return current_level

    def calculate_increment(self, base_value: int) -> int:
        return 1

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

    def get_notification(self, level: int) -> str:
        return 'REWARD: Shield'


class ArmorBuff(Buff):
    def calculate_value(self, base_value: int, current_level: int) -> int:
        return current_level

    def calculate_increment(self, base_value: int) -> int:
        return 1

    def apply(self, player) -> BuffResult:
        return BuffResult(
            name='Armor',
            notification='REWARD: Armor',
            color=(150, 150, 180)
        )

    def get_name(self) -> str:
        return 'Armor'

    def get_color(self) -> tuple:
        return (150, 150, 180)

    def get_notification(self, level: int) -> str:
        if level == 1:
            return 'REWARD: Armor'
        return f'UPGRADED: Armor (Lv.{level})'


class EvasionBuff(Buff):
    def calculate_value(self, base_value: int, current_level: int) -> int:
        return current_level

    def calculate_increment(self, base_value: int) -> int:
        return 1

    def apply(self, player) -> BuffResult:
        return BuffResult(
            name='Evasion',
            notification='REWARD: Evasion',
            color=(100, 200, 255)
        )

    def get_name(self) -> str:
        return 'Evasion'

    def get_color(self) -> tuple:
        return (100, 200, 255)

    def get_notification(self, level: int) -> str:
        if level == 1:
            return 'REWARD: Evasion'
        return f'UPGRADED: Evasion (Lv.{level})'


class BarrierBuff(Buff):
    def calculate_value(self, base_value: int, current_level: int) -> int:
        return current_level

    def calculate_increment(self, base_value: int) -> int:
        return 50

    def apply(self, player) -> BuffResult:
        return BuffResult(
            name='Barrier',
            notification='REWARD: Barrier',
            color=(100, 150, 200)
        )

    def get_name(self) -> str:
        return 'Barrier'

    def get_color(self) -> tuple:
        return (100, 150, 200)

    def get_notification(self, level: int) -> str:
        return 'REWARD: Barrier'


class PowerShotBuff(Buff):
    def calculate_value(self, base_value: int, current_level: int) -> int:
        return int(base_value * (1.25 ** current_level))

    def calculate_increment(self, base_value: int) -> int:
        return int(base_value * 0.25)

    def apply(self, player) -> BuffResult:
        return BuffResult(
            name='Power Shot',
            notification='REWARD: Power Shot',
            color=(255, 80, 80)
        )

    def get_name(self) -> str:
        return 'Power Shot'

    def get_color(self) -> tuple:
        return (255, 80, 80)

    def get_notification(self, level: int) -> str:
        if level == 1:
            return 'REWARD: Power Shot'
        return f'UPGRADED: Power Shot (Lv.{level})'


class RapidFireBuff(Buff):
    def calculate_value(self, base_value: int, current_level: int) -> int:
        return max(1, int(base_value * (0.8 ** current_level)))

    def calculate_increment(self, base_value: int) -> int:
        return int(base_value * 0.2)

    def apply(self, player) -> BuffResult:
        return BuffResult(
            name='Rapid Fire',
            notification='REWARD: Rapid Fire',
            color=(255, 200, 100)
        )

    def get_name(self) -> str:
        return 'Rapid Fire'

    def get_color(self) -> tuple:
        return (255, 200, 100)

    def get_notification(self, level: int) -> str:
        if level == 1:
            return 'REWARD: Rapid Fire'
        return f'UPGRADED: Rapid Fire (Lv.{level})'


class PiercingBuff(Buff):
    def calculate_value(self, base_value: int, current_level: int) -> int:
        return current_level

    def calculate_increment(self, base_value: int) -> int:
        return 1

    def apply(self, player) -> BuffResult:
        return BuffResult(
            name='Piercing',
            notification='REWARD: Piercing',
            color=(200, 200, 100)
        )

    def get_name(self) -> str:
        return 'Piercing'

    def get_color(self) -> tuple:
        return (200, 200, 100)

    def get_notification(self, level: int) -> str:
        if level == 1:
            return 'REWARD: Piercing'
        return f'UPGRADED: Piercing (Lv.{level})'


class SpreadShotBuff(Buff):
    def calculate_value(self, base_value: int, current_level: int) -> int:
        return current_level

    def calculate_increment(self, base_value: int) -> int:
        return 1

    def apply(self, player) -> BuffResult:
        return BuffResult(
            name='Spread Shot',
            notification='REWARD: Spread Shot',
            color=(255, 150, 100)
        )

    def get_name(self) -> str:
        return 'Spread Shot'

    def get_color(self) -> tuple:
        return (255, 150, 100)

    def get_notification(self, level: int) -> str:
        if level == 1:
            return 'REWARD: Spread Shot'
        return f'UPGRADED: Spread Shot (Lv.{level})'


class ExplosiveBuff(Buff):
    def calculate_value(self, base_value: int, current_level: int) -> int:
        return current_level

    def calculate_increment(self, base_value: int) -> int:
        return 1

    def apply(self, player) -> BuffResult:
        return BuffResult(
            name='Explosive',
            notification='REWARD: Explosive',
            color=(255, 100, 50)
        )

    def get_name(self) -> str:
        return 'Explosive'

    def get_color(self) -> tuple:
        return (255, 100, 50)

    def get_notification(self, level: int) -> str:
        if level == 1:
            return 'REWARD: Explosive'
        return f'UPGRADED: Explosive (Lv.{level})'


class ShotgunBuff(Buff):
    def calculate_value(self, base_value: int, current_level: int) -> int:
        return current_level

    def calculate_increment(self, base_value: int) -> int:
        return 1

    def apply(self, player) -> BuffResult:
        return BuffResult(
            name='Shotgun',
            notification='REWARD: Shotgun Mode',
            color=(255, 120, 200)
        )

    def get_name(self) -> str:
        return 'Shotgun'

    def get_color(self) -> tuple:
        return (255, 120, 200)

    def get_notification(self, level: int) -> str:
        if level == 1:
            return 'REWARD: Shotgun Mode'
        return f'UPGRADED: Shotgun (Lv.{level})'


class LaserBuff(Buff):
    def calculate_value(self, base_value: int, current_level: int) -> int:
        return current_level

    def calculate_increment(self, base_value: int) -> int:
        return 1

    def apply(self, player) -> BuffResult:
        return BuffResult(
            name='Laser',
            notification='REWARD: Laser Mode',
            color=(100, 200, 255)
        )

    def get_name(self) -> str:
        return 'Laser'

    def get_color(self) -> tuple:
        return (100, 200, 255)

    def get_notification(self, level: int) -> str:
        if level == 1:
            return 'REWARD: Laser Mode'
        return f'UPGRADED: Laser (Lv.{level})'


class SpeedBoostBuff(Buff):
    def calculate_value(self, base_value: int, current_level: int) -> int:
        return current_level

    def calculate_increment(self, base_value: int) -> int:
        return 1

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

    def get_notification(self, level: int) -> str:
        return 'REWARD: Speed Boost'


class MagnetBuff(Buff):
    def calculate_value(self, base_value: int, current_level: int) -> int:
        return current_level

    def calculate_increment(self, base_value: int) -> int:
        return 1

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

    def get_notification(self, level: int) -> str:
        return 'REWARD: Magnet'


class SlowFieldBuff(Buff):
    def calculate_value(self, base_value: int, current_level: int) -> int:
        return current_level

    def calculate_increment(self, base_value: int) -> int:
        return 1

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

    def get_notification(self, level: int) -> str:
        return 'REWARD: Slow Field'
