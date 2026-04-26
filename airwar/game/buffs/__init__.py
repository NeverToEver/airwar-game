"""Buffs package — player power-up and enhancement system."""
from .base_buff import Buff, BuffResult
from .buff_registry import BUFF_REGISTRY, create_buff
from .buffs import (
    ExtraLifeBuff, RegenerationBuff, LifestealBuff,
    ShieldBuff, ArmorBuff, EvasionBuff, BarrierBuff,
    PowerShotBuff, RapidFireBuff, PiercingBuff, SpreadShotBuff, ExplosiveBuff, ShotgunBuff, LaserBuff,
    SpeedBoostBuff, MagnetBuff, SlowFieldBuff
)

__all__ = [
    'Buff', 'BuffResult',
    'BUFF_REGISTRY', 'create_buff',
    'ExtraLifeBuff', 'RegenerationBuff', 'LifestealBuff',
    'PowerShotBuff', 'RapidFireBuff', 'PiercingBuff', 'SpreadShotBuff', 'ExplosiveBuff', 'ShotgunBuff', 'LaserBuff',
    'ShieldBuff', 'ArmorBuff', 'EvasionBuff', 'BarrierBuff',
    'SpeedBoostBuff', 'MagnetBuff', 'SlowFieldBuff'
]
