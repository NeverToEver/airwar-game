"""Buffs package — player power-up and enhancement system."""
from .base_buff import Buff, BuffResult
from .buff_registry import BUFF_REGISTRY, create_buff
from .buffs import (
    ExtraLifeBuff, RegenerationBuff, LifestealBuff,
    ArmorBuff, EvasionBuff,
    PowerShotBuff, RapidFireBuff, PiercingBuff, SpreadShotBuff, ExplosiveBuff, LaserBuff,
    SlowFieldBuff, BoostRecoveryBuff, MothershipRecallBuff,
)

__all__ = [
    'Buff', 'BuffResult',
    'BUFF_REGISTRY', 'create_buff',
    'ExtraLifeBuff', 'RegenerationBuff', 'LifestealBuff',
    'PowerShotBuff', 'RapidFireBuff', 'PiercingBuff', 'SpreadShotBuff', 'ExplosiveBuff', 'LaserBuff',
    'ArmorBuff', 'EvasionBuff',
    'SlowFieldBuff', 'BoostRecoveryBuff', 'MothershipRecallBuff',
]
