"""Mothership entity — visual representation and docking zone.

Capital ship design: cold-steel-blue hull, swept-back wings, bridge tower,
underside docking bay with guide lights. Shares faction colors with player ship.
"""
import pygame
import math
from airwar.utils._sprites_common import draw_glow_circle


class MotherShip:
    """Mothership entity — visual representation and docking zone.

    Renders a large capital-class support vessel with swept-back wings,
    bridge tower, and underside docking bay.
    """
    DOCKING_BAY_X_OFFSET = 0
    DOCKING_BAY_Y_OFFSET = 85

    ACCELERATION = 0.25
    MAX_SPEED = 3.0
    FRICTION = 1.0  # No friction — direct response, symmetric feel

    def __init__(self, screen_width: int, screen_height: int):
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._visible = False
        self._phantom_visible = False
        self._phantom_surf = None
        self._phantom_surf_size = (0, 0)
        self._initial_x = screen_width // 2
        self._initial_y = int(screen_height * 0.35)
        self._position = (self._initial_x, self._initial_y)
        self._animation_time = 0

        self._velocity = [0.0, 0.0]
        self._player_input = [0, 0]

        self._engine_pulse = 0.0
        self._wing_pulse = 0.0

        self._flyaway_mode = False
        self._flyaway_velocity_y = 0.0
        self._flyaway_accel = 0.15

        self._colors = {
            'hull_dark': (20, 24, 38),
            'hull_mid': (35, 44, 62),
            'hull_light': (52, 64, 88),
            'hull_highlight': (110, 130, 160),
            'wing_dark': (18, 22, 36),
            'wing_mid': (32, 40, 56),
            'wing_light': (50, 60, 82),
            'glass_dark': (28, 148, 190),
            'glass_mid': (55, 188, 225),
            'glass_bright': (150, 225, 246),
            'engine_core': (200, 230, 255),
            'engine_glow': (100, 180, 255),
            'engine_outer': (50, 120, 200),
            'accent': (180, 150, 120),
            'accent_dim': (140, 115, 90),
            'dock_guide': (80, 220, 160),
            'dock_guide_dim': (40, 160, 110),
            'running_light': (140, 170, 210),
            'panel_line': (55, 68, 95),
        }

    # ── Public API ─────────────────────────────────────────────────────────

    def show(self) -> None:
        self._visible = True
        self._animation_time = 0

    def hide(self) -> None:
        self._visible = False

    def is_visible(self) -> bool:
        return self._visible

    def set_position(self, x: int, y: int) -> None:
        self._position = (x, y)

    def show_phantom(self) -> None:
        self._phantom_visible = True

    def hide_phantom(self) -> None:
        self._phantom_visible = False

    def set_player_input(self, x: int, y: int) -> None:
        self._player_input = [x, y]

    def activate_flyaway(self) -> None:
        """Enter flyaway mode: accelerate upward and exit screen top."""
        self._flyaway_mode = True
        self._flyaway_velocity_y = 0.0

    def deactivate_flyaway(self) -> None:
        """Exit flyaway mode."""
        self._flyaway_mode = False
        self._flyaway_velocity_y = 0.0

    def is_flyaway_mode(self) -> bool:
        return self._flyaway_mode

    def get_docking_position(self) -> tuple:
        return (
            self._position[0] + self.DOCKING_BAY_X_OFFSET,
            self._position[1] + self.DOCKING_BAY_Y_OFFSET,
        )

    def update_animation(self) -> None:
        if self._visible:
            self._animation_time += 0.05
            self._engine_pulse = 0.5 + 0.5 * math.sin(self._animation_time * 2)
            self._wing_pulse = 0.3 + 0.3 * math.sin(self._animation_time * 1.5)

    def update(self) -> None:
        if not self._visible:
            return

        if self._flyaway_mode:
            self._flyaway_velocity_y -= self._flyaway_accel
            new_x = self._position[0]
            new_y = self._position[1] + self._flyaway_velocity_y
            self._position = (int(new_x), int(new_y))
            # Auto-hide when fully off the top of the screen
            if new_y < -200:
                self.hide()
                self._flyaway_mode = False
            return

        self._velocity[0] += self._player_input[0] * self.ACCELERATION
        self._velocity[1] += self._player_input[1] * self.ACCELERATION
        for i in range(2):
            if abs(self._velocity[i]) > self.MAX_SPEED:
                self._velocity[i] = self.MAX_SPEED if self._velocity[i] > 0 else -self.MAX_SPEED
        if self._player_input[0] == 0:
            self._velocity[0] *= self.FRICTION
        if self._player_input[1] == 0:
            self._velocity[1] *= self.FRICTION
        new_x = self._position[0] + self._velocity[0]
        new_y = self._position[1] + self._velocity[1]
        new_x = max(130, min(self._screen_width - 130, new_x))
        new_y = max(80, min(self._screen_height - 150, new_y))
        self._position = (int(new_x), int(new_y))

    # ── Render pipeline ────────────────────────────────────────────────────

    def render(self, surface: pygame.Surface) -> None:
        if self._phantom_visible:
            self._render_phantom(surface)

        if not self._visible:
            return
        self.update_animation()
        cx, cy = self._position

        self._render_engine_glow(surface, cx, cy)
        self._render_wings(surface, cx, cy)
        self._render_body(surface, cx, cy)
        self._render_docking_bay(surface, cx, cy)
        self._render_bridge(surface, cx, cy)
        self._render_details(surface, cx, cy)
        self._render_engines(surface, cx, cy)

    def _render_phantom(self, surface: pygame.Surface) -> None:
        """Draw a holographic preview matching the actual mothership silhouette."""
        cx, cy = self._initial_x, self._initial_y
        sw, sh = surface.get_width(), surface.get_height()
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 1000.0 * 2.5)

        # Reuse cached surface — only reallocate on size change or first use
        if self._phantom_surf is None or self._phantom_surf_size != (sw, sh):
            phantom = pygame.Surface((sw, sh), pygame.SRCALPHA)
            try:
                self._phantom_surf = phantom.convert_alpha()
            except pygame.error:
                self._phantom_surf = phantom
            self._phantom_surf_size = (sw, sh)
        phantom = self._phantom_surf
        phantom.fill((0, 0, 0, 0))

        base_alpha = int(35 + 20 * pulse)
        glow_alpha = int(15 + 10 * pulse)
        teal = (55, 188, 225)

        glow_color = (*teal, glow_alpha)
        self._draw_phantom_hull(phantom, cx, cy, glow_color, 6)
        self._draw_phantom_wings(phantom, cx, cy, glow_color, 6)

        wire_color = (*teal, base_alpha)
        self._draw_phantom_hull(phantom, cx, cy, wire_color, 2)
        self._draw_phantom_wings(phantom, cx, cy, wire_color, 2)
        self._draw_phantom_docking_bay(phantom, cx, cy, wire_color)
        self._draw_phantom_engines(phantom, cx, cy, pulse)

        surface.blit(phantom, (0, 0))

    def _draw_phantom_hull(self, surface: pygame.Surface, cx: int, cy: int,
                           color: tuple, width: int) -> None:
        """Hull outline matching the actual hull_outer polygon."""
        hull = [
            (cx, cy - 108),
            (cx + 104, cy - 22),
            (cx + 100, cy + 18),
            (cx + 72, cy + 68),
            (cx + 55, cy + 92),
            (cx - 55, cy + 92),
            (cx - 72, cy + 68),
            (cx - 100, cy + 18),
            (cx - 104, cy - 22),
        ]
        pygame.draw.polygon(surface, color, hull, width)

    def _draw_phantom_wings(self, surface: pygame.Surface, cx: int, cy: int,
                            color: tuple, width: int) -> None:
        """Wing outlines matching the actual wing_outer polygons."""
        left_wing = [
            (cx - 60, cy - 15),
            (cx - 215, cy + 30),
            (cx - 198, cy + 62),
            (cx - 163, cy + 75),
            (cx - 86, cy + 38),
        ]
        right_wing = [
            (cx + 60, cy - 15),
            (cx + 215, cy + 30),
            (cx + 198, cy + 62),
            (cx + 163, cy + 75),
            (cx + 86, cy + 38),
        ]
        pygame.draw.polygon(surface, color, left_wing, width)
        pygame.draw.polygon(surface, color, right_wing, width)

    def _draw_phantom_docking_bay(self, surface: pygame.Surface, cx: int, cy: int,
                                  color: tuple) -> None:
        """Docking bay indicator on the phantom."""
        bay = [
            (cx - 38, cy + 35),
            (cx - 32, cy + 84),
            (cx + 32, cy + 84),
            (cx + 38, cy + 35),
        ]
        pygame.draw.polygon(surface, color, bay, 1)
        # Guide lines
        pygame.draw.line(surface, color, (cx - 24, cy + 40), (cx - 20, cy + 76), 1)
        pygame.draw.line(surface, color, (cx + 24, cy + 40), (cx + 20, cy + 76), 1)

    def _draw_phantom_engines(self, surface: pygame.Surface, cx: int, cy: int,
                              pulse: float) -> None:
        """Engine glow indicators on the phantom."""
        engine_alpha = int(40 + 30 * pulse)
        engine_color = (55, 188, 225, engine_alpha)
        for nx in [cx - 172, cx + 172]:
            pygame.draw.ellipse(surface, engine_color,
                                (nx - 10, cy + 22, 20, 10))
            pygame.draw.ellipse(surface, engine_color,
                                (nx - 6, cy + 48, 12, 6))

    # ── Engine glow (back layer) ───────────────────────────────────────────

    def _render_engine_glow(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        engine_spots = [
            (cx - 160, cy + 35),   # left wing nacelle
            (cx + 160, cy + 35),   # right wing nacelle
            (cx, cy + 95),         # central thruster
        ]
        for ex, ey in engine_spots:
            pulse = 1.0 + 0.3 * self._engine_pulse
            glow_radius = int(28 * pulse)
            draw_glow_circle(surface, (ex, ey), 14, self._colors['engine_glow'], glow_radius)
            core_radius = int(7 + 3 * self._engine_pulse)
            draw_glow_circle(surface, (ex, ey), core_radius, self._colors['engine_core'], 7)

    # ── Swept-back wings ───────────────────────────────────────────────────

    def _render_wings(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        # ── Left wing ──
        left_outer = [
            (cx - 60, cy - 15),
            (cx - 215, cy + 30),
            (cx - 198, cy + 62),
            (cx - 163, cy + 75),
            (cx - 86, cy + 38),
        ]
        pygame.draw.polygon(surface, self._colors['wing_dark'], left_outer)
        left_mid = [
            (cx - 55, cy - 10),
            (cx - 180, cy + 25),
            (cx - 168, cy + 52),
            (cx - 140, cy + 62),
            (cx - 78, cy + 32),
        ]
        pygame.draw.polygon(surface, self._colors['wing_mid'], left_mid)
        left_top = [
            (cx - 48, cy - 5),
            (cx - 138, cy + 20),
            (cx - 128, cy + 39),
            (cx - 104, cy + 45),
            (cx - 72, cy + 25),
        ]
        pygame.draw.polygon(surface, self._colors['wing_light'], left_top)
        pygame.draw.line(surface, self._colors['accent_dim'],
                         (cx - 60, cy - 15), (cx - 215, cy + 30), 3)
        pygame.draw.line(surface, self._colors['panel_line'],
                         (cx - 100, cy + 8), (cx - 138, cy + 43), 1)

        # ── Right wing ──
        right_outer = [
            (cx + 60, cy - 15),
            (cx + 215, cy + 30),
            (cx + 198, cy + 62),
            (cx + 163, cy + 75),
            (cx + 86, cy + 38),
        ]
        pygame.draw.polygon(surface, self._colors['wing_dark'], right_outer)
        right_mid = [
            (cx + 55, cy - 10),
            (cx + 180, cy + 25),
            (cx + 168, cy + 52),
            (cx + 140, cy + 62),
            (cx + 78, cy + 32),
        ]
        pygame.draw.polygon(surface, self._colors['wing_mid'], right_mid)
        right_top = [
            (cx + 48, cy - 5),
            (cx + 138, cy + 20),
            (cx + 128, cy + 39),
            (cx + 104, cy + 45),
            (cx + 72, cy + 25),
        ]
        pygame.draw.polygon(surface, self._colors['wing_light'], right_top)
        pygame.draw.line(surface, self._colors['accent_dim'],
                         (cx + 60, cy - 15), (cx + 215, cy + 30), 3)
        pygame.draw.line(surface, self._colors['panel_line'],
                         (cx + 100, cy + 8), (cx + 138, cy + 43), 1)

        # ── Engine nacelles ──
        for nx in [cx - 172, cx + 172]:
            nacelle_points = [
                (nx - 14, cy + 22),
                (nx + 14, cy + 22),
                (nx + 10, cy + 50),
                (nx - 10, cy + 50),
            ]
            pygame.draw.polygon(surface, self._colors['hull_mid'], nacelle_points)
            pygame.draw.polygon(surface, self._colors['hull_light'], nacelle_points, 1)
            pygame.draw.rect(surface, self._colors['hull_dark'],
                             (nx - 10, cy + 18, 20, 6))
            pygame.draw.ellipse(surface, self._colors['engine_outer'],
                                (nx - 10, cy + 48, 20, 8))
            pygame.draw.ellipse(surface, self._colors['engine_glow'],
                                (nx - 5, cy + 50, 10, 5))

    # ── Main hull ──────────────────────────────────────────────────────────

    def _render_body(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        # Layer 0: outer silhouette
        hull_outer = [
            (cx, cy - 108),
            (cx + 104, cy - 22),
            (cx + 100, cy + 18),
            (cx + 72, cy + 68),
            (cx + 55, cy + 92),
            (cx - 55, cy + 92),
            (cx - 72, cy + 68),
            (cx - 100, cy + 18),
            (cx - 104, cy - 22),
        ]
        pygame.draw.polygon(surface, self._colors['hull_dark'], hull_outer)

        # Layer 1
        hull_mid = [
            (cx, cy - 94),
            (cx + 82, cy - 16),
            (cx + 78, cy + 16),
            (cx + 58, cy + 60),
            (cx + 42, cy + 84),
            (cx - 42, cy + 84),
            (cx - 58, cy + 60),
            (cx - 78, cy + 16),
            (cx - 82, cy - 16),
        ]
        pygame.draw.polygon(surface, self._colors['hull_mid'], hull_mid)

        # Layer 2
        hull_light = [
            (cx, cy - 80),
            (cx + 66, cy - 10),
            (cx + 62, cy + 22),
            (cx + 46, cy + 56),
            (cx + 28, cy + 78),
            (cx - 28, cy + 78),
            (cx - 46, cy + 56),
            (cx - 62, cy + 22),
            (cx - 66, cy - 10),
        ]
        pygame.draw.polygon(surface, self._colors['hull_light'], hull_light)

        # Layer 3: spine highlight
        hull_highlight = [
            (cx, cy - 66),
            (cx + 32, cy - 6),
            (cx + 28, cy + 26),
            (cx + 14, cy + 52),
            (cx - 14, cy + 52),
            (cx - 28, cy + 26),
            (cx - 32, cy - 6),
        ]
        pygame.draw.polygon(surface, self._colors['hull_highlight'], hull_highlight)

        # Outline
        pygame.draw.polygon(surface, self._colors['hull_highlight'], hull_outer, 3)

        # Centerline
        pygame.draw.line(surface, self._colors['panel_line'],
                         (cx, cy - 98), (cx, cy + 82), 1)

    # ── Underside docking bay ──────────────────────────────────────────────

    def _render_docking_bay(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        bay_points = [
            (cx - 38, cy + 35),
            (cx - 32, cy + 84),
            (cx + 32, cy + 84),
            (cx + 38, cy + 35),
        ]
        pygame.draw.polygon(surface, (10, 12, 22), bay_points)
        pygame.draw.polygon(surface, self._colors['hull_light'], bay_points, 1)

        pygame.draw.line(surface, self._colors['panel_line'],
                         (cx - 24, cy + 40), (cx - 20, cy + 76), 1)
        pygame.draw.line(surface, self._colors['panel_line'],
                         (cx + 24, cy + 40), (cx + 20, cy + 76), 1)

        0.6 + 0.4 * self._engine_pulse
        for side in [-1, 1]:
            for gy in [cy + 44, cy + 56, cy + 68]:
                gx = cx + side * 22
                draw_glow_circle(surface, (gx, gy), 3, self._colors['dock_guide'], 8)
                pygame.draw.circle(surface, self._colors['dock_guide'], (gx, gy), 3)
                alt_color = (
                    min(255, self._colors['dock_guide'][0] + 60),
                    min(255, self._colors['dock_guide'][1] + 40),
                    min(255, self._colors['dock_guide'][2] + 40),
                )
                pygame.draw.circle(surface, alt_color, (gx, gy), 1)

        beacon_y = cy + 60
        draw_glow_circle(surface, (cx, beacon_y), 5, self._colors['dock_guide_dim'], 14)
        pygame.draw.circle(surface, self._colors['dock_guide'], (cx, beacon_y), 5)

    # ── Bridge tower ───────────────────────────────────────────────────────

    def _render_bridge(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        # Bridge base platform
        bridge_base = [
            (cx - 28, cy - 38),
            (cx + 28, cy - 38),
            (cx + 22, cy - 26),
            (cx - 22, cy - 26),
        ]
        pygame.draw.polygon(surface, self._colors['hull_dark'], bridge_base)
        pygame.draw.polygon(surface, self._colors['hull_highlight'], bridge_base, 1)

        # Bridge superstructure
        bridge_body = [
            (cx - 18, cy - 62),
            (cx + 18, cy - 62),
            (cx + 22, cy - 38),
            (cx - 22, cy - 38),
        ]
        pygame.draw.polygon(surface, self._colors['hull_mid'], bridge_body)
        pygame.draw.polygon(surface, self._colors['hull_light'], bridge_body, 1)

        # Cyan canopy
        canopy = [
            (cx - 10, cy - 58),
            (cx + 10, cy - 58),
            (cx + 14, cy - 44),
            (cx - 14, cy - 44),
        ]
        pygame.draw.polygon(surface, self._colors['glass_dark'], canopy)
        pygame.draw.polygon(surface, self._colors['glass_mid'], canopy, 2)

        # Glass reflection
        reflection = [
            (cx - 5, cy - 54),
            (cx + 2, cy - 54),
            (cx + 3, cy - 48),
            (cx - 3, cy - 48),
        ]
        pygame.draw.polygon(surface, self._colors['glass_bright'], reflection)

        # Antenna spire
        pygame.draw.line(surface, self._colors['hull_highlight'],
                         (cx, cy - 62), (cx, cy - 86), 2)
        pygame.draw.circle(surface, self._colors['engine_glow'], (cx, cy - 86), 3)
        draw_glow_circle(surface, (cx, cy - 86), 2, self._colors['running_light'], 7)

    # ── Hull details ───────────────────────────────────────────────────────

    def _render_details(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        # Upper hull chevron panel lines
        for offset_y in [-54, -34, -12]:
            line_w = 22 + offset_y + 54
            pygame.draw.line(surface, self._colors['panel_line'],
                             (cx - line_w, cy + offset_y),
                             (cx + line_w, cy + offset_y), 1)

        # Side panel seams
        for sx in [-60, 60]:
            pygame.draw.line(surface, self._colors['panel_line'],
                             (sx + cx, cy - 16), (sx + cx, cy + 32), 1)
        for sx in [-44, 44]:
            pygame.draw.line(surface, self._colors['panel_line'],
                             (sx + cx, cy + 2), (sx + cx, cy + 68), 1)

        # Amber running lights
        for lx in [cx - 96, cx + 96]:
            ly = cy - 12
            draw_glow_circle(surface, (lx, ly), 3, self._colors['accent'], 9)
            pygame.draw.circle(surface, self._colors['accent'], (lx, ly), 3)

        # Stern lights
        for lx in [cx - 36, cx + 36]:
            pygame.draw.circle(surface, self._colors['accent_dim'], (lx, cy + 88), 3)

        # Bow accent chevron
        pygame.draw.line(surface, self._colors['accent_dim'],
                         (cx - 14, cy - 74), (cx, cy - 88), 2)
        pygame.draw.line(surface, self._colors['accent_dim'],
                         (cx + 14, cy - 74), (cx, cy - 88), 2)

        # Hull classification marks
        for mx in [cx - 52, cx - 30, cx - 8]:
            pygame.draw.circle(surface, self._colors['panel_line'], (mx, cy - 54), 1)
        for mx in [cx + 8, cx + 30, cx + 52]:
            pygame.draw.circle(surface, self._colors['panel_line'], (mx, cy - 54), 1)

        # Docking bay approach light stripe — cached surface
        if not hasattr(self, '_stripe_cache') or self._stripe_cache is None:
            self._stripe_cache = pygame.Surface((40, 2), pygame.SRCALPHA)
        stripe_alpha = int(40 + 20 * self._engine_pulse)
        self._stripe_cache.fill((0, 0, 0, 0))
        self._stripe_cache.fill((*self._colors['dock_guide'][:3], stripe_alpha))
        surface.blit(self._stripe_cache, (cx - 20, cy + 32))

    # ── Engine nozzles ─────────────────────────────────────────────────────

    def _render_engines(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        engine_defs = [
            (cx - 160, cy + 35, 0.0),
            (cx + 160, cy + 35, 1.2),
            (cx, cy + 95, 2.4),
        ]
        for ex, ey, phase in engine_defs:
            pulse = 0.7 + 0.3 * math.sin(self._animation_time * 3 + phase)

            nozzle_rect = pygame.Rect(ex - 12, ey - 5, 24, 16)
            pygame.draw.rect(surface, self._colors['hull_dark'], nozzle_rect)
            pygame.draw.rect(surface, self._colors['hull_highlight'], nozzle_rect, 2)

            inner_rect = pygame.Rect(ex - 7, ey - 2, 14, 10)
            pygame.draw.rect(surface, self._colors['engine_outer'], inner_rect)

            core_h = int(7 * pulse)
            core_rect = pygame.Rect(ex - 3, ey, 6, core_h)
            pygame.draw.rect(surface, self._colors['engine_core'], core_rect)

            flame_h = int(10 * pulse)
            if flame_h > 1:
                pygame.draw.rect(surface, (*self._colors['engine_glow'][:3], 180),
                                 (ex - 2, ey + core_h, 4, flame_h))
