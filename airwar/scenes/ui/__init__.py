"""Scene UI Components

提供场景共用的渲染组件，包括背景、粒子系统、特效渲染等。
使用 Flyweight 模式优化性能。
"""

from airwar.scenes.ui.background import BackgroundRenderer
from airwar.scenes.ui.particles import ParticleSystem
from airwar.scenes.ui.effects import EffectsRenderer

__all__ = [
    'BackgroundRenderer',
    'ParticleSystem',
    'EffectsRenderer',
]
