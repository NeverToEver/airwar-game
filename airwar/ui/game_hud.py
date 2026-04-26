"""HUD 渲染器 - 整合所有 UI 组件"""
import pygame
from typing import Optional, Tuple, List
from airwar.config.design_tokens import SystemColors, SystemUI, get_design_tokens
from airwar.ui.chamfered_panel import draw_chamfered_panel
from airwar.ui.segmented_bar import SegmentedProgressBar
from airwar.ui.hex_icon import HexIcon, ICON_POWER, ICON_DEFENSE, ICON_SPEED, ICON_HEALTH, ICON_SHIELD


class GameHUD:
    """游戏内 HUD 渲染器"""

    def __init__(self):
        self._tokens = get_design_tokens()
        self._font_label = None
        self._font_value = None
        self._font_small = None
        self._init_fonts()

        # 组件
        self._health_bar = SegmentedProgressBar(200, 14, 10)
        self._coeff_bar = SegmentedProgressBar(80, 8, 8)

    def _init_fonts(self):
        """初始化字体"""
        self._font_label = pygame.font.Font(
            pygame.font.get_default_font(), SystemUI.HUD_LABEL_SIZE
        )
        self._font_value = pygame.font.Font(
            pygame.font.get_default_font(), SystemUI.HUD_VALUE_SIZE
        )
        self._font_small = pygame.font.Font(
            pygame.font.get_default_font(), SystemUI.HUD_SMALL_SIZE
        )
        self._font_title = pygame.font.Font(
            pygame.font.get_default_font(), SystemUI.HUD_TITLE_SIZE
        )

    def render_hud_frame(
        self,
        surface: pygame.Surface,
        screen_width: int,
        screen_height: int
    ) -> None:
        """渲染 HUD 框架装饰（顶部和底部线条）

        Args:
            surface: 目标 surface
            screen_width: 屏幕宽度
            screen_height: 屏幕高度
        """
        # 顶部装饰线
        line_y = 25
        line_margin = 50

        # 绘制顶部角落装饰
        self._draw_corner_decoration(surface, line_margin, line_y, False)
        self._draw_corner_decoration(surface, screen_width - line_margin, line_y, True)

        # 底部装饰线
        bottom_y = screen_height - 25
        self._draw_corner_decoration(surface, line_margin, bottom_y, False)
        self._draw_corner_decoration(surface, screen_width - line_margin, bottom_y, True)

    def _draw_corner_decoration(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        flip: bool = False
    ) -> None:
        """绘制角落装饰

        Args:
            surface: 目标 surface
            x: x 坐标
            y: y 坐标
            flip: 是否翻转
        """
        w = 1 if not flip else -1
        length = 30

        points = [
            (x, y),
            (x + length * w, y),
            (x + length * w, y - 5),
        ]

        pygame.draw.lines(surface, SystemColors.BORDER_DIM, flip, points, 1)

    def render_top_bar(
        self,
        surface: pygame.Surface,
        score: int,
        milestone_progress: float,
        kills: int,
        boss_kills: int,
        milestone_max: float = 10000.0,
        x: int = None,
        y: int = 30
    ) -> None:
        """渲染顶部信息条

        Args:
            surface: 目标 surface
            score: 当前分数
            milestone_progress: 里程碑进度 (0-1)
            kills: 击杀数
            boss_kills: BOSS 击杀数
            milestone_max: 里程碑最大值
            x: x 坐标，None 则居中
            y: y 坐标
        """
        screen_width = surface.get_width()
        bar_width = 600
        bar_height = 35

        if x is None:
            x = (screen_width - bar_width) // 2

        # 绘制面板背景
        draw_chamfered_panel(
            surface, x, y, bar_width, bar_height,
            SystemColors.BG_PANEL,
            SystemColors.BORDER_GLOW,
            SystemColors.ACCENT_GLOW
        )

        # 信息布局
        padding = 20
        segment_width = (bar_width - padding * 2) // 4

        # 分数
        score_text = f"SCORE: {score:,}"
        score_surf = self._font_value.render(score_text, True, SystemColors.ACCENT_PRIMARY)
        score_rect = score_surf.get_rect(left=x + padding, centery=y + bar_height // 2)
        surface.blit(score_surf, score_rect)

        # 里程碑进度
        milestone_text = f"MILESTONE: {int(milestone_progress * 100)}%"
        milestone_surf = self._font_small.render(milestone_text, True, SystemColors.TEXT_DIM)
        milestone_rect = milestone_surf.get_rect(
            left=x + padding + segment_width,
            centery=y + bar_height // 2 - 4
        )
        surface.blit(milestone_surf, milestone_rect)

        # 里程碑进度条
        self._health_bar.render(
            surface,
            x + padding + segment_width,
            y + bar_height // 2 + 6,
            milestone_progress * milestone_max,
            milestone_max,
            SystemColors.ACCENT_PRIMARY,
            SystemColors.BG_PANEL_LIGHT,
            SystemColors.ACCENT_DIM
        )

        # 击杀数
        kills_text = f"KILLS: {kills}"
        kills_surf = self._font_value.render(kills_text, True, SystemColors.TEXT_PRIMARY)
        kills_rect = kills_surf.get_rect(
            left=x + padding + segment_width * 2,
            centery=y + bar_height // 2
        )
        surface.blit(kills_surf, kills_rect)

        # BOSS 击杀
        boss_text = f" BOSS: {boss_kills}"
        boss_surf = self._font_value.render(boss_text, True, SystemColors.DANGER_RED)
        boss_rect = boss_surf.get_rect(
            left=x + padding + segment_width * 3,
            centery=y + bar_height // 2
        )
        surface.blit(boss_surf, boss_rect)

    def render_health_panel(
        self,
        surface: pygame.Surface,
        health: float,
        max_health: float,
        x: int = 20,
        y: int = None
    ) -> None:
        """渲染左下角生命值面板

        Args:
            surface: 目标 surface
            health: 当前生命值
            max_health: 最大生命值
            x: x 坐标
            y: y 坐标
        """
        screen_height = surface.get_height()
        if y is None:
            y = screen_height - 80

        panel_width = 250
        panel_height = 60

        # 绘制面板
        draw_chamfered_panel(
            surface, x, y, panel_width, panel_height,
            SystemColors.BG_PANEL,
            SystemColors.BORDER_GLOW
        )

        padding = 15

        # 生命值图标 + 文字
        hp_icon = HexIcon(ICON_HEALTH, 14, fill_color=SystemColors.HEALTH_FULL)
        hp_icon.render(surface, (x + padding + 10, y + 20))

        # 标签
        hp_label = self._font_small.render("HP", True, SystemColors.TEXT_DIM)
        surface.blit(hp_label, (x + padding + 28, y + 12))

        # 生命值数值
        hp_value = self._font_value.render(f"{int(health)}", True, SystemColors.HEALTH_FULL)
        surface.blit(hp_value, (x + padding + 50, y + 10))

        # 生命值进度条
        bar_x = x + padding
        bar_y = y + 38
        bar_width = panel_width - padding * 2
        bar_height = 12

        # 根据血量选择颜色
        ratio = health / max_health if max_health > 0 else 0
        if ratio > 0.6:
            fill_color = SystemColors.HEALTH_FULL
        elif ratio > 0.3:
            fill_color = SystemColors.HEALTH_MEDIUM
        else:
            fill_color = SystemColors.HEALTH_LOW

        # 分段进度条
        health_bar = SegmentedProgressBar(bar_width, bar_height, 10)
        health_bar.render(
            surface, bar_x, bar_y,
            health, max_health,
            fill_color,
            SystemColors.BG_PANEL_LIGHT,
            SystemColors.SEGMENT_BORDER,
            is_chamfered=True
        )

        # 百分比
        percent_text = f"{int(ratio * 100)}%"
        percent_surf = self._font_small.render(percent_text, True, SystemColors.TEXT_DIM)
        percent_rect = percent_surf.get_rect(right=x + panel_width - padding, centery=y + 20)
        surface.blit(percent_surf, percent_rect)

    def render_difficulty_panel(
        self,
        surface: pygame.Surface,
        difficulty: str,
        coefficient: float,
        x: int = None,
        y: int = None
    ) -> None:
        """渲染右下角难度信息面板

        Args:
            surface: 目标 surface
            difficulty: 难度名称
            coefficient: 难度系数
            x: x 坐标，None 则右对齐
            y: y 坐标
        """
        screen_width = surface.get_width()
        screen_height = surface.get_height()

        panel_width = 180
        panel_height = 60

        if x is None:
            x = screen_width - panel_width - 20
        if y is None:
            y = screen_height - 80

        # 绘制面板
        draw_chamfered_panel(
            surface, x, y, panel_width, panel_height,
            SystemColors.BG_PANEL,
            SystemColors.BORDER_GLOW
        )

        padding = 15

        # COEFF 标签
        coeff_label = self._font_small.render("COEFF", True, SystemColors.TEXT_DIM)
        surface.blit(coeff_label, (x + padding, y + padding))

        # COEFF 数值
        coeff_value = self._font_value.render(f"{coefficient:.1f}x", True, SystemColors.ACCENT_PRIMARY)
        surface.blit(coeff_value, (x + padding, y + padding + 18))

        # 难度标签
        diff_label = self._font_small.render("DIFFICULTY", True, SystemColors.TEXT_DIM)
        surface.blit(diff_label, (x + padding, y + 42))

        # 难度名称
        diff_color = SystemColors.TEXT_PRIMARY
        if difficulty.upper() == "HARD":
            diff_color = SystemColors.DANGER_RED
        elif difficulty.upper() == "MEDIUM":
            diff_color = SystemColors.ACCENT_PRIMARY

        diff_value = self._font_value.render(difficulty.upper(), True, diff_color)
        surface.blit(diff_value, (x + padding + 80, y + 38))

    def render_buff_panel(
        self,
        surface: pygame.Surface,
        buffs: List[dict],
        x: int = None,
        y: int = 30
    ) -> None:
        """渲染右侧 Buff 状态面板

        Args:
            surface: 目标 surface
            buffs: Buff 列表，每项包含 type, level, max_level
            x: x 坐标，None 则右对齐
            y: y 坐标
        """
        if not buffs:
            return

        screen_width = surface.get_width()

        panel_width = 120
        panel_height = 30 + len(buffs) * 45 + 15

        if x is None:
            x = screen_width - panel_width - 15

        # 绘制面板
        draw_chamfered_panel(
            surface, x, y, panel_width, panel_height,
            SystemColors.BG_PANEL,
            SystemColors.BORDER_GLOW
        )

        # 标题
        title = self._font_small.render("ACTIVE", True, SystemColors.TEXT_DIM)
        surface.blit(title, (x + 10, y + 8))

        # 绘制每个 buff
        for i, buff in enumerate(buffs):
            buff_y = y + 30 + i * 45
            buff_type = buff.get('type', ICON_POWER)
            level = buff.get('level', 1)
            max_level = buff.get('max_level', 5)
            is_max = level >= max_level

            # 图标
            icon = HexIcon(buff_type, 16, is_max_level=is_max)
            icon.render(surface, (x + 20, buff_y + 12))

            # Buff 名称和等级
            buff_label = self._font_small.render(buff.get('name', 'BUFF'), True, SystemColors.TEXT_PRIMARY)
            surface.blit(buff_label, (x + 42, buff_y + 2))

            level_text = f"+{level}"
            level_color = SystemColors.ACCENT_BRIGHT if is_max else SystemColors.ACCENT_PRIMARY
            level_surf = self._font_small.render(level_text, True, level_color)
            surface.blit(level_surf, (x + 42, buff_y + 18))

    def render_milestone_bar(
        self,
        surface: pygame.Surface,
        current_score: int,
        next_milestone: int,
        x: int = None,
        y: int = None
    ) -> None:
        """渲染里程碑进度条

        Args:
            surface: 目标 surface
            current_score: 当前分数
            next_milestone: 下一个里程碑分数
            x: x 坐标，None 则居中
            y: y 坐标
        """
        screen_width = surface.get_width()
        screen_height = surface.get_height()

        bar_width = 400
        bar_height = 40

        if x is None:
            x = (screen_width - bar_width) // 2
        if y is None:
            y = screen_height - 100

        # 计算进度
        prev_milestone = next_milestone / 1.5  # Approximate previous milestone
        progress = (current_score - prev_milestone) / (next_milestone - prev_milestone)
        progress = max(0.0, min(1.0, progress))

        # 绘制面板
        draw_chamfered_panel(
            surface, x, y, bar_width, bar_height,
            SystemColors.BG_PANEL,
            SystemColors.BORDER_GLOW,
            SystemColors.ACCENT_GLOW,
            chamfer_depth=10
        )

        # 标签
        label_text = self._font_small.render("NEXT REWARD:", True, SystemColors.TEXT_DIM)
        surface.blit(label_text, (x + 15, y + 8))

        # 进度条
        bar_x = x + 15
        bar_y = y + 25
        bar_width_inner = bar_width - 30

        milestone_bar = SegmentedProgressBar(bar_width_inner, 10, 10)
        milestone_bar.render(
            surface, bar_x, bar_y,
            progress * 100, 100,
            SystemColors.ACCENT_PRIMARY,
            SystemColors.BG_PANEL_LIGHT,
            SystemColors.ACCENT_DIM,
            is_chamfered=True
        )

        # 百分比
        percent_text = f"{int(progress * 100)}%"
        percent_surf = self._font_small.render(percent_text, True, SystemColors.ACCENT_PRIMARY)
        percent_rect = percent_surf.get_rect(right=x + bar_width - 15, centery=y + bar_height // 2)
        surface.blit(percent_surf, percent_rect)

    def render_complete_hud(
        self,
        surface: pygame.Surface,
        score: int,
        health: float,
        max_health: float,
        kills: int,
        boss_kills: int,
        difficulty: str,
        coefficient: float,
        milestone_progress: float = 0.0,
        buffs: List[dict] = None,
        milestone_max: float = 10000.0
    ) -> None:
        """渲染完整的 HUD（便捷方法）

        Args:
            surface: 目标 surface
            score: 当前分数
            health: 当前生命值
            max_health: 最大生命值
            kills: 击杀数
            boss_kills: BOSS 击杀数
            difficulty: 难度名称
            coefficient: 难度系数
            milestone_progress: 里程碑进度 (0-1)
            buffs: Buff 列表
            milestone_max: 里程碑最大值
        """
        screen_width = surface.get_width()
        screen_height = surface.get_height()

        # 渲染框架装饰
        self.render_hud_frame(surface, screen_width, screen_height)

        # 渲染顶部信息条
        self.render_top_bar(
            surface, score, milestone_progress, kills, boss_kills, milestone_max
        )

        # 渲染左下生命值
        self.render_health_panel(surface, health, max_health)

        # 渲染右下难度信息
        self.render_difficulty_panel(surface, difficulty, coefficient)

        # 渲染 Buff 面板
        if buffs:
            self.render_buff_panel(surface, buffs)
