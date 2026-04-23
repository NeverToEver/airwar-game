import pygame
import math
from airwar.config.design_tokens import get_design_tokens, MilitaryColors, MilitaryUI


class EffectsRenderer:
    """特效渲染器 — 负责发光文字等视觉效果"""

    def __init__(self):
        self._glow_cache = {}
        self._tokens = get_design_tokens()

    def render_glow_text(
        self,
        surface: pygame.Surface,
        text: str,
        font: pygame.font.Font,
        pos: tuple,
        color: tuple,
        glow_color: tuple,
        glow_radius: int = None
    ):
        """渲染发光文字"""
        if glow_radius is None:
            glow_radius = self._tokens.animation.GLOW_RADIUS_DEFAULT

        for i in range(glow_radius, 0, -1):
            alpha = int(100 / i)
            glow_surf = font.render(text, True, glow_color)
            glow_surf.set_alpha(alpha)
            glow_rect = glow_surf.get_rect(center=(pos[0], pos[1] + i))
            surface.blit(glow_surf, glow_rect)

        main_text = font.render(text, True, color)
        surface.blit(main_text, main_text.get_rect(center=pos))

    def render_option_box(
        self,
        surface: pygame.Surface,
        text: str,
        y: int,
        is_selected: bool,
        colors: dict,
        option_width: int = None,
        option_height: int = None,
        scale: float = 1.0
    ):
        """渲染选项框"""
        from airwar.utils.responsive import ResponsiveHelper

        if option_width is None:
            option_width = self._tokens.spacing.BOX_WIDTH
        if option_height is None:
            option_height = self._tokens.spacing.BOX_HEIGHT

        width = surface.get_width()
        center_x = width // 2

        box_width = ResponsiveHelper.scale(option_width, scale)
        box_height = ResponsiveHelper.scale(option_height, scale)
        box_rect = pygame.Rect(center_x - box_width // 2, y - box_height // 2, box_width, box_height)

        colors_config = self._tokens.colors
        if is_selected:
            glow_color = colors.get('selected_glow', colors_config.HUD_AMBER_BRIGHT)
            for i in range(4, 0, -1):
                glow_rect = box_rect.inflate(i * 4, i * 4)
                glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (*glow_color, 50 // i), glow_surf.get_rect())
                surface.blit(glow_surf, glow_rect)

            pygame.draw.rect(surface, colors_config.BUTTON_SELECTED_BG, box_rect, border_radius=12)
            pygame.draw.rect(surface, colors.get('selected', colors_config.HUD_AMBER), box_rect, 3, border_radius=12)
        else:
            pygame.draw.rect(surface, colors_config.BUTTON_UNSELECTED_BG, box_rect, border_radius=12)
            pygame.draw.rect(surface, colors.get('unselected', colors_config.TEXT_MUTED), box_rect, 2, border_radius=12)

        arrow = ">> " if is_selected else "   "
        option_text = pygame.font.Font(None, self._tokens.typography.OPTION_SIZE).render(f"{arrow}{text}", True,
            colors.get('selected', colors_config.HUD_AMBER) if is_selected else colors.get('unselected', colors_config.TEXT_MUTED))
        text_rect = option_text.get_rect(center=(center_x, y))
        surface.blit(option_text, text_rect)

    def render_chamfered_rect(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        width: int,
        height: int,
        bg_color: tuple = None,
        border_color: tuple = None,
        glow_color: tuple = None,
        glow_intensity: float = 1.0
    ):
        """渲染切角矩形面板（军事风格）

        Args:
            surface: 目标 surface
            x: 左上角 x 坐标
            y: 左上角 y 坐标
            width: 面板宽度
            height: 面板高度
            bg_color: 背景颜色
            border_color: 边框颜色
            glow_color: 发光颜色
            glow_intensity: 发光强度 0.0-1.0
        """
        if bg_color is None:
            bg_color = MilitaryColors.BG_PANEL
        if border_color is None:
            border_color = MilitaryColors.BORDER_GLOW
        if glow_color is None:
            glow_color = MilitaryColors.AMBER_GLOW

        chamfer = MilitaryUI.CHAMFER_DEPTH
        border_width = MilitaryUI.CHAMFER_BORDER_WIDTH

        # 绘制发光效果（如果启用）
        if glow_intensity > 0:
            glow_surf = pygame.Surface((width + 8, height + 8), pygame.SRCALPHA)
            glow_surf.fill((0, 0, 0, 0))

            # 计算发光多边形点
            gw, gh = width + 8, height + 8
            gch = chamfer + 4
            glow_points = [
                (gch, 0),
                (gw - gch, 0),
                (gw, gch),
                (gw, gh - gch),
                (gw - gch, gh),
                (gch, gh),
                (0, gh - gch),
                (0, gch),
            ]

            # 分层绘制发光
            for layer in range(3, 0, -1):
                alpha = int(30 * glow_intensity / layer)
                layer_color = (*glow_color[:3], alpha) if len(glow_color) == 4 else (*glow_color, alpha)
                pygame.draw.lines(glow_surf, layer_color, False, glow_points, border_width + layer)
                # 填充内部
                glow_fill = pygame.Surface((gw - 4, gh - 4), pygame.SRCALPHA)
                glow_fill.fill((0, 0, 0, 0))
                inner_points = [
                    (gch - 2, 2),
                    (gw - gch + 2, 2),
                    (gw - 2, gch - 2),
                    (gw - 2, gh - gch + 2),
                    (gw - gch + 2, gh - 2),
                    (gch - 2, gh - 2),
                    (2, gh - gch + 2),
                    (2, gch - 2),
                ]
                pygame.draw.polygon(glow_fill, (*glow_color[:3], alpha // 2), inner_points)
                glow_surf.blit(glow_fill, (2, 2))

            surface.blit(glow_surf, (x - 4, y - 4))

        # 绘制背景
        bg_surf = pygame.Surface((width, height), pygame.SRCALPHA)
        bg_surf.fill((0, 0, 0, 0))

        # 切角多边形
        points = [
            (chamfer, 0),
            (width - chamfer, 0),
            (width, chamfer),
            (width, height - chamfer),
            (width - chamfer, height),
            (chamfer, height),
            (0, height - chamfer),
            (0, chamfer),
        ]

        # 填充背景
        pygame.draw.polygon(bg_surf, bg_color if len(bg_color) == 3 else bg_color[:3], points)
        surface.blit(bg_surf, (x, y))

        # 绘制边框
        border_surf = pygame.Surface((width, height), pygame.SRCALPHA)
        border_surf.fill((0, 0, 0, 0))
        border_col = border_color if len(border_color) == 4 else (*border_color, 255)
        pygame.draw.lines(border_surf, border_col, False, points, border_width)
        surface.blit(border_surf, (x, y))

    def render_military_text(
        self,
        surface: pygame.Surface,
        text: str,
        font: pygame.font.Font,
        x: int,
        y: int,
        color: tuple = None,
        glow: bool = True
    ):
        """渲染军事风格文字（带发光）

        Args:
            surface: 目标 surface
            text: 文字内容
            font: 字体
            x: x 坐标
            y: y 坐标
            color: 文字颜色
            glow: 是否发光
        """
        if color is None:
            color = MilitaryColors.TEXT_PRIMARY

        if glow:
            # 发光层
            glow_color = MilitaryColors.AMBER_PRIMARY
            for i in range(3, 0, -1):
                alpha = int(60 / i)
                glow_surf = font.render(text, True, glow_color)
                glow_surf.set_alpha(alpha)
                glow_rect = glow_surf.get_rect(center=(x, y + i * 0.5))
                surface.blit(glow_surf, glow_rect)

        main_text = font.render(text, True, color)
        text_rect = main_text.get_rect(center=(x, y))
        surface.blit(main_text, text_rect)

    def render_scanline_overlay(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect = None,
        alpha: int = None
    ):
        """渲染扫描线覆盖效果

        Args:
            surface: 目标 surface
            rect: 覆盖区域，None 则覆盖整个 surface
            alpha: 扫描线透明度
        """
        if alpha is None:
            alpha = MilitaryUI.SCANLINE_ALPHA
        if rect is None:
            rect = surface.get_rect()

        # 每隔 SCANLINE_SPACING 像素画一条线
        for ly in range(rect.top, rect.bottom, MilitaryUI.SCANLINE_SPACING):
            pygame.draw.line(
                surface,
                (*MilitaryColors.AMBER_PRIMARY[:3], alpha),
                (rect.left, ly),
                (rect.right, ly)
            )
