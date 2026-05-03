"""六边形图标组件 - 军事风格 HUD"""
import pygame
import math
from typing import Tuple
from airwar.config.design_tokens import SystemColors, SystemUI


# Icon types as constants
ICON_POWER = "power"
ICON_DEFENSE = "defense"
ICON_SPEED = "speed"
ICON_LASER = "laser"
ICON_MISSILE = "missile"
ICON_HEALTH = "health"
ICON_SHIELD = "shield"
ICON_STAR = "star"


# Color mapping for icon types
ICON_COLORS = {
    ICON_POWER: SystemColors.ICON_POWER,
    ICON_DEFENSE: SystemColors.ICON_DEFENSE,
    ICON_SPEED: SystemColors.ICON_SPEED,
    ICON_LASER: SystemColors.ICON_LASER,
    ICON_MISSILE: SystemColors.ICON_MISSILE,
    ICON_HEALTH: SystemColors.HEALTH_FULL,
    ICON_SHIELD: SystemColors.ICON_DEFENSE,
    ICON_STAR: SystemColors.AMBER_BRIGHT,
}


def _get_hexagon_points(center: Tuple[float, float], size: float, pointy_top: bool = True) -> list:
    """计算六边形的6个顶点

    Args:
        center: 中心点坐标 (x, y)
        size: 六边形外接圆半径
        pointy_top: True 为尖顶朝上, False 为平顶朝上

    Returns:
        6个顶点坐标列表
    """
    points = []
    for i in range(6):
        angle = math.radians(60 * i - 30) if pointy_top else math.radians(60 * i)
        x = center[0] + size * math.cos(angle)
        y = center[1] + size * math.sin(angle)
        points.append((x, y))
    return points


def draw_hexagon(
    surface: pygame.Surface,
    center: Tuple[float, float],
    size: float,
    fill_color: Tuple[int, int, int],
    border_color: Tuple[int, int, int, int] = None,
    border_width: int = 2,
    glow_color: Tuple[int, int, int, int] = None,
    pointy_top: bool = True
) -> None:
    """绘制六边形

    Args:
        surface: 目标 surface
        center: 中心点坐标
        size: 六边形外接圆半径
        fill_color: 填充颜色
        border_color: 边框颜色 (RGBA)
        border_width: 边框宽度
        glow_color: 发光颜色 (RGBA)
        pointy_top: 是否尖顶朝上
    """
    points = _get_hexagon_points(center, size, pointy_top)

    # 绘制发光效果
    if glow_color is not None:
        for layer in range(3, 0, -1):
            layer_size = size + layer * 2
            layer_points = _get_hexagon_points(center, layer_size, pointy_top)
            alpha = int(glow_color[3] / layer)
            layer_color = (*glow_color[:3], alpha)
            pygame.draw.polygon(surface, layer_color, layer_points)

    # 绘制填充
    if len(fill_color) == 4 and fill_color[3] == 0:
        # 完全透明，绘制轮廓
        pass
    else:
        pygame.draw.polygon(surface, fill_color, points)

    # 绘制边框
    if border_color is not None:
        border_col = border_color if len(border_color) == 4 else (*border_color, 255)
        pygame.draw.lines(surface, border_col, False, points, border_width)


def draw_icon(
    surface: pygame.Surface,
    icon_type: str,
    center: Tuple[float, float],
    size: float,
    color: Tuple[int, int, int] = None,
    glow: bool = False
) -> None:
    """绘制图标符号

    Args:
        surface: 目标 surface
        icon_type: 图标类型 (ICON_POWER, ICON_DEFENSE 等)
        center: 中心点坐标
        size: 图标大小
        color: 颜色，默认根据类型自动选择
        glow: 是否发光
    """
    if color is None:
        color = ICON_COLORS.get(icon_type, SystemColors.AMBER_PRIMARY)

    # 设置线条宽度
    line_width = max(2, int(size / 6))

    if glow:
        for layer in range(2, 0, -1):
            layer_color = (*color[:3], int(50 / layer))
            _draw_icon_shape(surface, icon_type, center, size + layer, layer_color, line_width)

    _draw_icon_shape(surface, icon_type, center, size, color, line_width)


