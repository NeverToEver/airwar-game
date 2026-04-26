"""分段进度条组件 - 军事风格 HUD"""
import pygame
from typing import Optional, Tuple
from airwar.config.design_tokens import SystemColors, SystemUI


class SegmentedProgressBar:
    """分段进度条组件，支持军事风格样式"""

    def __init__(
        self,
        width: int,
        height: int = 16,
        segments: int = 10,
        segment_gap: int = None
    ):
        """初始化分段进度条

        Args:
            width: 总宽度
            height: 条高度
            segments: 分段数量
            segment_gap: 段间距
        """
        self.width = width
        self.height = height
        self.segments = segments
        self.segment_gap = segment_gap or SystemUI.SEGMENT_GAP
        self.segment_width = (width - (segments - 1) * self.segment_gap) // segments
        self._rendered_cache = {}

    def render(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        value: float,
        max_value: float,
        fill_color: Tuple[int, int, int] = None,
        bg_color: Tuple[int, int, int] = None,
        border_color: Tuple[int, int, int] = None,
        is_chamfered: bool = False
    ) -> None:
        """渲染分段进度条

        Args:
            surface: 目标 surface
            x: x 坐标
            y: y 坐标
            value: 当前值
            max_value: 最大值
            fill_color: 填充颜色
            bg_color: 背景颜色
            border_color: 边框颜色
            is_chamfered: 是否使用切角样式
        """
        if fill_color is None:
            fill_color = SystemColors.HEALTH_MEDIUM
        if bg_color is None:
            bg_color = SystemColors.HEALTH_LOW
        if border_color is None:
            border_color = SystemColors.SEGMENT_BORDER

        ratio = min(max(value / max_value, 0.0), 1.0)
        filled_count = int(ratio * self.segments)

        # 绘制每个段
        for i in range(self.segments):
            seg_x = x + i * (self.segment_width + self.segment_gap)
            seg_rect = pygame.Rect(seg_x, y, self.segment_width, self.height)

            if i < filled_count:
                # 填充段
                if is_chamfered:
                    self._draw_chamfered_segment(
                        surface, seg_rect, fill_color, border_color
                    )
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
        fill_color: Tuple[int, int, int],
        border_color: Tuple[int, int, int]
    ) -> None:
        """绘制切角段"""
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
        glow_color: Tuple[int, int, int, int] = None,
        fill_color: Tuple[int, int, int] = None,
        bg_color: Tuple[int, int, int] = None,
        is_chamfered: bool = False
    ) -> None:
        """渲染带发光效果的进度条

        Args:
            surface: 目标 surface
            x: x 坐标
            y: y 坐标
            value: 当前值
            max_value: 最大值
            glow_color: 发光颜色
            fill_color: 填充颜色
            bg_color: 背景颜色
            is_chamfered: 是否使用切角样式
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
        self.render(
            surface, x, y, value, max_value,
            fill_color, bg_color, SystemColors.SEGMENT_BORDER, is_chamfered
        )

    def render_danger_pulse(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        value: float,
        max_value: float,
        pulse_alpha: int
    ) -> None:
        """渲染危险状态脉冲效果（用于低血量）

        Args:
            surface: 目标 surface
            x: x 坐标
            y: y 坐标
            value: 当前值
            max_value: 最大值
            pulse_alpha: 脉冲透明度 0-255
        """
        danger_color = SystemColors.DANGER_RED

        # 绘制普通进度条
        self.render(surface, x, y, value, max_value, danger_color, SystemColors.HEALTH_LOW)

        # 添加脉冲闪烁
        if pulse_alpha > 0:
            if not hasattr(self, '_pulse_surf') or self._pulse_surf.get_size() != (self.width, self.height):
                self._pulse_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            self._pulse_surf.fill((0, 0, 0, 0))
            pygame.draw.rect(self._pulse_surf, (*danger_color, pulse_alpha), self._pulse_surf.get_rect())
            surface.blit(self._pulse_surf, (x, y))


class BossHealthBar:
    """Boss 血条组件 - 军事风格"""

    def __init__(self, width: int = 600, height: int = 30):
        """初始化 Boss 血条

        Args:
            width: 总宽度
            height: 条高度
        """
        self.width = width
        self.height = height
        self.segment_count = 8  # 8 段 (每段 12.5%)
        self.progress_bar = SegmentedProgressBar(
            width - 24,  # 减去标签宽度
            height - 8,
            segments=self.segment_count,
            segment_gap=2
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
        font: pygame.font.Font = None
    ) -> None:
        """渲染 Boss 血条

        Args:
            surface: 目标 surface
            x: x 坐标
            y: y 坐标
            current_hp: 当前血量
            max_hp: 最大血量
            boss_name: Boss 名称
            current_phase: 当前阶段
            total_phases: 总阶段数
            font: 字体
        """
        if font is None:
            font = pygame.font.Font(pygame.font.get_default_font(), 20)

        # 标签区域 (左侧)
        label_width = 24
        bar_x = x + label_width
        bar_y = y + 4

        # 绘制血条背景
        bg_rect = pygame.Rect(bar_x, bar_y, self.width - label_width, self.height - 8)
        pygame.draw.rect(surface, SystemColors.BG_PANEL, bg_rect, border_radius=2)
        pygame.draw.rect(surface, SystemColors.BORDER_DIM, bg_rect, 1, border_radius=2)

        # 绘制分段血条
        ratio = min(current_hp / max_hp, 1.0)

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
        text_surf = font.render(percent_text, True, SystemColors.TEXT_PRIMARY)
        text_rect = text_surf.get_rect(right=bar_x + self.width - label_width - 10,
                                       centery=y + self.height // 2)
        surface.blit(text_surf, text_rect)

        # 绘制阶段指示器
        if total_phases > 1:
            phase_text = f"PHASE {current_phase}/{total_phases}"
            phase_surf = font.render(phase_text, True, SystemColors.AMBER_DIM)
            phase_rect = phase_surf.get_rect(right=bar_x + self.width - label_width - 10,
                                            top=y - 22)
            surface.blit(phase_surf, phase_rect)

        # 绘制 Boss 名称
        if boss_name:
            name_surf = font.render(boss_name, True, SystemColors.TEXT_PRIMARY)
            name_rect = name_surf.get_rect(left=bar_x,
                                          centery=y + self.height // 2)
            surface.blit(name_surf, name_rect)
