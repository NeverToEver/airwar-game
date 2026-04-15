import pygame
import math
import random


def create_gradient_surface(width: int, height: int, color1: tuple, color2: tuple, vertical: bool = True) -> pygame.Surface:
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    for i in range(height if vertical else width):
        ratio = i / (height if vertical else width)
        r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
        g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
        b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
        color = (r, g, b, 255)
        if vertical:
            pygame.draw.line(surface, color, (0, i), (width, i))
        else:
            pygame.draw.line(surface, color, (i, 0), (i, height))
    return surface


def draw_glow_circle(surface: pygame.Surface, center: tuple, radius: int, color: tuple, glow_radius: int = 0) -> None:
    if glow_radius > 0:
        for i in range(glow_radius, 0, -2):
            alpha = int(80 * (1 - i / glow_radius))
            glow_color = (*color[:3], alpha) if len(color) == 4 else (*color, alpha)
            glow_surf = pygame.Surface((i * 2 + 4, i * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, glow_color, (i + 2, i + 2), i)
            surface.blit(glow_surf, (center[0] - i - 2, center[1] - i - 2))
    pygame.draw.circle(surface, color, center, radius)


def draw_player_ship(surface: pygame.Surface, x: float, y: float, width: float = 50, height: float = 60) -> None:
    """绘制 B2 风格飞翼隐形战机 - 科幻飞翼布局"""
    center_x = x + width / 2
    center_y = y + height / 2
    
    hull_dark = (35, 60, 100)
    hull_mid = (55, 100, 160)
    hull_light = (85, 140, 200)
    hull_highlight = (130, 180, 230)
    
    glow_cyan = (80, 220, 255)
    glow_blue = (60, 180, 255)
    thruster_glow = (100, 200, 255)
    thruster_deep = (50, 150, 220)
    
    wing_edge_left = [
        (center_x - width * 0.08, y + height * 0.05),
        (x - width * 0.55, y + height * 0.65),
        (x - width * 0.35, y + height * 0.75),
        (x - width * 0.15, y + height * 0.55),
    ]
    pygame.draw.polygon(surface, hull_dark, wing_edge_left)
    
    wing_front_left = [
        (center_x - width * 0.08, y + height * 0.05),
        (x - width * 0.15, y + height * 0.55),
        (x - width * 0.05, y + height * 0.4),
        (center_x - width * 0.12, y + height * 0.25),
    ]
    pygame.draw.polygon(surface, hull_mid, wing_front_left)
    
    wing_top_left = [
        (center_x - width * 0.12, y + height * 0.25),
        (x - width * 0.05, y + height * 0.4),
        (x + width * 0.1, y + height * 0.38),
        (center_x - width * 0.15, y + height * 0.3),
    ]
    pygame.draw.polygon(surface, hull_light, wing_top_left)
    
    wing_edge_right = [
        (center_x + width * 0.08, y + height * 0.05),
        (x + width + width * 0.55, y + height * 0.65),
        (x + width + width * 0.35, y + height * 0.75),
        (x + width + width * 0.15, y + height * 0.55),
    ]
    pygame.draw.polygon(surface, hull_dark, wing_edge_right)
    
    wing_front_right = [
        (center_x + width * 0.08, y + height * 0.05),
        (x + width + width * 0.15, y + height * 0.55),
        (x + width + width * 0.05, y + height * 0.4),
        (center_x + width * 0.12, y + height * 0.25),
    ]
    pygame.draw.polygon(surface, hull_mid, wing_front_right)
    
    wing_top_right = [
        (center_x + width * 0.12, y + height * 0.25),
        (x + width + width * 0.05, y + height * 0.4),
        (x + width - width * 0.1, y + height * 0.38),
        (center_x + width * 0.15, y + height * 0.3),
    ]
    pygame.draw.polygon(surface, hull_light, wing_top_right)
    
    core_body = [
        (center_x - width * 0.08, y + height * 0.3),
        (x + width * 0.08, y + height * 0.3),
        (x + width * 0.12, y + height * 0.65),
        (center_x, y + height * 0.85),
        (x + width * 0.88, y + height * 0.65),
        (x + width * 0.92, y + height * 0.3),
    ]
    pygame.draw.polygon(surface, hull_dark, core_body)
    
    body_middle = [
        (center_x - width * 0.05, y + height * 0.35),
        (x + width * 0.05, y + height * 0.35),
        (x + width * 0.08, y + height * 0.6),
        (center_x, y + height * 0.75),
        (x + width * 0.92, y + height * 0.6),
        (x + width * 0.95, y + height * 0.35),
    ]
    pygame.draw.polygon(surface, hull_mid, body_middle)
    
    body_upper = [
        (center_x - width * 0.03, y + height * 0.38),
        (x + width * 0.03, y + height * 0.38),
        (x + width * 0.05, y + height * 0.55),
        (center_x, y + height * 0.65),
        (x + width * 0.95, y + height * 0.55),
        (x + width * 0.97, y + height * 0.38),
    ]
    pygame.draw.polygon(surface, hull_light, body_upper)
    
    center_line_left = [
        (center_x - width * 0.02, y + height * 0.4),
        (center_x - width * 0.01, y + height * 0.6),
        (center_x, y + height * 0.68),
    ]
    pygame.draw.polygon(surface, glow_cyan, center_line_left)
    
    center_line_right = [
        (center_x + width * 0.02, y + height * 0.4),
        (center_x + width * 0.01, y + height * 0.6),
        (center_x, y + height * 0.68),
    ]
    pygame.draw.polygon(surface, glow_cyan, center_line_right)
    
    draw_glow_circle(surface, (int(center_x), int(y + height * 0.5)), 5, glow_cyan, 15)
    draw_glow_circle(surface, (int(center_x), int(y + height * 0.5)), 2, (200, 255, 255), 8)
    
    engine_serrated_left = [
        (center_x - width * 0.15, y + height * 0.72),
        (center_x - width * 0.2, y + height * 0.78),
        (center_x - width * 0.12, y + height * 0.8),
        (center_x - width * 0.08, y + height * 0.76),
    ]
    pygame.draw.polygon(surface, hull_dark, engine_serrated_left)
    
    engine_serrated_center_left = [
        (center_x - width * 0.08, y + height * 0.75),
        (center_x - width * 0.06, y + height * 0.82),
        (center_x - width * 0.02, y + height * 0.8),
        (center_x, y + height * 0.77),
    ]
    pygame.draw.polygon(surface, hull_mid, engine_serrated_center_left)
    
    engine_serrated_center_right = [
        (center_x + width * 0.08, y + height * 0.75),
        (center_x + width * 0.06, y + height * 0.82),
        (center_x + width * 0.02, y + height * 0.8),
        (center_x, y + height * 0.77),
    ]
    pygame.draw.polygon(surface, hull_mid, engine_serrated_center_right)
    
    engine_serrated_right = [
        (center_x + width * 0.15, y + height * 0.72),
        (center_x + width * 0.2, y + height * 0.78),
        (center_x + width * 0.12, y + height * 0.8),
        (center_x + width * 0.08, y + height * 0.76),
    ]
    pygame.draw.polygon(surface, hull_dark, engine_serrated_right)
    
    for i in range(3):
        line_y = y + height * 0.42 + i * height * 0.08
        pygame.draw.line(surface, hull_highlight,
                        (center_x - width * 0.08, line_y),
                        (center_x - width * 0.02, line_y), 1)
        pygame.draw.line(surface, hull_highlight,
                        (center_x + width * 0.08, line_y),
                        (center_x + width * 0.02, line_y), 1)


def draw_enemy_ship(surface: pygame.Surface, x: float, y: float, width: float = 40, height: float = 40, health_ratio: float = 1.0) -> None:
    """绘制外星生物风格敌机 - 变异怪物设计"""
    center_x = x + width / 2
    center_y = y + height / 2
    
    if health_ratio > 0.6:
        body_dark = (40, 15, 60)
        body_mid = (80, 35, 100)
        body_light = (130, 70, 150)
        core_color = (255, 50, 100)
        core_glow = (255, 120, 180)
        eye_color = (255, 200, 50)
    elif health_ratio > 0.3:
        body_dark = (50, 35, 30)
        body_mid = (100, 70, 55)
        body_light = (160, 120, 90)
        core_color = (255, 150, 50)
        core_glow = (255, 200, 120)
        eye_color = (255, 220, 100)
    else:
        body_dark = (60, 50, 30)
        body_mid = (120, 100, 55)
        body_light = (180, 150, 90)
        core_color = (255, 220, 50)
        core_glow = (255, 250, 150)
        eye_color = (255, 255, 150)
    
    tentacle_1 = [
        (center_x - width * 0.3, y + height * 0.2),
        (x - width * 0.25, y + height * 0.55),
        (center_x - width * 0.15, y + height * 0.35),
    ]
    pygame.draw.polygon(surface, body_dark, tentacle_1)
    pygame.draw.circle(surface, core_color, (int(x - width * 0.15), int(y + height * 0.45)), 5)
    
    tentacle_2 = [
        (center_x + width * 0.3, y + height * 0.2),
        (x + width + width * 0.25, y + height * 0.55),
        (center_x + width * 0.15, y + height * 0.35),
    ]
    pygame.draw.polygon(surface, body_dark, tentacle_2)
    pygame.draw.circle(surface, core_color, (int(x + width + width * 0.15), int(y + height * 0.45)), 5)
    
    tentacle_3 = [
        (center_x - width * 0.4, y + height * 0.35),
        (x - width * 0.35, y + height * 0.75),
        (center_x - width * 0.2, y + height * 0.5),
    ]
    pygame.draw.polygon(surface, body_mid, tentacle_3)
    
    tentacle_4 = [
        (center_x + width * 0.4, y + height * 0.35),
        (x + width + width * 0.35, y + height * 0.75),
        (center_x + width * 0.2, y + height * 0.5),
    ]
    pygame.draw.polygon(surface, body_mid, tentacle_4)
    
    main_body = [
        (center_x, y + height + height * 0.1),
        (x + width * 0.9, y + height * 0.35),
        (x + width * 0.75, y + height * 0.05),
        (center_x, y - height * 0.05),
        (x + width * 0.25, y + height * 0.05),
        (x + width * 0.1, y + height * 0.35),
    ]
    pygame.draw.polygon(surface, body_dark, main_body)
    
    body_upper = [
        (center_x, y + height * 0.75),
        (x + width * 0.78, y + height * 0.4),
        (x + width * 0.65, y + height * 0.15),
        (center_x, y + height * 0.1),
        (x + width * 0.35, y + height * 0.15),
        (x + width * 0.22, y + height * 0.4),
    ]
    pygame.draw.polygon(surface, body_mid, body_upper)
    
    body_top = [
        (center_x, y + height * 0.5),
        (x + width * 0.6, y + height * 0.28),
        (x + width * 0.5, y + height * 0.1),
        (center_x, y + height * 0.15),
        (x + width * 0.5, y + height * 0.1),
        (x + width * 0.4, y + height * 0.28),
    ]
    pygame.draw.polygon(surface, body_light, body_top)
    
    eye_left = [
        (center_x - width * 0.25, y + height * 0.35),
        (center_x - width * 0.15, y + height * 0.45),
        (center_x - width * 0.18, y + height * 0.55),
        (center_x - width * 0.32, y + height * 0.45),
    ]
    pygame.draw.polygon(surface, (30, 20, 40), eye_left)
    draw_glow_circle(surface, (int(center_x - width * 0.23), int(y + height * 0.43)), 6, eye_color, 12)
    
    eye_right = [
        (center_x + width * 0.25, y + height * 0.35),
        (center_x + width * 0.15, y + height * 0.45),
        (center_x + width * 0.18, y + height * 0.55),
        (center_x + width * 0.32, y + height * 0.45),
    ]
    pygame.draw.polygon(surface, (30, 20, 40), eye_right)
    draw_glow_circle(surface, (int(center_x + width * 0.23), int(y + height * 0.43)), 6, eye_color, 12)
    
    mouth = [
        (center_x - width * 0.15, y + height * 0.55),
        (center_x, y + height * 0.7),
        (center_x + width * 0.15, y + height * 0.55),
        (center_x, y + height * 0.6),
    ]
    pygame.draw.polygon(surface, (20, 10, 25), mouth)
    
    for i in range(5):
        tooth_x = center_x - width * 0.12 + i * width * 0.06
        pygame.draw.polygon(surface, body_light, [
            (tooth_x, y + height * 0.56),
            (tooth_x + width * 0.03, y + height * 0.62),
            (tooth_x + width * 0.06, y + height * 0.56),
        ])
    
    spike_left = [
        (x - width * 0.1, y + height * 0.25),
        (x - width * 0.25, y + height * 0.1),
        (x + width * 0.05, y + height * 0.2),
    ]
    pygame.draw.polygon(surface, body_light, spike_left)
    
    spike_right = [
        (x + width + width * 0.1, y + height * 0.25),
        (x + width + width * 0.25, y + height * 0.1),
        (x + width - width * 0.05, y + height * 0.2),
    ]
    pygame.draw.polygon(surface, body_light, spike_right)
    
    draw_glow_circle(surface, (int(center_x), int(y + height * 0.3)), 12, core_color, 25)
    draw_glow_circle(surface, (int(center_x), int(y + height * 0.3)), 7, core_glow, 15)
    draw_glow_circle(surface, (int(center_x), int(y + height * 0.3)), 3, (255, 255, 220), 8)


def draw_bullet(surface: pygame.Surface, x: float, y: float, width: float = 8, height: float = 16, bullet_type: str = "single") -> None:
    if bullet_type == "spread":
        draw_spread_bullet(surface, x, y, width, height)
    elif bullet_type == "laser":
        draw_laser_bullet(surface, x, y, width, height)
    else:
        draw_single_bullet(surface, x, y, width, height)


def draw_single_bullet(surface: pygame.Surface, x: float, y: float, width: float, height: float) -> None:
    center_x = x + width / 2
    top_y = y

    glow = pygame.Surface((int(width + 16), int(height + 12)), pygame.SRCALPHA)
    for i in range(6, 0, -1):
        alpha = 30 * (6 - i) // 5
        glow_color = (255, 200, 50, alpha)
        pygame.draw.ellipse(glow, glow_color,
                            (8 - i, 4 - i // 2, int(width) + i * 2 - 6, int(height) + i - 2))
    surface.blit(glow, (int(x - 8), int(top_y - 4)))

    points = [
        (center_x, top_y),
        (x + width, y + height * 0.3),
        (center_x, y + height),
        (x, y + height * 0.3),
    ]
    pygame.draw.polygon(surface, (255, 220, 50), points)

    highlight_surf = pygame.Surface((int(width + 4), int(height // 2 + 2)), pygame.SRCALPHA)
    highlight_points = [
        (int(width / 2 + 2), 0),
        (int(width + 2), int(height * 0.15)),
        (int(width / 2 + 2), int(height * 0.3)),
    ]
    pygame.draw.polygon(highlight_surf, (255, 255, 200, 150), highlight_points)
    surface.blit(highlight_surf, (int(x), int(top_y)))


def draw_spread_bullet(surface: pygame.Surface, x: float, y: float, width: float, height: float) -> None:
    center = (int(x + width / 2), int(y + height / 2))
    radius = int(width / 2)

    glow = pygame.Surface((radius * 4 + 8, radius * 4 + 8), pygame.SRCALPHA)
    for i in range(radius + 4, 0, -2):
        alpha = 40 * (radius + 4 - i) // (radius + 4)
        pygame.draw.circle(glow, (255, 150, 50, alpha), (radius * 2 + 4, radius * 2 + 4), i)
    surface.blit(glow, (center[0] - radius * 2 - 4, center[1] - radius * 2 - 4))

    pygame.draw.circle(surface, (255, 180, 80), center, radius + 2)
    pygame.draw.circle(surface, (255, 220, 150), center, radius)


def draw_laser_bullet(surface: pygame.Surface, x: float, y: float, width: float, height: float) -> None:
    center_x = x + width / 2

    glow = pygame.Surface((20, int(height) + 8), pygame.SRCALPHA)
    for i in range(8, 0, -2):
        alpha = 50 * (8 - i) // 7
        pygame.draw.line(glow, (255, 50, 150, alpha), (10, 2), (10, int(height) + 6), i)
    surface.blit(glow, (int(center_x - 10), int(y - 2)))

    pygame.draw.line(surface, (255, 100, 200), (center_x, y), (center_x, y + height), 4)
    pygame.draw.line(surface, (255, 220, 240), (center_x, y), (center_x, y + height), 2)


def draw_ripple(surface: pygame.Surface, x: float, y: float, radius: float, alpha: int, pulse: int = 0) -> None:
    if alpha <= 0:
        return

    ripple_color = (150, 255, 255)
    glow_color = (200, 255, 255)

    surface_size = int(radius * 2 + 30)
    ripple_surface = pygame.Surface((surface_size, surface_size), pygame.SRCALPHA)
    center_offset = surface_size // 2
    x_pos = int(x - center_offset)
    y_pos = int(y - center_offset)

    pulse_effect = int(3 * (1 + 0.3 * math.sin(pulse * 0.3)))

    for i in range(int(radius), 0, -3):
        ring_alpha = max(0, alpha * (radius - i) // int(radius))
        if ring_alpha > 30:
            color = (*ripple_color, min(255, ring_alpha))
            thickness = max(2, 3 + pulse_effect // 2)
            pygame.draw.circle(ripple_surface, color, (center_offset, center_offset), i, thickness)

    for i in range(int(radius * 0.6), 0, -2):
        inner_alpha = max(0, alpha * (radius - i * 1.5) // int(radius * 0.6))
        if inner_alpha > 50:
            color = (*glow_color, min(255, inner_alpha))
            pygame.draw.circle(ripple_surface, color, (center_offset, center_offset), i, max(1, 2))

    core_radius = max(3, int(8 - pulse * 0.1))
    core_alpha = max(0, min(255, alpha * 1.5))
    if core_alpha > 50:
        pygame.draw.circle(ripple_surface, (*glow_color, core_alpha), (center_offset, center_offset), core_radius)
        pygame.draw.circle(ripple_surface, (255, 255, 255, core_alpha), (center_offset, center_offset), max(1, core_radius - 2))

    surface.blit(ripple_surface, (x_pos, y_pos))


def draw_boss_ship(surface: pygame.Surface, x: float, y: float, width: float = 120, height: float = 100, health_ratio: float = 1.0) -> None:
    """绘制巨型外星母舰 - 恐怖生物战舰设计"""
    center_x = x + width / 2
    center_y = y + height / 2
    
    if health_ratio > 0.6:
        hull_dark = (50, 20, 70)
        hull_mid = (90, 40, 120)
        hull_light = (140, 80, 170)
        core_color = (200, 50, 255)
        core_glow = (220, 150, 255)
        eye_color = (255, 50, 200)
    elif health_ratio > 0.3:
        hull_dark = (70, 40, 40)
        hull_mid = (120, 70, 70)
        hull_light = (180, 120, 120)
        core_color = (255, 140, 50)
        core_glow = (255, 190, 120)
        eye_color = (255, 200, 50)
    else:
        hull_dark = (80, 30, 30)
        hull_mid = (130, 50, 50)
        hull_light = (180, 90, 90)
        core_color = (220, 50, 50)
        core_glow = (255, 120, 120)
        eye_color = (255, 255, 50)
    
    for i in range(3):
        tentacle_x = center_x - width * 0.45 + i * width * 0.2
        tentacle_points = [
            (tentacle_x, y + height * 0.7),
            (tentacle_x - width * 0.1, y + height * 1.2),
            (tentacle_x + width * 0.1, y + height * 1.2),
        ]
        pygame.draw.polygon(surface, hull_dark, tentacle_points)
        pygame.draw.circle(surface, core_color, (int(tentacle_x), int(y + height * 1.1)), 8)
    
    large_tentacle_left = [
        (x - width * 0.15, y + height * 0.5),
        (x - width * 0.5, y + height * 1.1),
        (x - width * 0.2, y + height * 0.7),
    ]
    pygame.draw.polygon(surface, hull_dark, large_tentacle_left)
    pygame.draw.polygon(surface, hull_mid, [
        (x - width * 0.18, y + height * 0.55),
        (x - width * 0.4, y + height * 0.95),
        (x - width * 0.15, y + height * 0.65),
    ])
    pygame.draw.circle(surface, core_color, (int(x - width * 0.35), int(y + height * 0.9)), 12)
    
    large_tentacle_right = [
        (x + width + width * 0.15, y + height * 0.5),
        (x + width + width * 0.5, y + height * 1.1),
        (x + width + width * 0.2, y + height * 0.7),
    ]
    pygame.draw.polygon(surface, hull_dark, large_tentacle_right)
    pygame.draw.polygon(surface, hull_mid, [
        (x + width + width * 0.18, y + height * 0.55),
        (x + width + width * 0.4, y + height * 0.95),
        (x + width + width * 0.15, y + height * 0.65),
    ])
    pygame.draw.circle(surface, core_color, (int(x + width + width * 0.35), int(y + height * 0.9)), 12)
    
    wing_left = [
        (center_x - width * 0.1, center_y + height * 0.1),
        (x - width * 0.35, y + height * 0.65),
        (x + width * 0.05, y + height * 0.4),
        (center_x - width * 0.25, center_y - height * 0.05),
    ]
    pygame.draw.polygon(surface, hull_dark, wing_left)
    pygame.draw.polygon(surface, hull_mid, [
        (center_x - width * 0.12, center_y),
        (x - width * 0.28, y + height * 0.58),
        (x + width * 0.02, y + height * 0.42),
        (center_x - width * 0.3, center_y - height * 0.08),
    ])
    
    wing_right = [
        (center_x + width * 0.1, center_y + height * 0.1),
        (x + width + width * 0.35, y + height * 0.65),
        (x + width - width * 0.05, y + height * 0.4),
        (center_x + width * 0.25, center_y - height * 0.05),
    ]
    pygame.draw.polygon(surface, hull_dark, wing_right)
    pygame.draw.polygon(surface, hull_mid, [
        (center_x + width * 0.12, center_y),
        (x + width + width * 0.28, y + height * 0.58),
        (x + width - width * 0.02, y + height * 0.42),
        (center_x + width * 0.3, center_y - height * 0.08),
    ])
    
    main_hull = [
        (center_x, y - height * 0.1),
        (x + width * 0.92, y + height * 0.15),
        (x + width * 0.88, y + height * 0.45),
        (x + width * 0.78, y + height * 0.88),
        (x + width * 0.6, y + height + height * 0.08),
        (center_x, y + height * 0.92),
        (x + width * 0.4, y + height + height * 0.08),
        (x + width * 0.22, y + height * 0.88),
        (x + width * 0.12, y + height * 0.45),
        (x + width * 0.08, y + height * 0.15),
    ]
    pygame.draw.polygon(surface, hull_dark, main_hull)
    
    hull_detail = [
        (center_x, y + height * 0.08),
        (x + width * 0.8, y + height * 0.25),
        (x + width * 0.72, y + height * 0.52),
        (center_x, y + height * 0.42),
        (x + width * 0.28, y + height * 0.52),
        (x + width * 0.2, y + height * 0.25),
    ]
    pygame.draw.polygon(surface, hull_mid, hull_detail)
    
    hull_upper = [
        (center_x, y + height * 0.15),
        (x + width * 0.68, y + height * 0.28),
        (x + width * 0.58, y + height * 0.12),
        (center_x, y + height * 0.08),
        (x + width * 0.42, y + height * 0.12),
        (x + width * 0.32, y + height * 0.28),
    ]
    pygame.draw.polygon(surface, hull_light, hull_upper)
    
    for i in range(4):
        offset = -width * 0.28 + i * width * 0.18
        draw_glow_circle(surface, (int(center_x + offset), int(y + height * 0.22)), 7, core_color, 15)
    
    main_eye_left = [
        (center_x - width * 0.35, y + height * 0.38),
        (center_x - width * 0.2, y + height * 0.52),
        (center_x - width * 0.25, y + height * 0.65),
        (center_x - width * 0.45, y + height * 0.52),
    ]
    pygame.draw.polygon(surface, (20, 10, 30), main_eye_left)
    draw_glow_circle(surface, (int(center_x - width * 0.3), int(y + height * 0.48)), 14, eye_color, 30)
    draw_glow_circle(surface, (int(center_x - width * 0.3), int(y + height * 0.48)), 8, (255, 255, 200), 18)
    
    main_eye_right = [
        (center_x + width * 0.35, y + height * 0.38),
        (center_x + width * 0.2, y + height * 0.52),
        (center_x + width * 0.25, y + height * 0.65),
        (center_x + width * 0.45, y + height * 0.52),
    ]
    pygame.draw.polygon(surface, (20, 10, 30), main_eye_right)
    draw_glow_circle(surface, (int(center_x + width * 0.3), int(y + height * 0.48)), 14, eye_color, 30)
    draw_glow_circle(surface, (int(center_x + width * 0.3), int(y + height * 0.48)), 8, (255, 255, 200), 18)
    
    draw_glow_circle(surface, (int(center_x), int(y + height * 0.58)), 28, core_color, 60)
    draw_glow_circle(surface, (int(center_x), int(y + height * 0.58)), 18, core_glow, 40)
    draw_glow_circle(surface, (int(center_x), int(y + height * 0.58)), 10, (255, 255, 255), 22)
    
    for i in range(7):
        line_y = y + height * 0.32 + i * height * 0.08
        pygame.draw.line(surface, hull_light,
                        (center_x - width * 0.22, line_y),
                        (center_x + width * 0.22, line_y), 2)
    
    for i in range(3):
        spike_x = center_x - width * 0.4 + i * width * 0.4
        spike = [
            (spike_x, y + height * 0.1),
            (spike_x - width * 0.08, y - height * 0.15),
            (spike_x + width * 0.08, y - height * 0.15),
        ]
        pygame.draw.polygon(surface, hull_light, spike)
