import pygame
import math
import random
from airwar.config.design_tokens import get_design_tokens, MilitaryColors, MilitaryUI


class MenuBackground:
    """背景渲染器 — 负责渐变背景和星星效果"""

    def __init__(self):
        self._stars = []
        self._animation_time = 0
        self._gradient_cache = {}
        self._tokens = get_design_tokens()
        self._init_stars()

    def _init_stars(self):
        """初始化星星数据"""
        self._stars = []
        star_count = self._tokens.components.STAR_COUNT
        for _ in range(star_count):
            self._stars.append({
                'x': random.random(),
                'y': random.random(),
                'size': random.uniform(0.5, 2.0),
                'brightness': random.randint(50, 150),
                'twinkle_speed': random.uniform(
                    self._tokens.animation.TWINKLE_SPEED_MIN,
                    self._tokens.animation.TWINKLE_SPEED_MAX
                ),
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
        star_speed = self._tokens.animation.STAR_SPEED
        for star in self._stars:
            star['y'] += star_speed
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
        star_color = self._tokens.colors.star_color
        for star in self._stars:
            x = int(star['x'] * width)
            y = int(star['y'] * height)
            twinkle = math.sin(self._animation_time * star['twinkle_speed'] + star['twinkle_offset'])
            brightness = int(star['brightness'] * (0.5 + 0.5 * twinkle))
            pygame.draw.circle(surface, star_color(brightness), (x, y), int(star['size']))

    def render_military_style(self, surface: pygame.Surface, colors: dict):
        """渲染军事风格背景（带网格和扫描线）

        Args:
            surface: 目标 surface
            colors: 颜色配置
        """
        # 先渲染普通背景
        self.render(surface, colors)

        # 渲染网格线
        self._render_grid_overlay(surface)

        # 渲染扫描线
        self._render_scanline_overlay(surface)

    def _render_grid_overlay(self, surface: pygame.Surface):
        """渲染网格覆盖层"""
        width, height = surface.get_size()
        spacing = MilitaryUI.GRID_SPACING
        alpha = MilitaryUI.GRID_ALPHA

        grid_color = (*MilitaryColors.AMBER_PRIMARY[:3], alpha)

        # 垂直线
        for x in range(0, width, spacing):
            pygame.draw.line(surface, grid_color, (x, 0), (x, height))

        # 水平线
        for y in range(0, height, spacing):
            pygame.draw.line(surface, grid_color, (0, y), (width, y))

    def _render_scanline_overlay(self, surface: pygame.Surface):
        """渲染扫描线覆盖层"""
        width, height = surface.get_size()
        spacing = MilitaryUI.SCANLINE_SPACING
        alpha = MilitaryUI.SCANLINE_ALPHA

        # 计算扫描线偏移（动画效果）
        offset = (self._animation_time * MilitaryUI.SCANLINE_SPEED) % spacing

        scanline_color = (*MilitaryColors.AMBER_PRIMARY[:3], alpha)

        for y in range(int(offset), height, spacing):
            pygame.draw.line(surface, scanline_color, (0, y), (width, y))
