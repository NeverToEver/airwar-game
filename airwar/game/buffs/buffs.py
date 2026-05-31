"""Buff implementations — 12 buff types for player power-ups."""
from airwar.config.design_tokens import Colors

from .base_buff import Buff, BuffResult


class ExtraLifeBuff(Buff):
    """Extra life buff — increases maximum and current HP."""
    NAME = 'Extra Life'
    COLOR = (100, 255, 150)

    def calculate_value(self, base_value: int, current_level: int) -> int:
        return base_value + (current_level * 50)

    def calculate_increment(self, base_value: int) -> int:
        return 50


class RegenerationBuff(Buff):
    """Regeneration buff — passively heals HP per second."""
    NAME = 'Regeneration'
    COLOR = (150, 255, 100)

    def calculate_value(self, base_value: int, current_level: int) -> int:
        return current_level

    def calculate_increment(self, base_value: int) -> int:
        return 1


class LifestealBuff(Buff):
    """Lifesteal buff — heals a percentage of damage dealt on kill."""
    NAME = 'Lifesteal'
    COLOR = (255, 100, 150)

    def calculate_value(self, base_value: int, current_level: int) -> int:
        return current_level

    def calculate_increment(self, base_value: int) -> int:
        return 1


class ArmorBuff(Buff):
    """Armor buff — reduces incoming damage by a percentage."""
    NAME = 'Armor'
    COLOR = (150, 150, 180)

    def calculate_value(self, base_value: int, current_level: int) -> int:
        return current_level

    def calculate_increment(self, base_value: int) -> int:
        return 1

    def get_notification(self, level: int) -> str:
        if level == 1:
            return 'Acquired: Armor'
        return f'Upgraded: Armor (Lv.{level})'


class EvasionBuff(Buff):
    """Evasion buff — grants a chance to dodge incoming attacks."""
    NAME = 'Evasion'
    COLOR = (100, 200, 255)

    def calculate_value(self, base_value: int, current_level: int) -> int:
        return current_level

    def calculate_increment(self, base_value: int) -> int:
        return 1

    def get_notification(self, level: int) -> str:
        if level == 1:
            return 'Acquired: Evasion'
        return f'Upgraded: Evasion (Lv.{level})'


class PowerShotBuff(Buff):
    """Power shot buff — increases bullet damage."""
    NAME = 'Power Shot'
    COLOR = (255, 80, 80)

    def calculate_value(self, base_value: int, current_level: int) -> int:
        return int(base_value * (1.25 ** current_level))

    def calculate_increment(self, base_value: int) -> int:
        return int(base_value * 0.25)

    def get_notification(self, level: int) -> str:
        if level == 1:
            return 'Acquired: Power Shot'
        return f'Upgraded: Power Shot (Lv.{level})'


class RapidFireBuff(Buff):
    """Rapid fire buff — reduces fire cooldown time."""
    NAME = 'Rapid Fire'
    COLOR = (255, 200, 100)

    def calculate_value(self, base_value: int, current_level: int) -> int:
        return max(1, int(base_value * (0.8 ** current_level)))

    def calculate_increment(self, base_value: int) -> int:
        return int(base_value * 0.2)

    def get_notification(self, level: int) -> str:
        if level == 1:
            return 'Acquired: Rapid Fire'
        return f'Upgraded: Rapid Fire (Lv.{level})'


class PiercingBuff(Buff):
    """Piercing buff — bullets pass through a number of enemies."""
    NAME = 'Piercing'
    COLOR = (200, 200, 100)

    def calculate_value(self, base_value: int, current_level: int) -> int:
        return current_level

    def calculate_increment(self, base_value: int) -> int:
        return 1

    def get_notification(self, level: int) -> str:
        if level == 1:
            return 'Acquired: Piercing'
        return f'Upgraded: Piercing (Lv.{level})'


class SpreadShotBuff(Buff):
    """Spread shot buff — fires multiple bullets in a spread pattern."""
    NAME = 'Spread Shot'
    COLOR = (255, 150, 100)

    def calculate_value(self, base_value: int, current_level: int) -> int:
        return current_level

    def calculate_increment(self, base_value: int) -> int:
        return 1

    def get_notification(self, level: int) -> str:
        if level == 1:
            return 'Acquired: Spread Shot'
        return f'Upgraded: Spread Shot (Lv.{level})'


class ExplosiveBuff(Buff):
    """Explosive buff — bullets deal area-of-effect damage on hit."""
    NAME = 'Explosive'
    COLOR = Colors.ACCENT_EXPLOSIVE

    def calculate_value(self, base_value: int, current_level: int) -> int:
        return current_level

    def calculate_increment(self, base_value: int) -> int:
        return 1

    def get_notification(self, level: int) -> str:
        if level == 1:
            return 'Acquired: Explosive'
        return f'Upgraded: Explosive (Lv.{level})'


class LaserBuff(Buff):
    """Laser buff — continuous laser beam attack."""
    NAME = 'Laser'
    COLOR = (100, 200, 255)

    def calculate_value(self, base_value: int, current_level: int) -> int:
        return current_level

    def calculate_increment(self, base_value: int) -> int:
        return 1

    def get_notification(self, level: int) -> str:
        if level == 1:
            return 'Acquired: Laser Mode'
        return f'Upgraded: Laser (Lv.{level})'


class SlowFieldBuff(Buff):
    """Slow field buff — reduces enemy movement speed globally."""
    NAME = 'Slow Field'
    COLOR = (150, 150, 255)

    def calculate_value(self, base_value: int, current_level: int) -> int:
        return current_level

    def calculate_increment(self, base_value: int) -> int:
        return 1


class BoostRecoveryBuff(Buff):
    """Boost recovery buff — increases boost energy regeneration rate by 50%."""
    NAME = 'Boost Recovery'
    COLOR = (100, 200, 230)

    def calculate_value(self, base_value: int, current_level: int) -> int:
        return current_level

    def calculate_increment(self, base_value: int) -> int:
        return 1

    def apply(self, player) -> BuffResult:
        player.boost_recovery_rate *= 1.5
        return BuffResult(
            name=self.NAME,
            notification=self.get_notification(1),
            color=self.COLOR
        )


class PhaseDashBuff(Buff):
    """Phase Dash buff — unlocks a boost-fueled invincible dash."""
    NAME = 'Phase Dash'
    COLOR = (220, 95, 85)

    def calculate_value(self, base_value: int, current_level: int) -> int:
        return current_level

    def calculate_increment(self, base_value: int) -> int:
        return 1

    def apply(self, player) -> BuffResult:
        player.activate_phase_dash()
        return BuffResult(
            name=self.NAME,
            notification=self.get_notification(1),
            color=self.COLOR
        )


class MothershipRecallBuff(Buff):
    """Mothership Recall buff — reduces mothership cooldown by 50% per level."""
    NAME = 'Mothership Recall'
    COLOR = (80, 180, 220)

    def calculate_value(self, base_value: int, current_level: int) -> int:
        return current_level

    def calculate_increment(self, base_value: int) -> int:
        return 1

    def apply(self, player) -> BuffResult:
        # Each level: cooldown_mult *= 0.5 (60s → 30s → 15s)
        player.mothership_cooldown_mult *= 0.5
        return BuffResult(
            name=self.NAME,
            notification=self.get_notification(1),
            color=self.COLOR
        )
