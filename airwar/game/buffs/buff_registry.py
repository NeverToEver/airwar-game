from typing import Type, Dict
from .base_buff import Buff
from .buffs import (
    ExtraLifeBuff, RegenerationBuff, LifestealBuff,
    ShieldBuff, ArmorBuff, EvasionBuff, BarrierBuff,
    PowerShotBuff, RapidFireBuff, PiercingBuff, SpreadShotBuff, ExplosiveBuff, ShotgunBuff, LaserBuff,
    SpeedBoostBuff, MagnetBuff, SlowFieldBuff
)


BUFF_REGISTRY: Dict[str, Type[Buff]] = {
    'Extra Life': ExtraLifeBuff,
    'Regeneration': RegenerationBuff,
    'Lifesteal': LifestealBuff,
    'Power Shot': PowerShotBuff,
    'Rapid Fire': RapidFireBuff,
    'Piercing': PiercingBuff,
    'Spread Shot': SpreadShotBuff,
    'Explosive': ExplosiveBuff,
    'Shotgun': ShotgunBuff,
    'Laser': LaserBuff,
    'Shield': ShieldBuff,
    'Armor': ArmorBuff,
    'Evasion': EvasionBuff,
    'Barrier': BarrierBuff,
    'Speed Boost': SpeedBoostBuff,
    'Magnet': MagnetBuff,
    'Slow Field': SlowFieldBuff,
}


def create_buff(name: str) -> Buff:
    buff_class = BUFF_REGISTRY.get(name)
    if buff_class:
        return buff_class()
    raise ValueError(f"Unknown buff: {name}")
