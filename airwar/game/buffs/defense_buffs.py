from .base_buff import Buff, BuffResult


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
