import pygame
import math


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
    hull_dark = (35, 60, 100)
    hull_mid = (55, 100, 160)
    hull_light = (85, 140, 200)
    hull_highlight = (130, 180, 230)
    glow_cyan = (80, 220, 255)
    
    wing_left = [
        (center_x - width * 0.08, y + height * 0.05),
        (x - width * 0.55, y + height * 0.65),
        (x - width * 0.35, y + height * 0.75),
        (x - width * 0.15, y + height * 0.55),
    ]
    pygame.draw.polygon(surface, hull_dark, wing_left)
    
    wing_left_mid = [
        (center_x - width * 0.08, y + height * 0.05),
        (x - width * 0.15, y + height * 0.55),
        (x - width * 0.05, y + height * 0.4),
        (center_x - width * 0.12, y + height * 0.25),
    ]
    pygame.draw.polygon(surface, hull_mid, wing_left_mid)
    
    wing_left_top = [
        (center_x - width * 0.12, y + height * 0.25),
        (x - width * 0.05, y + height * 0.4),
        (x + width * 0.1, y + height * 0.38),
        (center_x - width * 0.15, y + height * 0.3),
    ]
    pygame.draw.polygon(surface, hull_light, wing_left_top)
    
    wing_right = [
        (center_x + width * 0.08, y + height * 0.05),
        (x + width + width * 0.55, y + height * 0.65),
        (x + width + width * 0.35, y + height * 0.75),
        (x + width + width * 0.15, y + height * 0.55),
    ]
    pygame.draw.polygon(surface, hull_dark, wing_right)
    
    wing_right_mid = [
        (center_x + width * 0.08, y + height * 0.05),
        (x + width + width * 0.15, y + height * 0.55),
        (x + width + width * 0.05, y + height * 0.4),
        (center_x + width * 0.12, y + height * 0.25),
    ]
    pygame.draw.polygon(surface, hull_mid, wing_right_mid)
    
    wing_right_top = [
        (center_x + width * 0.12, y + height * 0.25),
        (x + width + width * 0.05, y + height * 0.4),
        (x + width - width * 0.1, y + height * 0.38),
        (center_x + width * 0.15, y + height * 0.3),
    ]
    pygame.draw.polygon(surface, hull_light, wing_right_top)
    
    body_base = [
        (center_x - width * 0.08, y + height * 0.3),
        (x + width * 0.08, y + height * 0.3),
        (x + width * 0.12, y + height * 0.65),
        (center_x, y + height * 0.85),
        (x + width * 0.88, y + height * 0.65),
        (x + width * 0.92, y + height * 0.3),
    ]
    pygame.draw.polygon(surface, hull_dark, body_base)
    
    body_mid = [
        (center_x - width * 0.05, y + height * 0.35),
        (x + width * 0.05, y + height * 0.35),
        (x + width * 0.08, y + height * 0.6),
        (center_x, y + height * 0.75),
        (x + width * 0.92, y + height * 0.6),
        (x + width * 0.95, y + height * 0.35),
    ]
    pygame.draw.polygon(surface, hull_mid, body_mid)
    
    body_top = [
        (center_x - width * 0.03, y + height * 0.38),
        (x + width * 0.03, y + height * 0.38),
        (x + width * 0.05, y + height * 0.55),
        (center_x, y + height * 0.65),
        (x + width * 0.95, y + height * 0.55),
        (x + width * 0.97, y + height * 0.38),
    ]
    pygame.draw.polygon(surface, hull_light, body_top)
    
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
    
    engine_left = [
        (center_x - width * 0.15, y + height * 0.72),
        (center_x - width * 0.2, y + height * 0.78),
        (center_x - width * 0.12, y + height * 0.8),
        (center_x - width * 0.08, y + height * 0.76),
    ]
    pygame.draw.polygon(surface, hull_dark, engine_left)
    
    engine_center_left = [
        (center_x - width * 0.08, y + height * 0.75),
        (center_x - width * 0.04, y + height * 0.82),
        (center_x, y + height * 0.8),
        (center_x + width * 0.04, y + height * 0.75),
    ]
    pygame.draw.polygon(surface, hull_mid, engine_center_left)
    
    engine_center_right = [
        (center_x + width * 0.08, y + height * 0.75),
        (center_x + width * 0.04, y + height * 0.82),
        (center_x, y + height * 0.8),
        (center_x - width * 0.04, y + height * 0.75),
    ]
    pygame.draw.polygon(surface, hull_mid, engine_center_right)
    
    engine_right = [
        (center_x + width * 0.15, y + height * 0.72),
        (center_x + width * 0.2, y + height * 0.78),
        (center_x + width * 0.12, y + height * 0.8),
        (center_x + width * 0.08, y + height * 0.76),
    ]
    pygame.draw.polygon(surface, hull_dark, engine_right)
    
    for i in range(3):
        line_y = y + height * 0.42 + i * height * 0.08
        pygame.draw.line(surface, hull_highlight, (center_x - width * 0.08, line_y), (center_x - width * 0.02, line_y), 1)
        pygame.draw.line(surface, hull_highlight, (center_x + width * 0.08, line_y), (center_x + width * 0.02, line_y), 1)


