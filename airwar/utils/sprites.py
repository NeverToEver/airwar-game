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
    center_x = x + width / 2
    center_y = y + height / 2

    cyan = (0, 220, 255)
    dark_cyan = (0, 120, 160)
    white = (255, 255, 255)
    glow_color = (0, 180, 255)

    wing_glow = pygame.Surface((int(width * 2.5), int(height * 1.8)), pygame.SRCALPHA)
    wing_points = [
        (int(width * 1.25), int(height * 0.5)),
        (int(-width * 0.3), int(height * 0.85)),
        (int(width * 0.1), int(height * 0.5)),
    ]
    for i in range(3, 0, -1):
        expanded = [(p[0] + (wing_points[j][0] - wing_points[1][0]) * (3 - i) * 0.15,
                     p[1] + (wing_points[j][1] - wing_points[1][1]) * (3 - i) * 0.15)
                    for j, p in enumerate(wing_points)]
        alpha = 30 * (4 - i)
        pygame.draw.polygon(wing_glow, (*glow_color[:3], alpha), expanded)
    surface.blit(wing_glow, (int(x - width * 0.6), int(y - height * 0.1)))

    wing_points = [
        (center_x - width * 0.1, center_y),
        (x - width * 0.1, y + height * 0.55),
        (x, y + height * 0.5),
        (x + width * 0.2, center_y),
    ]
    pygame.draw.polygon(surface, dark_cyan, wing_points)

    wing_points_right = [
        (center_x + width * 0.1, center_y),
        (x + width + width * 0.1, y + height * 0.55),
        (x + width + width * 0.05, y + height * 0.5),
        (x + width * 0.8, center_y),
    ]
    pygame.draw.polygon(surface, dark_cyan, wing_points_right)

    points_body = [
        (center_x, y),
        (x + width * 0.8, y + height * 0.35),
        (x + width, y + height * 0.5),
        (x + width * 0.85, y + height * 0.65),
        (x + width * 0.7, y + height),
        (center_x, y + height * 0.8),
        (x + width * 0.3, y + height),
        (x + width * 0.15, y + height * 0.65),
        (x, y + height * 0.5),
        (x + width * 0.2, y + height * 0.35),
    ]
    pygame.draw.polygon(surface, cyan, points_body)

    draw_glow_circle(surface, (int(center_x), int(center_y - height * 0.1)), 5, white, 12)
    pygame.draw.line(surface, white, (center_x, y + 5), (center_x, y + height * 0.25), 2)

    pygame.draw.polygon(surface, dark_cyan, [
        (center_x, y + height * 0.85),
        (center_x - width * 0.1, y + height + 5),
        (center_x + width * 0.1, y + height + 5),
    ])

    thruster_glow = pygame.Surface((20, 30), pygame.SRCALPHA)
    for i in range(10, 0, -1):
        alpha = 25 * (10 - i) // 10
        color = (0, 200, 255, alpha)
        pygame.draw.circle(thruster_glow, color, (10, 15 + i), 10 - i // 2)
    surface.blit(thruster_glow, (int(center_x - 10), int(y + height)))


def draw_enemy_ship(surface: pygame.Surface, x: float, y: float, width: float = 40, height: float = 40, health_ratio: float = 1.0) -> None:
    center_x = x + width / 2
    center_y = y + height / 2

    if health_ratio > 0.6:
        main_color = (255, 50, 50)
        dark_color = (180, 30, 30)
        glow_color = (255, 80, 80)
    elif health_ratio > 0.3:
        main_color = (255, 140, 40)
        dark_color = (180, 90, 20)
        glow_color = (255, 170, 80)
    else:
        main_color = (220, 180, 50)
        dark_color = (160, 130, 30)
        glow_color = (255, 200, 80)

    wing_glow = pygame.Surface((int(width * 2), int(height * 1.5)), pygame.SRCALPHA)
    wing_points = [
        (int(width * 0.5), int(height * 0.5)),
        (int(-width * 0.2), int(height * 0.9)),
        (int(width * 0.5), int(height * 0.6)),
    ]
    for i in range(3, 0, -1):
        expanded = [(p[0] + (wing_points[j][0] - wing_points[1][0]) * (3 - i) * 0.2,
                     p[1] + (wing_points[j][1] - wing_points[1][1]) * (3 - i) * 0.2)
                    for j, p in enumerate(wing_points)]
        alpha = 40 * (4 - i) // 3
        pygame.draw.polygon(wing_glow, (*glow_color[:3], alpha), expanded)
    surface.blit(wing_glow, (int(x - width * 0.6), int(y - height * 0.1)))

    points_body = [
        (center_x, y + height),
        (x + width, y + height * 0.3),
        (x + width * 0.8, y),
        (center_x, y + height * 0.2),
        (x + width * 0.2, y),
        (x, y + height * 0.3),
    ]
    pygame.draw.polygon(surface, main_color, points_body)

    wing_left = [
        (x + width * 0.15, y + height * 0.4),
        (x - width * 0.15, y + height * 0.7),
        (x + width * 0.3, y + height * 0.5),
    ]
    pygame.draw.polygon(surface, dark_color, wing_left)

    wing_right = [
        (x + width * 0.85, y + height * 0.4),
        (x + width + width * 0.15, y + height * 0.7),
        (x + width * 0.7, y + height * 0.5),
    ]
    pygame.draw.polygon(surface, dark_color, wing_right)

    draw_glow_circle(surface, (int(center_x), int(center_y)), 6, glow_color, 15)
    draw_glow_circle(surface, (int(center_x), int(center_y)), 3, (255, 255, 200), 5)


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


def draw_ripple(surface: pygame.Surface, x: float, y: float, radius: float, alpha: int) -> None:
    if alpha <= 0:
        return
    ripple_surface = pygame.Surface((int(radius * 2 + 20), int(radius * 2 + 20)), pygame.SRCALPHA)
    for i in range(int(radius), 0, -2):
        ring_alpha = alpha * (radius - i) // int(radius)
        color = (100, 220, 255, ring_alpha)
        pygame.draw.circle(ripple_surface, color, (int(radius + 10), int(radius + 10)), i, 2)
    surface.blit(ripple_surface, (int(x - radius - 10), int(y - radius - 10)))


def draw_boss_ship(surface: pygame.Surface, x: float, y: float, width: float = 120, height: float = 100, health_ratio: float = 1.0) -> None:
    center_x = x + width / 2
    center_y = y + height / 2

    if health_ratio > 0.6:
        main_color = (140, 40, 200)
        dark_color = (90, 20, 150)
        glow_color = (180, 100, 255)
    elif health_ratio > 0.3:
        main_color = (180, 90, 50)
        dark_color = (130, 60, 30)
        glow_color = (255, 150, 100)
    else:
        main_color = (180, 40, 50)
        dark_color = (130, 20, 30)
        glow_color = (255, 100, 100)

    wing_glow = pygame.Surface((int(width * 2.5), int(height * 2)), pygame.SRCALPHA)
    wing_points = [
        (int(width * 1.25), int(height * 0.6)),
        (int(-width * 0.3), int(height * 1.2)),
        (int(width * 1.25), int(height * 0.7)),
    ]
    for i in range(5, 0, -1):
        expanded = [(p[0] + (wing_points[j][0] - wing_points[1][0]) * (5 - i) * 0.12,
                     p[1] + (wing_points[j][1] - wing_points[1][1]) * (5 - i) * 0.12)
                    for j, p in enumerate(wing_points)]
        alpha = 35 * (6 - i) // 5
        pygame.draw.polygon(wing_glow, (*glow_color[:3], alpha), expanded)
    surface.blit(wing_glow, (int(x - width * 0.6), int(y - height * 0.2)))

    main_body = [
        (center_x, y + height),
        (x + width, y + height * 0.4),
        (x + width * 0.9, y),
        (center_x, y + height * 0.15),
        (x + width * 0.1, y),
        (x, y + height * 0.4),
    ]
    pygame.draw.polygon(surface, main_color, main_body)

    wing_left = [
        (x, y + height * 0.4),
        (x - width * 0.2, y + height * 0.7),
        (x + width * 0.15, y + height * 0.55),
    ]
    pygame.draw.polygon(surface, dark_color, wing_left)

    wing_right = [
        (x + width, y + height * 0.4),
        (x + width + width * 0.2, y + height * 0.7),
        (x + width * 0.85, y + height * 0.55),
    ]
    pygame.draw.polygon(surface, dark_color, wing_right)

    side_wing_left = [
        (x + width * 0.1, y + height * 0.5),
        (x - width * 0.1, y + height * 0.85),
        (x + width * 0.25, y + height * 0.75),
    ]
    pygame.draw.polygon(surface, dark_color, side_wing_left)

    side_wing_right = [
        (x + width * 0.9, y + height * 0.5),
        (x + width + width * 0.1, y + height * 0.85),
        (x + width * 0.75, y + height * 0.75),
    ]
    pygame.draw.polygon(surface, dark_color, side_wing_right)

    draw_glow_circle(surface, (int(center_x), int(center_y)), 14, glow_color, 30)
    draw_glow_circle(surface, (int(center_x), int(center_y)), 8, (255, 255, 255), 15)

    draw_glow_circle(surface, (int(center_x - width * 0.2), int(center_y - height * 0.1)), 10, glow_color, 22)
    draw_glow_circle(surface, (int(center_x - width * 0.2), int(center_y - height * 0.1)), 5, (255, 220, 220), 10)

    draw_glow_circle(surface, (int(center_x + width * 0.2), int(center_y - height * 0.1)), 10, glow_color, 22)
    draw_glow_circle(surface, (int(center_x + width * 0.2), int(center_y - height * 0.1)), 5, (255, 220, 220), 10)

    for i in range(3):
        offset_x = (i - 1) * width * 0.15
        line_glow = pygame.Surface((6, int(height * 0.25)), pygame.SRCALPHA)
        pygame.draw.line(line_glow, (*glow_color[:3], 100), (3, 0), (3, int(height * 0.25)), 3)
        surface.blit(line_glow, (int(center_x + offset_x - 3), int(y + height * 0.3)))

    thruster_surf = pygame.Surface((int(width * 0.5), 40), pygame.SRCALPHA)
    for i in range(15, 0, -1):
        alpha = 20 * (15 - i) // 14
        color = (*glow_color[:3], alpha) if len(glow_color) == 3 else (*glow_color, alpha)
        pygame.draw.ellipse(thruster_surf, color,
                           (int(width * 0.25 - i), 20 + i // 2, i * 2, 20 - i))
    surface.blit(thruster_surf, (int(center_x - width * 0.25), int(y + height)))
