import pygame
import math
import random


class BackgroundRenderer:
    """背景渲染器 — 负责渐变背景和星星效果"""

    def __init__(self):
        self._stars = []
        self._animation_time = 0
        self._gradient_cache = {}
        self._init_stars()

    def _init_stars(self):
        """初始化星星数据"""
        self._stars = []
        for _ in range(100):
            self._stars.append({
                'x': random.random(),
                'y': random.random(),
                'size': random.uniform(0.5, 2.0),
                'brightness': random.randint(50, 150),
                'twinkle_speed': random.uniform(0.03, 0.08),
                'twinkle_offset': random.random() * math.pi * 2,
            })

    def _get_cached_gradient(self, surface: pygame.Surface, bg_color: tuple, gradient_color: tuple) -> pygame.Surface:
        """获取或创建渐变背景缓存"""
        width, height = surface.get_size()
        cache_key = (width, height, bg_color, gradient_color)

        if cache_key not in self._gradient_cache:
            gradient = pygame.Surface((width, height))
            for y in range(0, height, 3):
                ratio = y / height
                r = int(bg_color[0] * (1 - ratio) + gradient_color[0] * ratio)
                g = int(bg_color[1] * (1 - ratio) + gradient_color[1] * ratio)
                b = int(bg_color[2] * (1 - ratio) + gradient_color[2] * ratio)
                pygame.draw.line(gradient, (r, g, b), (0, y), (width, y))
            self._gradient_cache[cache_key] = gradient

        return self._gradient_cache[cache_key]

    def update(self):
        """更新动画状态"""
        self._animation_time += 1
        for star in self._stars:
            star['y'] += 0.008
            if star['y'] > 1:
                star['y'] = 0
                star['x'] = random.random()

    def render(self, surface: pygame.Surface, colors: dict):
        """渲染背景"""
        gradient = self._get_cached_gradient(
            surface,
            colors['bg'],
            colors.get('bg_gradient', colors['bg'])
        )
        surface.blit(gradient, (0, 0))

        width, height = surface.get_size()
        for star in self._stars:
            x = int(star['x'] * width)
            y = int(star['y'] * height)
            twinkle = math.sin(self._animation_time * star['twinkle_speed'] + star['twinkle_offset'])
            brightness = int(star['brightness'] * (0.5 + 0.5 * twinkle))
            pygame.draw.circle(surface, (brightness, brightness, brightness + 30), (x, y), int(star['size']))