def _draw_icon_shape(
    surface: pygame.Surface,
    icon_type: str,
    center: Tuple[float, float],
    size: float,
    color: Tuple[int, int, int],
    line_width: int
) -> None:
    """绘制图标形状"""
    cx, cy = center

    if icon_type == ICON_POWER:
        # 闪电符号
        points = [
            (cx + size * 0.3, cy - size * 0.5),
            (cx - size * 0.1, cy),
            (cx + size * 0.1, cy),
            (cx - size * 0.3, cy + size * 0.5),
            (cx + size * 0.1, cy + size * 0.1),
            (cx - size * 0.1, cy + size * 0.1),
        ]
        pygame.draw.polygon(surface, color, points)

    elif icon_type == ICON_DEFENSE:
        # 盾牌符号
        points = [
            (cx, cy - size * 0.5),
            (cx + size * 0.4, cy - size * 0.3),
            (cx + size * 0.4, cy + size * 0.1),
            (cx, cy + size * 0.5),
            (cx - size * 0.4, cy + size * 0.1),
            (cx - size * 0.4, cy - size * 0.3),
        ]
        pygame.draw.polygon(surface, color, points, line_width)

    elif icon_type == ICON_SPEED:
        # 箭头/速度符号
        points = [
            (cx + size * 0.4, cy - size * 0.4),
            (cx + size * 0.4, cy - size * 0.1),
            (cx + size * 0.1, cy - size * 0.1),
            (cx + size * 0.1, cy + size * 0.4),
            (cx - size * 0.1, cy + size * 0.2),
            (cx + size * 0.2, cy + size * 0.2),
            (cx - size * 0.4, cy - size * 0.4),
            (cx + size * 0.1, cy - size * 0.4),
        ]
        pygame.draw.polygon(surface, color, points)

    elif icon_type == ICON_LASER:
        # 激光符号 - 两条交叉线
        pygame.draw.line(surface, color, (cx - size * 0.3, cy), (cx + size * 0.3, cy), line_width)
        pygame.draw.line(surface, color, (cx, cy - size * 0.3), (cx, cy + size * 0.3), line_width)
        # 端点圆圈
        pygame.draw.circle(surface, color, (int(cx - size * 0.3), int(cy)), line_width)
        pygame.draw.circle(surface, color, (int(cx + size * 0.3), int(cy)), line_width)
        pygame.draw.circle(surface, color, (int(cx), int(cy - size * 0.3)), line_width)
        pygame.draw.circle(surface, color, (int(cx), int(cy + size * 0.3)), line_width)

    elif icon_type == ICON_MISSILE:
        # 导弹符号
        points = [
            (cx, cy - size * 0.5),
            (cx + size * 0.2, cy + size * 0.1),
            (cx + size * 0.1, cy + size * 0.1),
            (cx + size * 0.1, cy + size * 0.5),
            (cx - size * 0.1, cy + size * 0.5),
            (cx - size * 0.1, cy + size * 0.1),
            (cx - size * 0.2, cy + size * 0.1),
        ]
        pygame.draw.polygon(surface, color, points)
        # 火焰
        pygame.draw.polygon(surface, SystemColors.DANGER_RED, [
            (cx, cy + size * 0.5),
            (cx + size * 0.08, cy + size * 0.35),
            (cx - size * 0.08, cy + size * 0.35),
        ])

    elif icon_type == ICON_HEALTH:
        # 加号/医疗符号
        pygame.draw.rect(surface, color,
                        (cx - line_width, cy - size * 0.4, line_width * 2, size * 0.8))
        pygame.draw.rect(surface, color,
                        (cx - size * 0.4, cy - line_width, size * 0.8, line_width * 2))

    elif icon_type == ICON_SHIELD:
        # 小盾牌
        points = [
            (cx, cy - size * 0.4),
            (cx + size * 0.3, cy - size * 0.2),
            (cx + size * 0.3, cy + size * 0.2),
            (cx, cy + size * 0.4),
            (cx - size * 0.3, cy + size * 0.2),
            (cx - size * 0.3, cy - size * 0.2),
        ]
        pygame.draw.polygon(surface, color, points, line_width)

    elif icon_type == ICON_STAR:
        # 星形
        points = []
        for i in range(5):
            outer_angle = math.radians(72 * i - 90)
            inner_angle = math.radians(72 * i - 90 + 36)
            points.append((cx + size * 0.5 * math.cos(outer_angle),
                         cy + size * 0.5 * math.sin(outer_angle)))
            points.append((cx + size * 0.25 * math.cos(inner_angle),
                         cy + size * 0.25 * math.sin(inner_angle)))
        pygame.draw.polygon(surface, color, points)

    else:
        # 默认：绘制空心圆
        pygame.draw.circle(surface, color, (int(cx), int(cy)), int(size * 0.4), line_width)


