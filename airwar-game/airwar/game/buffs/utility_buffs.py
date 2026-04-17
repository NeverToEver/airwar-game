from .base_buff import Buff, BuffResult


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
