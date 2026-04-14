from .base_buff import Buff, BuffResult


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
