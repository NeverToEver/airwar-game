"""Buff registry — centralized buff metadata and factory functions."""

from .base_buff import Buff
from .buffs import (
    ArmorBuff,
    BoostRecoveryBuff,
    EvasionBuff,
    ExplosiveBuff,
    ExtraLifeBuff,
    LaserBuff,
    LifestealBuff,
    MothershipRecallBuff,
    PhaseDashBuff,
    PiercingBuff,
    PowerShotBuff,
    RapidFireBuff,
    RegenerationBuff,
    SlowFieldBuff,
    SpreadShotBuff,
)

BUFF_REGISTRY: dict[str, type[Buff]] = {
    "Extra Life": ExtraLifeBuff,
    "Regeneration": RegenerationBuff,
    "Lifesteal": LifestealBuff,
    "Power Shot": PowerShotBuff,
    "Rapid Fire": RapidFireBuff,
    "Piercing": PiercingBuff,
    "Spread Shot": SpreadShotBuff,
    "Explosive": ExplosiveBuff,
    "Laser": LaserBuff,
    "Armor": ArmorBuff,
    "Evasion": EvasionBuff,
    "Slow Field": SlowFieldBuff,
    "Boost Recovery": BoostRecoveryBuff,
    "Phase Dash": PhaseDashBuff,
    "Mothership Recall": MothershipRecallBuff,
}

_BUFF_COLOR_CACHE: dict[str, tuple] = {}


def get_buff_color(name: str) -> tuple:
    if name not in _BUFF_COLOR_CACHE:
        buff_class = BUFF_REGISTRY.get(name)
        if buff_class:
            _BUFF_COLOR_CACHE[name] = buff_class().get_color()
        else:
            _BUFF_COLOR_CACHE[name] = (255, 200, 100)
    return _BUFF_COLOR_CACHE[name]


def create_buff(name: str) -> Buff:
    buff_class = BUFF_REGISTRY.get(name)
    if buff_class:
        return buff_class()
    raise ValueError(f"Unknown buff: {name}")
