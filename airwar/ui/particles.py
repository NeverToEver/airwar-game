"""UI particles — particle system for visual effects in the UI."""
import pygame
import math
import random
from airwar.config.design_tokens import get_design_tokens
from airwar.game.constants import GAME_CONSTANTS


class ParticleSystem:
    """粒子系统 — 使用 Flyweight 模式缓存粒子纹理"""

    _texture_cache = {}

    def __init__(self):
        self._particles = []
        self._animation_time = 0
        self._tokens = get_design_tokens()
        self._init_cache()

    def _init_cache(self):
        """预创建常用尺寸的粒子纹理"""
        colors_config = self._tokens.colors
        for base_size in [8, 12, 16, 20]:
            for color_key in ['particle', 'particle_alt']:
                key = (base_size, color_key)
                if key not in self._texture_cache:
                    surf = pygame.Surface((base_size * 4, base_size * 4), pygame.SRCALPHA)
                    color = colors_config.PARTICLE_PRIMARY if color_key == 'particle' else colors_config.PARTICLE_ALT
                    for i in range(base_size * 2, 0, -2):
                        layer_alpha = int(180 * (base_size * 2 - i) / (base_size * 2) * 0.4)
                        pygame.draw.circle(
                            surf,
                            (*color, layer_alpha),
                            (base_size * 2, base_size * 2),
                            i
                        )
                    self._texture_cache[key] = surf

    def _init_particles(self, count: int = 40, color_key: str = 'particle'):
        """初始化粒子数据"""
        self._particles = []
        animation_config = self._tokens.animation
        for _ in range(count):
            self._particles.append({
                'x': random.random(),
                'y': random.random(),
                'size': random.uniform(1.5, 3.5),
                'speed': random.uniform(animation_config.PARTICLE_SPEED_MIN, animation_config.PARTICLE_SPEED_MAX),
                'alpha': random.randint(80, 180),
                'pulse_speed': random.uniform(0.02, 0.05),
                'pulse_offset': random.random() * math.pi * 2,
                'color_key': color_key,
            })

    def update(self, direction: float = -1):
        """更新粒子状态"""
        self._animation_time += 1
        for p in self._particles[:]:
            p['y'] += p['speed'] * 0.003 * direction
            if p['y'] < -0.1:
                p['y'] = 1.1
                p['x'] = random.random()
                p['alpha'] = random.randint(80, 180)

    def render(self, surface: pygame.Surface, color: tuple):
        """渲染粒子"""
        width, height = surface.get_size()

        for p in self._particles:
            x = int(p['x'] * width)
            y = int(p['y'] * height)
            pulse = math.sin(self._animation_time * p['pulse_speed'] + p['pulse_offset'])
            alpha = int(p['alpha'] * (0.6 + 0.4 * pulse))
            size = int(p['size'] * (0.7 + 0.3 * pulse))
            size = max(4, min(size, 24))

            const = GAME_CONSTANTS.ANIMATION
            base_size = const.PARTICLE_BASE_SIZE_TINY
            if size > const.PARTICLE_SIZE_THRESHOLD_LARGE:
                base_size = const.PARTICLE_BASE_SIZE_LARGE
            elif size > const.PARTICLE_SIZE_THRESHOLD_MEDIUM:
                base_size = const.PARTICLE_BASE_SIZE_MEDIUM
            elif size > const.PARTICLE_SIZE_THRESHOLD_SMALL:
                base_size = const.PARTICLE_BASE_SIZE_SMALL

            cache_key = (base_size, p.get('color_key', 'particle'))
            if cache_key in self._texture_cache:
                particle_surf = self._texture_cache[cache_key]
                particle_surf.set_alpha(alpha)
                surface.blit(particle_surf, (x - base_size * 2, y - base_size * 2))
            else:
                particle_surf = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
                for i in range(size * 2, 0, -2):
                    layer_alpha = int(alpha * (size * 2 - i) / (size * 2) * 0.4)
                    pygame.draw.circle(particle_surf, (*color, layer_alpha),
                                     (size * 2, size * 2), i)
                surface.blit(particle_surf, (x - size * 2, y - size * 2))

    def reset(self, count: int = 40, color_key: str = 'particle'):
        """重置粒子系统"""
        self._animation_time = 0
        self._init_particles(count, color_key)