def draw_enemy_ship(surface: pygame.Surface, x: float, y: float, width: float = 40, height: float = 40, health_ratio: float = 1.0) -> None:
    center_x = x + width / 2
    
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
        pygame.draw.ellipse(glow, glow_color, (8 - i, 4 - i // 2, int(width) + i * 2 - 6, int(height) + i - 2))
    surface.blit(glow, (int(x - 8), int(top_y - 4)))

    points = [
        (center_x, top_y),
        (x + width, y + height * 0.3),
        (center_x, y + height),
        (x, y + height * 0.3),
    ]
    pygame.draw.polygon(surface, (255, 220, 50), points)


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

    surface_size = int(radius * 2 + 40)
    ripple_surface = pygame.Surface((surface_size, surface_size), pygame.SRCALPHA)
    center_offset = surface_size // 2
    x_pos = int(x - center_offset)
    y_pos = int(y - center_offset)

    ring_count = 5
    base_thickness = 2
    pulse_mod = pulse % 20
    phase_offset = pulse * 0.15

    for i in range(ring_count):
        ring_radius = int(radius * (1 - i * 0.15))
        if ring_radius < 5:
            continue

        ring_phase = phase_offset + i * 0.8
        intensity = 0.5 + 0.5 * math.sin(ring_phase)
        ring_alpha = int(alpha * 0.5 * intensity)

        if ring_alpha < 15:
            continue

        thickness = max(1, base_thickness + int(intensity * 2))

        if i % 2 == 0:
            ring_color = (180, 220, 255, ring_alpha)
        else:
            ring_color = (220, 240, 255, ring_alpha)

        pygame.draw.circle(ripple_surface, ring_color, (center_offset, center_offset), ring_radius, thickness)

    interference_rings = 3
    for i in range(interference_rings):
        interference_radius = int(radius * (0.4 + i * 0.25))
        if interference_radius < 3:
            continue

        interference_phase = phase_offset * 1.5 + i * 1.2
        interference_intensity = abs(math.sin(interference_phase))

        interference_alpha = int(alpha * 0.3 * interference_intensity)
        if interference_alpha < 10:
            continue

        interference_thickness = 1 if interference_intensity < 0.3 else 2

        pygame.draw.circle(
            ripple_surface,
            (200, 235, 255, interference_alpha),
            (center_offset, center_offset),
            interference_radius,
            interference_thickness
        )

    surface.blit(ripple_surface, (x_pos, y_pos))


def draw_boss_ship(surface: pygame.Surface, x: float, y: float, width: float = 120, height: float = 100, health_ratio: float = 1.0) -> None:
    center_x = x + width / 2
    center_y = y + height / 2

    if health_ratio > 0.6:
        hull_dark = (50, 20, 70)
        hull_mid = (90, 40, 120)
        hull_light = (140, 80, 170)
        core_color = (200, 50, 255)
        core_glow = (220, 150, 255)
        eye_color = (255, 50, 200)
        eye_pupil = (255, 255, 200)
    elif health_ratio > 0.3:
        hull_dark = (70, 40, 40)
        hull_mid = (120, 70, 70)
        hull_light = (180, 120, 120)
        core_color = (255, 140, 50)
        core_glow = (255, 190, 120)
        eye_color = (255, 200, 50)
        eye_pupil = (255, 255, 200)
    else:
        hull_dark = (80, 30, 30)
        hull_mid = (130, 50, 50)
        hull_light = (180, 90, 90)
        core_color = (220, 50, 50)
        core_glow = (255, 120, 120)
        eye_color = (255, 255, 50)
        eye_pupil = (255, 255, 255)

    wing_left = [
        (center_x - width * 0.08, y + height * 0.25),
        (x - width * 0.1, y + height * 0.7),
        (center_x - width * 0.05, y + height * 0.45),
    ]
    pygame.draw.polygon(surface, hull_dark, wing_left)
    pygame.draw.polygon(surface, hull_mid, [
        (center_x - width * 0.07, y + height * 0.28),
        (x - width * 0.08, y + height * 0.65),
        (center_x - width * 0.04, y + height * 0.48),
    ])

    wing_right = [
        (center_x + width * 0.08, y + height * 0.25),
        (x + width + width * 0.1, y + height * 0.7),
        (center_x + width * 0.05, y + height * 0.45),
    ]
    pygame.draw.polygon(surface, hull_dark, wing_right)
    pygame.draw.polygon(surface, hull_mid, [
        (center_x + width * 0.07, y + height * 0.28),
        (x + width + width * 0.08, y + height * 0.65),
        (center_x + width * 0.04, y + height * 0.48),
    ])

    main_body = [
        (center_x, y + height * 0.1),
        (x + width * 0.85, y + height * 0.35),
        (x + width * 0.9, y + height * 0.65),
        (center_x, y + height * 0.9),
        (x + width * 0.1, y + height * 0.65),
        (x + width * 0.15, y + height * 0.35),
    ]
    pygame.draw.polygon(surface, hull_dark, main_body)

    body_mid = [
        (center_x, y + height * 0.2),
        (x + width * 0.75, y + height * 0.4),
        (x + width * 0.8, y + height * 0.6),
        (center_x, y + height * 0.8),
        (x + width * 0.2, y + height * 0.6),
        (x + width * 0.25, y + height * 0.4),
    ]
    pygame.draw.polygon(surface, hull_mid, body_mid)

    body_top = [
        (center_x, y + height * 0.15),
        (x + width * 0.7, y + height * 0.32),
        (x + width * 0.75, y + height * 0.55),
        (center_x, y + height * 0.72),
        (x + width * 0.25, y + height * 0.55),
        (x + width * 0.3, y + height * 0.32),
    ]
    pygame.draw.polygon(surface, hull_light, body_top)

    tentacle_1 = [
        (center_x - width * 0.3, y + height * 0.75),
        (center_x - width * 0.25, y + height * 1.05),
        (center_x - width * 0.15, y + height * 0.75),
    ]
    pygame.draw.polygon(surface, hull_dark, tentacle_1)
    draw_glow_circle(surface, (int(center_x - width * 0.2), int(y + height * 0.95)), 8, core_color, 18)

    tentacle_2 = [
        (center_x - width * 0.08, y + height * 0.82),
        (center_x, y + height * 1.1),
        (center_x + width * 0.08, y + height * 0.82),
    ]
    pygame.draw.polygon(surface, hull_dark, tentacle_2)
    draw_glow_circle(surface, (int(center_x), int(y + height * 0.98)), 10, core_color, 22)

    tentacle_3 = [
        (center_x + width * 0.15, y + height * 0.75),
        (center_x + width * 0.25, y + height * 1.05),
        (center_x + width * 0.3, y + height * 0.75),
    ]
    pygame.draw.polygon(surface, hull_dark, tentacle_3)
    draw_glow_circle(surface, (int(center_x + width * 0.2), int(y + height * 0.95)), 8, core_color, 18)

    eye_left_socket = [
        (center_x - width * 0.32, y + height * 0.38),
        (center_x - width * 0.18, y + height * 0.48),
        (center_x - width * 0.22, y + height * 0.58),
        (center_x - width * 0.38, y + height * 0.5),
    ]
    pygame.draw.polygon(surface, (25, 15, 35), eye_left_socket)
    draw_glow_circle(surface, (int(center_x - width * 0.25), int(y + height * 0.46)), 10, eye_color, 22)
    draw_glow_circle(surface, (int(center_x - width * 0.25), int(y + height * 0.46)), 5, eye_pupil, 12)

    eye_right_socket = [
        (center_x + width * 0.32, y + height * 0.38),
        (center_x + width * 0.18, y + height * 0.48),
        (center_x + width * 0.22, y + height * 0.58),
        (center_x + width * 0.38, y + height * 0.5),
    ]
    pygame.draw.polygon(surface, (25, 15, 35), eye_right_socket)
    draw_glow_circle(surface, (int(center_x + width * 0.25), int(y + height * 0.46)), 10, eye_color, 22)
    draw_glow_circle(surface, (int(center_x + width * 0.25), int(y + height * 0.46)), 5, eye_pupil, 12)

    draw_glow_circle(surface, (int(center_x), int(y + height * 0.6)), 20, core_color, 45)
    draw_glow_circle(surface, (int(center_x), int(y + height * 0.6)), 12, core_glow, 28)
    draw_glow_circle(surface, (int(center_x), int(y + height * 0.6)), 6, (255, 255, 255), 15)

    for i in range(4):
        line_y = y + height * 0.35 + i * height * 0.1
        line_start = center_x - width * 0.18
        line_end = center_x + width * 0.18
        pygame.draw.line(surface, hull_light, (line_start, line_y), (line_end, line_y), 2)

    spike_1 = [
        (center_x - width * 0.15, y + height * 0.15),
        (center_x - width * 0.2, y - height * 0.05),
        (center_x - width * 0.1, y + height * 0.12),
    ]
    pygame.draw.polygon(surface, hull_light, spike_1)

    spike_2 = [
        (center_x + width * 0.15, y + height * 0.15),
        (center_x + width * 0.2, y - height * 0.05),
        (center_x + width * 0.1, y + height * 0.12),
    ]
    pygame.draw.polygon(surface, hull_light, spike_2)
