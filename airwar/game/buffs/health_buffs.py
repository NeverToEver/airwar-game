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
