"""Buffs package — player power-up and enhancement system."""

from .base_buff import Buff, BuffResult
from .buff_registry import BUFF_REGISTRY, create_buff
from .buffs import (
    ArmorBuff,
    BoostRecoveryBuff,
    EvasionBuff,
    ExplosiveBuff,
    ExtraLifeBuff,
    LaserBuff,
    LifestealBuff,
    MothershipRecallBuff,
    PiercingBuff,
    PowerShotBuff,
    RapidFireBuff,
    RegenerationBuff,
    SlowFieldBuff,
    SpreadShotBuff,
)

__all__ = [
    "BUFF_REGISTRY",
    "ArmorBuff",
    "BoostRecoveryBuff",
    "Buff",
    "BuffResult",
    "EvasionBuff",
    "ExplosiveBuff",
    "ExtraLifeBuff",
    "LaserBuff",
    "LifestealBuff",
    "MothershipRecallBuff",
    "PiercingBuff",
    "PowerShotBuff",
    "RapidFireBuff",
    "RegenerationBuff",
    "SlowFieldBuff",
    "SpreadShotBuff",
    "create_buff",
]
