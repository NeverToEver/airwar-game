import pygame
import math


class MotherShip:
    DOCKING_BAY_X_OFFSET = 0
    DOCKING_BAY_Y_OFFSET = 50

    # Movement configuration - inertia-based system
    ACCELERATION = 0.08  # how fast mothership accelerates when player input
    MAX_SPEED = 1.5  # maximum velocity (pixels per frame), very slow
    FRICTION = 0.98  # velocity multiplier per frame when no input (1 = no friction)

    def __init__(self, screen_width: int, screen_height: int):
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._visible = False
        self._initial_x = screen_width // 2
        self._initial_y = int(screen_height * 0.35)  # 35% from top, closer to center
        self._position = (self._initial_x, self._initial_y)
        self._animation_time = 0

        # Inertia-based velocity
        self._velocity = [0.0, 0.0]
        self._player_input = [0, 0]  # [x, y] input direction (-1, 0, or 1)

        self._engine_pulse = 0.0
        self._wing_pulse = 0.0

        self._colors = {
            # 军事配色：银灰 + 琥珀金
            'hull_dark': (45, 50, 60),
            'hull_main': (70, 80, 100),
            'hull_light': (100, 115, 140),
            'hull_highlight': (140, 155, 185),
            'wing_dark': (40, 48, 58),
            'wing_main': (60, 72, 90),
            'wing_light': (90, 105, 130),
            # 引擎：琥珀色/橙色
            'engine_core': (255, 180, 50),
            'engine_glow': (255, 200, 80),
            'engine_outer': (200, 120, 30),
            # 驾驶舱：金色
            'cockpit': (180, 140, 60),
            'cockpit_glass': (255, 200, 100),
            'detail_line': (120, 140, 180),
            'accent': (255, 180, 50),  # 琥珀金色标记线
        }

    def show(self) -> None:
        self._visible = True
        self._animation_time = 0

    def hide(self) -> None:
        self._visible = False

    def is_visible(self) -> bool:
        return self._visible

    def set_player_input(self, x: int, y: int) -> None:
        self._player_input = [x, y]

    def get_docking_position(self) -> tuple:
        return (
            self._position[0] + self.DOCKING_BAY_X_OFFSET,
            self._position[1] + self.DOCKING_BAY_Y_OFFSET
        )

    def update_animation(self) -> None:
        if self._visible:
            self._animation_time += 0.05
            self._engine_pulse = 0.5 + 0.5 * math.sin(self._animation_time * 2)
            self._wing_pulse = 0.3 + 0.3 * math.sin(self._animation_time * 1.5)

    def update(self) -> None:
        if not self._visible:
            return

        # Apply acceleration based on player input
        self._velocity[0] += self._player_input[0] * self.ACCELERATION
        self._velocity[1] += self._player_input[1] * self.ACCELERATION

        # Clamp velocity to max speed
        for i in range(2):
            if abs(self._velocity[i]) > self.MAX_SPEED:
                self._velocity[i] = self.MAX_SPEED if self._velocity[i] > 0 else -self.MAX_SPEED

        # Apply friction when no input
        if self._player_input[0] == 0:
            self._velocity[0] *= self.FRICTION
        if self._player_input[1] == 0:
            self._velocity[1] *= self.FRICTION

        # Update position
        new_x = self._position[0] + self._velocity[0]
        new_y = self._position[1] + self._velocity[1]

        # Keep within screen bounds
        new_x = max(50, min(self._screen_width - 50, new_x))
        new_y = max(50, min(self._screen_height - 100, new_y))

        self._position = (int(new_x), int(new_y))

    def render(self, surface: pygame.Surface) -> None:
        if not self._visible:
            return

        self.update_animation()
        cx, cy = self._position

        self._render_engine_glow(surface, cx, cy)
        self._render_wings(surface, cx, cy)
        self._render_body(surface, cx, cy)
        self._render_cockpit(surface, cx, cy)
        self._render_details(surface, cx, cy)
        self._render_engines(surface, cx, cy)

    def _render_engine_glow(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        for i in range(3):
            offset_x = (i - 1) * 20
            pulse = 0.7 + 0.3 * self._engine_pulse
            radius = int(25 + 10 * pulse)

            glow_pos = (cx + offset_x, cy + 55)

            for r in range(radius, radius // 2, -3):
                alpha = int(30 * pulse * (radius - r) / radius)
                glow_color = (*self._colors['engine_outer'][:3], alpha)
                glow_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, glow_color, (r, r), r)
                surface.blit(glow_surf, (glow_pos[0] - r, glow_pos[1] - r))

            core_radius = 6 + int(3 * pulse)
            pygame.draw.circle(surface, self._colors['engine_core'], glow_pos, core_radius)
            pygame.draw.circle(surface, self._colors['engine_glow'], glow_pos, core_radius + 2, 1)

    def _render_wings(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        left_wing_points = [
            (cx - 50, cy + 15),
            (cx - 130, cy + 45),
            (cx - 115, cy + 60),
            (cx - 95, cy + 70),
            (cx - 55, cy + 45),
        ]

        right_wing_points = [
            (cx + 50, cy + 15),
            (cx + 130, cy + 45),
            (cx + 115, cy + 60),
            (cx + 95, cy + 70),
            (cx + 55, cy + 45),
        ]

        for wing_points in [left_wing_points, right_wing_points]:
            pygame.draw.polygon(surface, self._colors['wing_dark'], wing_points)
            pygame.draw.polygon(surface, self._colors['wing_main'], wing_points[:-1])

            for i in range(len(wing_points) - 1):
                p1 = wing_points[i]
                p2 = wing_points[i + 1]
                if i % 2 == 0:
                    pygame.draw.line(surface, self._colors['wing_light'], p1, p2, 1)

        left_detail = [
            (cx - 70, cy + 25), (cx - 110, cy + 50),
        ]
        right_detail = [
            (cx + 70, cy + 25), (cx + 110, cy + 50),
        ]

        for detail in [left_detail, right_detail]:
            pygame.draw.line(surface, self._colors['accent'], detail[0], detail[1], 2)

    def _render_body(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        hull_points = [
            (cx, cy - 50),
            (cx + 70, cy + 5),
            (cx + 60, cy + 25),
            (cx + 45, cy + 50),
            (cx - 45, cy + 50),
            (cx - 60, cy + 25),
            (cx - 70, cy + 5),
        ]

        pygame.draw.polygon(surface, self._colors['hull_dark'], hull_points)
        pygame.draw.polygon(surface, self._colors['hull_main'], [
            (cx, cy - 40),
            (cx + 55, cy + 8),
            (cx + 48, cy + 22),
            (cx + 35, cy + 42),
            (cx - 35, cy + 42),
            (cx - 48, cy + 22),
            (cx - 55, cy + 8),
        ])

        pygame.draw.polygon(surface, self._colors['hull_highlight'], [
            (cx, cy - 35),
            (cx + 40, cy + 5),
            (cx + 30, cy + 35),
            (cx - 30, cy + 35),
            (cx - 40, cy + 5),
        ])

        pygame.draw.polygon(surface, self._colors['hull_light'], hull_points, 2)

        panel_points = [
            (cx - 30, cy - 20),
            (cx + 30, cy - 20),
            (cx + 35, cy + 10),
            (cx - 35, cy + 10),
        ]
        pygame.draw.polygon(surface, self._colors['hull_dark'], panel_points, 1)

    def _render_cockpit(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        cockpit_points = [
            (cx, cy - 25),
            (cx + 20, cy),
            (cx + 15, cy + 15),
            (cx - 15, cy + 15),
            (cx - 20, cy),
        ]

        pygame.draw.polygon(surface, self._colors['cockpit'], cockpit_points)
        pygame.draw.polygon(surface, self._colors['cockpit_glass'], [
            (cx, cy - 20),
            (cx + 12, cy - 2),
            (cx + 8, cy + 8),
            (cx - 8, cy + 8),
            (cx - 12, cy - 2),
        ])

        pygame.draw.polygon(surface, (150, 210, 255, 100), [
            (cx - 5, cy - 15),
            (cx + 3, cy - 10),
            (cx, cy - 2),
        ])

        pygame.draw.polygon(surface, self._colors['cockpit_glass'], cockpit_points, 1)

    def _render_details(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        line_color = self._colors['detail_line']

        front_line = [(cx - 50, cy - 10), (cx - 25, cy - 30), (cx + 25, cy - 30), (cx + 50, cy - 10)]
        pygame.draw.lines(surface, line_color, False, front_line, 1)

        side_lines = [
            [(cx - 60, cy + 15), (cx - 50, cy + 30)],
            [(cx + 60, cy + 15), (cx + 50, cy + 30)],
        ]
        for line in side_lines:
            pygame.draw.line(surface, line_color, line[0], line[1], 1)

        for offset_x in [-25, 25]:
            dot_pos = (cx + offset_x, cy + 30)
            pygame.draw.circle(surface, self._colors['engine_glow'], dot_pos, 3)
            pygame.draw.circle(surface, self._colors['engine_core'], dot_pos, 2)

        hull_lines = [
            [(cx - 40, cy - 5), (cx - 40, cy + 20)],
            [(cx + 40, cy - 5), (cx + 40, cy + 20)],
        ]
        for line in hull_lines:
            pygame.draw.line(surface, self._colors['hull_dark'], line[0], line[1], 2)

    def _render_engines(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        engine_positions = [
            (cx - 20, cy + 48),
            (cx, cy + 52),
            (cx + 20, cy + 48),
        ]

        for i, pos in enumerate(engine_positions):
            base_y = pos[1]
            pulse = 0.8 + 0.2 * math.sin(self._animation_time * 3 + i * 0.5)

            engine_rect = pygame.Rect(pos[0] - 6, base_y, 12, 8)
            pygame.draw.rect(surface, self._colors['hull_dark'], engine_rect)

            inner_rect = pygame.Rect(pos[0] - 4, base_y + 1, 8, 6)
            pygame.draw.rect(surface, self._colors['engine_outer'], inner_rect)

            core_rect = pygame.Rect(pos[0] - 2, base_y + 2, 4, int(4 * pulse))
            pygame.draw.rect(surface, self._colors['engine_glow'], core_rect)
