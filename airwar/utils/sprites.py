import pygame


def draw_player_ship(surface: pygame.Surface, x: float, y: float, width: float = 50, height: float = 60) -> None:
    center_x = x + width / 2
    center_y = y + height / 2

    main_color = (0, 220, 255)
    dark_color = (0, 150, 200)
    accent_color = (255, 255, 255)

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
    pygame.draw.polygon(surface, main_color, points_body)

    wing_points = [
        (center_x - width * 0.1, center_y),
        (x - width * 0.1, y + height * 0.55),
        (x, y + height * 0.5),
        (x + width * 0.2, center_y),
    ]
    pygame.draw.polygon(surface, dark_color, wing_points)

    wing_points_right = [
        (center_x + width * 0.1, center_y),
        (x + width + width * 0.1, y + height * 0.55),
        (x + width + width * 0.05, y + height * 0.5),
        (x + width * 0.8, center_y),
    ]
    pygame.draw.polygon(surface, dark_color, wing_points_right)

    pygame.draw.circle(surface, accent_color, (int(center_x), int(center_y - height * 0.1)), 4)

    pygame.draw.line(surface, accent_color, (center_x, y + 5), (center_x, y + height * 0.25), 2)

    pygame.draw.polygon(surface, dark_color, [
        (center_x, y + height * 0.85),
        (center_x - width * 0.1, y + height + 5),
        (center_x + width * 0.1, y + height + 5),
    ])


def draw_enemy_ship(surface: pygame.Surface, x: float, y: float, width: float = 40, height: float = 40, health_ratio: float = 1.0) -> None:
    center_x = x + width / 2
    center_y = y + height / 2

    if health_ratio > 0.6:
        main_color = (255, 60, 60)
        dark_color = (180, 40, 40)
    elif health_ratio > 0.3:
        main_color = (255, 150, 50)
        dark_color = (180, 100, 30)
    else:
        main_color = (200, 200, 100)
        dark_color = (150, 150, 70)

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

    pygame.draw.circle(surface, (255, 200, 100), (int(center_x), int(center_y)), 5)
    pygame.draw.circle(surface, (255, 100, 100), (int(center_x), int(center_y)), 3)


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

    points = [
        (center_x, top_y),
        (x + width, y + height * 0.3),
        (center_x, y + height),
        (x, y + height * 0.3),
    ]
    pygame.draw.polygon(surface, (255, 255, 0), points)

    glow = pygame.Surface((int(width + 8), int(height + 8)), pygame.SRCALPHA)
    pygame.draw.polygon(glow, (255, 200, 0, 100), [
        (4, 2),
        (int(width + 4), int(height * 0.3 + 2)),
        (4, int(height + 2)),
        (2, int(height * 0.3 + 2)),
    ])
    surface.blit(glow, (int(x - 4), int(top_y - 2)))


def draw_spread_bullet(surface: pygame.Surface, x: float, y: float, width: float, height: float) -> None:
    color = (255, 150, 50)
    pygame.draw.circle(surface, color, (int(x + width/2), int(y + height/2)), int(width/2 + 2))
    pygame.draw.circle(surface, (255, 200, 100), (int(x + width/2), int(y + height/2)), int(width/2))


def draw_laser_bullet(surface: pygame.Surface, x: float, y: float, width: float, height: float) -> None:
    center_x = x + width / 2
    pygame.draw.line(surface, (255, 0, 100), (center_x, y), (center_x, y + height), 4)
    pygame.draw.line(surface, (255, 100, 150), (center_x, y), (center_x, y + height), 2)


def draw_ripple(surface: pygame.Surface, x: float, y: float, radius: float, alpha: int) -> None:
    if alpha <= 0:
        return
    ripple_surface = pygame.Surface((int(radius * 2 + 10), int(radius * 2 + 10)), pygame.SRCALPHA)
    color = (100, 200, 255, alpha)
    pygame.draw.circle(ripple_surface, color, (int(radius + 5), int(radius + 5)), int(radius), 3)
    surface.blit(ripple_surface, (int(x - radius - 5), int(y - radius - 5)))


def draw_boss_ship(surface: pygame.Surface, x: float, y: float, width: float = 120, height: float = 100, health_ratio: float = 1.0) -> None:
    center_x = x + width / 2
    center_y = y + height / 2

    if health_ratio > 0.6:
        main_color = (150, 50, 200)
        dark_color = (100, 30, 150)
        accent_color = (200, 100, 255)
    elif health_ratio > 0.3:
        main_color = (180, 100, 50)
        dark_color = (130, 70, 30)
        accent_color = (255, 150, 100)
    else:
        main_color = (180, 50, 50)
        dark_color = (130, 30, 30)
        accent_color = (255, 100, 100)

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

    pygame.draw.circle(surface, accent_color, (int(center_x), int(center_y)), 12)
    pygame.draw.circle(surface, (255, 255, 255), (int(center_x), int(center_y)), 6)

    pygame.draw.circle(surface, accent_color, (int(center_x - width * 0.2), int(center_y - height * 0.1)), 8)
    pygame.draw.circle(surface, (255, 200, 200), (int(center_x - width * 0.2), int(center_y - height * 0.1)), 4)

    pygame.draw.circle(surface, accent_color, (int(center_x + width * 0.2), int(center_y - height * 0.1)), 8)
    pygame.draw.circle(surface, (255, 200, 200), (int(center_x + width * 0.2), int(center_y - height * 0.1)), 4)

    for i in range(3):
        offset_x = (i - 1) * width * 0.15
        pygame.draw.line(surface, accent_color,
                        (center_x + offset_x, y + height * 0.3),
                        (center_x + offset_x, y + height * 0.5), 2)

    pygame.draw.polygon(surface, dark_color, [
        (center_x - width * 0.15, y + height + 5),
        (center_x, y + height + 20),
        (center_x + width * 0.15, y + height + 5),
    ])
