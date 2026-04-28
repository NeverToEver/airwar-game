"""Discrete segmented health indicator — fine-grained segments, no shell."""
import pygame


class DiscreteBatteryIndicator:
    """离散分段血量指示器 — 无外壳，仅渲染细密分段。

    支持 vertical（折叠模式）和 horizontal（展开模式）两种方向。
    所有有效段使用同一颜色，颜色根据血量比例整体变化。
    """

    def __init__(self, width: int, height: int, num_segments: int = 20,
                 orientation: str = 'vertical'):
        self._w = width
        self._h = height
        self._num_segments = num_segments
        self._orientation = orientation
        self._health = 100
        self._max_health = 100
        self._gap = 1

    def set_health(self, health: int, max_health: int) -> None:
        self._health = health
        self._max_health = max_health

    def _health_color(self, ratio: float):
        """根据血量比例返回整体颜色。"""
        if ratio > 0.5:
            return (80, 200, 100)
        elif ratio > 0.25:
            return (230, 170, 50)
        else:
            return (220, 60, 45)

    def render(self, surface: pygame.Surface, x: int, y: int) -> None:
        if self._orientation == 'vertical':
            self._render_vertical(surface, x, y)
        else:
            self._render_horizontal(surface, x, y)

    def _render_vertical(self, surface, x, y):
        w, h = self._w, self._h
        gap = self._gap
        n = self._num_segments

        seg_space = h - (n - 1) * gap
        base_h = seg_space // n
        rem = seg_space % n

        health_ratio = self._health / self._max_health if self._max_health > 0 else 0
        active_count = max(0, min(n, int(n * health_ratio + 0.5)))
        active_start = max(0, n - active_count)

        color = self._health_color(health_ratio)

        seg_y = y
        for i in range(n):
            cur_h = base_h + (1 if i < rem else 0)
            seg_r = max(1, cur_h // 4)
            seg_rect = pygame.Rect(x, int(seg_y), w, cur_h)

            if i >= active_start:
                pygame.draw.rect(surface, color, seg_rect, border_radius=seg_r)
            else:
                pygame.draw.rect(surface, (12, 12, 14, 200), seg_rect, border_radius=seg_r)

            seg_y += cur_h + gap

    def _render_horizontal(self, surface, x, y):
        w, h = self._w, self._h
        gap = self._gap
        n = self._num_segments

        seg_space = w - (n - 1) * gap
        base_w = seg_space // n
        rem = seg_space % n

        health_ratio = self._health / self._max_health if self._max_health > 0 else 0
        active_count = max(0, min(n, int(n * health_ratio + 0.5)))

        color = self._health_color(health_ratio)

        seg_x = x
        for i in range(n):
            cur_w = base_w + (1 if i < rem else 0)
            seg_r = max(1, cur_w // 5)
            seg_rect = pygame.Rect(int(seg_x), y, cur_w, h)

            if i < active_count:
                pygame.draw.rect(surface, color, seg_rect, border_radius=seg_r)
            else:
                pygame.draw.rect(surface, (12, 12, 14, 200), seg_rect, border_radius=seg_r)

            seg_x += cur_w + gap
