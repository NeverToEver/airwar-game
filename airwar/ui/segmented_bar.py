"""Segmented progress bar component — military HUD style."""

from typing import Any

import pygame

from airwar.config.design_tokens import SystemColors, SystemUI
from airwar.ui.scene_rendering_utils import render_cached_text
from airwar.utils.fonts import get_cjk_font


class SegmentedProgressBar:
    """Segmented progress bar with military-style rendering."""

    def __init__(self, width: int, height: int = 16, segments: int = 10, segment_gap: int | None = None):
        """Initialize the segmented progress bar.

        Args:
            width: Total width.
            height: Bar height.
            segments: Number of segments.
            segment_gap: Gap between segments.
        """
        self.width = width
        self.height = height
        self.segments = segments
        self.segment_gap = segment_gap or SystemUI.SEGMENT_GAP
        self.segment_width = (width - (segments - 1) * self.segment_gap) // segments
        self._rendered_cache: dict[tuple[Any, ...], pygame.Surface] = {}
        self._pulse_surf: pygame.Surface | None = None

    def render(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        value: float,
        max_value: float,
        fill_color: tuple[int, int, int] | None = None,
        bg_color: tuple[int, int, int] | None = None,
        border_color: tuple[int, int, int] | None = None,
        is_chamfered: bool = False,
    ) -> None:
        """Render the segmented progress bar.

        Args:
            surface: Target surface.
            x: X coordinate.
            y: Y coordinate.
            value: Current value.
            max_value: Maximum value.
            fill_color: Fill color.
            bg_color: Background color.
            border_color: Border color.
            is_chamfered: Whether to use chamfered (cut-corner) style.
        """
        if fill_color is None:
            fill_color = SystemColors.HEALTH_MEDIUM
        if bg_color is None:
            bg_color = SystemColors.HEALTH_LOW
        if border_color is None:
            border_color = SystemColors.SEGMENT_BORDER

        ratio = 0.0 if max_value <= 0 else min(max(value / max_value, 0.0), 1.0)
        filled_count = int(ratio * self.segments)

        # 绘制每个段
        for i in range(self.segments):
            seg_x = x + i * (self.segment_width + self.segment_gap)
            seg_rect = pygame.Rect(seg_x, y, self.segment_width, self.height)

            if i < filled_count:
                # 填充段
                if is_chamfered:
                    self._draw_chamfered_segment(surface, seg_rect, fill_color, border_color)
                else:
                    pygame.draw.rect(surface, fill_color, seg_rect)
                    pygame.draw.rect(surface, border_color, seg_rect, 1)
            else:
                # 空段
                pygame.draw.rect(surface, bg_color, seg_rect)
                pygame.draw.rect(surface, border_color, seg_rect, 1)

    def _draw_chamfered_segment(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        fill_color: tuple[int, int, int],
        border_color: tuple[int, int, int],
    ) -> None:
        """Draw a chamfered (cut-corner) segment."""
        cache_key = (self.segment_width, self.height, fill_color, border_color)
        if cache_key not in self._rendered_cache:
            chamfer = min(3, rect.width // 4, rect.height // 2)
            points = [
                (chamfer, 0),
                (rect.width - chamfer, 0),
                (rect.width, chamfer),
                (rect.width, rect.height - chamfer),
                (rect.width - chamfer, rect.height),
                (chamfer, rect.height),
                (0, rect.height - chamfer),
                (0, chamfer),
            ]
            seg_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            seg_surf.fill((0, 0, 0, 0))
            pygame.draw.polygon(seg_surf, fill_color, points)
            pygame.draw.lines(seg_surf, border_color, False, points, 1)
            self._rendered_cache[cache_key] = seg_surf
        surface.blit(self._rendered_cache[cache_key], (rect.x, rect.y))

    def render_with_glow(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        value: float,
        max_value: float,
        glow_color: tuple[int, int, int, int] | None = None,
        fill_color: tuple[int, int, int] | None = None,
        bg_color: tuple[int, int, int] | None = None,
        is_chamfered: bool = False,
    ) -> None:
        """Render a progress bar with a glow effect.

        Args:
            surface: Target surface.
            x: X coordinate.
            y: Y coordinate.
            value: Current value.
            max_value: Maximum value.
            glow_color: Glow color (RGBA).
            fill_color: Fill color.
            bg_color: Background color.
            is_chamfered: Whether to use chamfered style.
        """
        if glow_color is None:
            glow_color = SystemColors.AMBER_GLOW
        if fill_color is None:
            fill_color = SystemColors.HEALTH_MEDIUM
        if bg_color is None:
            bg_color = SystemColors.HEALTH_LOW

        # 首先渲染发光层 (from cache)
        glow_key = (self.width, self.height, glow_color)
        if glow_key not in self._rendered_cache:
            glow_rect = pygame.Rect(0, 0, self.width + 4, self.height + 4)
            glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
            glow_surf.fill((0, 0, 0, 0))
            pygame.draw.rect(glow_surf, glow_color, glow_surf.get_rect(), border_radius=2)
            self._rendered_cache[glow_key] = glow_surf
        surface.blit(self._rendered_cache[glow_key], (x - 2, y - 2))

        # 然后渲染进度条
        self.render(surface, x, y, value, max_value, fill_color, bg_color, SystemColors.SEGMENT_BORDER, is_chamfered)

    def render_danger_pulse(
        self, surface: pygame.Surface, x: int, y: int, value: float, max_value: float, pulse_alpha: int
    ) -> None:
        """Render a danger pulse effect for low health.

        Args:
            surface: Target surface.
            x: X coordinate.
            y: Y coordinate.
            value: Current value.
            max_value: Maximum value.
            pulse_alpha: Pulse opacity (0-255).
        """
        danger_color = SystemColors.DANGER_RED

        # 绘制普通进度条
        self.render(surface, x, y, value, max_value, danger_color, SystemColors.HEALTH_LOW)

        # 添加脉冲闪烁
        if pulse_alpha > 0:
            if self._pulse_surf is None or self._pulse_surf.get_size() != (self.width, self.height):
                self._pulse_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            self._pulse_surf.fill((0, 0, 0, 0))
            pygame.draw.rect(self._pulse_surf, (*danger_color, pulse_alpha), self._pulse_surf.get_rect())
            surface.blit(self._pulse_surf, (x, y))


class BossHealthBar:
    """Boss health bar component — military style."""

    def __init__(self, width: int = 600, height: int = 30):
        """Initialize the Boss health bar.

        Args:
            width: Total width.
            height: Bar height.
        """
        self.width = width
        self.height = height
        self.segment_count = 8  # 8 段 (每段 12.5%)
        self._default_font = get_cjk_font(20)
        self._text_cache: dict[str, tuple[str, pygame.Surface]] = {}
        self.progress_bar = SegmentedProgressBar(
            width - 24,  # 减去标签宽度
            height - 8,
            segments=self.segment_count,
            segment_gap=2,
        )

    def render(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        current_hp: float,
        max_hp: float,
        boss_name: str = "",
        current_phase: int = 1,
        total_phases: int = 3,
        font: pygame.font.Font | None = None,
    ) -> None:
        """Render the Boss health bar.

        Args:
            surface: Target surface.
            x: X coordinate.
            y: Y coordinate.
            current_hp: Current health points.
            max_hp: Maximum health points.
            boss_name: Boss display name.
            current_phase: Current phase number.
            total_phases: Total number of phases.
            font: Font to use.
        """
        if font is None:
            font = self._default_font

        # 标签区域 (左侧) — wider for CJK boss names
        label_width = 60
        bar_x = x + label_width
        bar_y = y + 4

        # 绘制血条背景
        bg_rect = pygame.Rect(bar_x, bar_y, self.width - label_width, self.height - 8)
        pygame.draw.rect(surface, SystemColors.BG_PANEL, bg_rect, border_radius=2)
        pygame.draw.rect(surface, SystemColors.BORDER_DIM, bg_rect, 1, border_radius=2)

        # 绘制分段血条
        ratio = min(current_hp / max_hp, 1.0) if max_hp > 0 else 0.0

        # 根据血量选择颜色
        if ratio > 0.6:
            fill_color = SystemColors.BOSS_BAR_FULL
        elif ratio > 0.3:
            fill_color = SystemColors.HEALTH_MEDIUM
        else:
            fill_color = SystemColors.HEALTH_LOW

        # 计算填充段数
        filled_segments = int(ratio * self.segment_count)

        # 绘制填充的段
        segment_width = (self.width - label_width - 16) / self.segment_count
        for i in range(filled_segments):
            seg_x = bar_x + 4 + i * (segment_width + 2)
            seg_rect = pygame.Rect(seg_x, bar_y + 4, segment_width, self.height - 16)
            pygame.draw.rect(surface, fill_color, seg_rect)

        # 绘制百分比
        percent_text = f"{int(ratio * 100)}%"
        text_surf = render_cached_text(font, percent_text, SystemColors.TEXT_PRIMARY, "percent", self._text_cache)
        text_rect = text_surf.get_rect(right=bar_x + self.width - label_width - 10, centery=y + self.height // 2)
        surface.blit(text_surf, text_rect)

        # 绘制阶段指示器
        if total_phases > 1:
            phase_text = f"阶段 {current_phase}/{total_phases}"
            phase_surf = render_cached_text(font, phase_text, SystemColors.AMBER_DIM, "phase", self._text_cache)
            phase_rect = phase_surf.get_rect(left=bar_x + 8, top=y - 22)
            surface.blit(phase_surf, phase_rect)

        # 绘制 Boss 名称
        if boss_name:
            name_surf = render_cached_text(font, boss_name, SystemColors.TEXT_PRIMARY, "boss_name", self._text_cache)
            name_rect = name_surf.get_rect(left=bar_x, centery=y + self.height // 2)
            surface.blit(name_surf, name_rect)