class HexIcon:
    """六边形图标组件"""

    def __init__(
        self,
        icon_type: str = ICON_POWER,
        size: float = SystemUI.HEXAGON_SIZE,
        fill_color: Tuple[int, int, int] = None,
        border_color: Tuple[int, int, int, int] = None,
        glow_color: Tuple[int, int, int, int] = None,
        is_active: bool = True,
        is_max_level: bool = False
    ):
        """初始化六边形图标

        Args:
            icon_type: 图标类型
            size: 图标大小
            fill_color: 填充颜色
            border_color: 边框颜色
            glow_color: 发光颜色
            is_active: 是否激活
            is_max_level: 是否满级（显示金色高亮）
        """
        self.icon_type = icon_type
        self.size = size
        self.fill_color = fill_color or SystemColors.BG_PANEL_LIGHT
        self.border_color = border_color or SystemColors.BORDER_GLOW
        self.glow_color = glow_color or SystemColors.AMBER_GLOW
        self.is_active = is_active
        self.is_max_level = is_max_level

    def render(
        self,
        surface: pygame.Surface,
        center: Tuple[float, float],
        icon_color: Tuple[int, int, int] = None
    ) -> None:
        """渲染图标

        Args:
            surface: 目标 surface
            center: 中心点坐标
            icon_color: 图标颜色，默认根据类型自动选择
        """
        if icon_color is None:
            icon_color = ICON_COLORS.get(self.icon_type, SystemColors.AMBER_PRIMARY)

        # 满级时使用金色边框
        if self.is_max_level:
            border_color = SystemColors.AMBER_BRIGHT
            glow_color = (*SystemColors.AMBER_BRIGHT, 80)
        elif self.is_active:
            border_color = self.border_color
            glow_color = self.glow_color
        else:
            border_color = SystemColors.BORDER_DIM
            glow_color = None

        # 绘制六边形底
        draw_hexagon(
            surface, center, self.size,
            self.fill_color,
            border_color=border_color,
            border_width=SystemUI.HEXAGON_BORDER_WIDTH,
            glow_color=glow_color if self.is_active else None
        )

        # 绘制图标
        icon_size = self.size * 0.5
        icon_center = center  # 图标在六边形中心

        if self.is_active:
            draw_icon(surface, self.icon_type, icon_center, icon_size, icon_color, glow=False)
        else:
            # 非激活状态，绘制暗淡版本
            dim_color = (*icon_color[:3], 100) if len(icon_color) == 4 else icon_color
            draw_icon(surface, self.icon_type, icon_center, icon_size, dim_color, glow=False)

    def render_with_label(
        self,
        surface: pygame.Surface,
        center: Tuple[float, float],
        label: str,
        font: pygame.font.Font,
        level: int = None,
        icon_color: Tuple[int, int, int] = None
    ) -> None:
        """渲染图标和标签

        Args:
            surface: 目标 surface
            center: 中心点坐标
            label: 标签文字
            font: 字体
            level: 等级数字
            icon_color: 图标颜色
        """
        # 渲染图标
        self.render(surface, center, icon_color)

        # 渲染等级数字（如果提供）
        if level is not None and level > 0:
            level_text = f"+{level}"
            level_surf = font.render(level_text, True, SystemColors.AMBER_BRIGHT)
            level_rect = level_surf.get_rect(center=(center[0] + self.size * 0.6,
                                                    center[1] + self.size * 0.6))
            surface.blit(level_surf, level_rect)
