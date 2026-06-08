"""Mothership renderer — visual hull, phantom preview, and z-order pipeline.

Extracted from :class:`MotherShip` in Phase 5-γ. Owns the 22-color
palette, the cached ``_phantom_surf`` / ``_stripe_cache`` surfaces,
and the 9 ``_render_*`` methods + 4 ``_draw_phantom_*`` helpers.

The renderer holds a reference to the :class:`MotherShip` facade for
inversion-of-control — it reads live motion state (position, pulse
values, phantom timer) from the facade's ``_motion`` component.
This mirrors the Phase 5-β ``boss.py`` pattern.
"""

import math

import pygame

from airwar.utils._sprites_common import draw_glow_circle


class MotherShipRenderer:
    """Renders the mothership visual — hull, phantom, weapons, docking bay.

    Public surface (called by :class:`MotherShip` facade):

    - :meth:`render` — z-order orchestrator
    - :meth:`_render_phantom` — holographic preview (test-reachable)
    - :meth:`_get_phantom_reveal` — phantom fade math (test-reachable)

    Owned state: ``_phantom_surf``, ``_phantom_surf_size``,
    ``_stripe_cache``, and the 22-entry ``_colors`` dict.

    Reads from the motion (via ``self._mother_ship._motion``):
    ``_visible``, ``_phantom_visible``, ``_phantom_started_at``,
    ``_phantom_fade_duration_ms``, ``_initial_x``, ``_initial_y``,
    ``_position``, ``_animation_time``, ``_engine_pulse``,
    ``_wing_pulse``.
    """

    def __init__(self, mother_ship) -> None:
        self._mother_ship = mother_ship

        # Cached surfaces (Phase 5-γ: re-allocated on size change or first use)
        self._phantom_surf = None
        self._phantom_surf_size = (0, 0)
        self._stripe_cache = None

        self._colors = {
            "hull_dark": (18, 22, 32),
            "hull_mid": (34, 42, 58),
            "hull_light": (62, 72, 88),
            "hull_highlight": (154, 164, 174),
            "wing_dark": (16, 20, 30),
            "wing_mid": (30, 38, 52),
            "wing_light": (58, 68, 84),
            "glass_dark": (18, 110, 142),
            "glass_mid": (44, 184, 214),
            "glass_bright": (170, 244, 252),
            "engine_core": (200, 230, 255),
            "engine_glow": (100, 180, 255),
            "engine_outer": (50, 120, 200),
            "accent": (216, 168, 104),
            "accent_dim": (146, 112, 78),
            "dock_guide": (80, 220, 160),
            "dock_guide_dim": (40, 160, 110),
            "running_light": (140, 170, 210),
            "panel_line": (78, 88, 106),
            "armor_shadow": (8, 10, 18),
            "weapon_dark": (12, 15, 24),
            "warning_red": (218, 76, 64),
        }

    # ── Render pipeline ───────────────────────────────────────────────────

    def render(self, surface: pygame.Surface) -> None:
        motion = self._mother_ship._motion
        if motion._phantom_visible:
            self._render_phantom(surface)

        if not motion._visible:
            return
        motion.update_animation()
        cx, cy = motion._position

        self._render_engine_glow(surface, cx, cy)
        self._render_side_sponsons(surface, cx, cy)
        self._render_body(surface, cx, cy)
        self._render_weapon_bays(surface, cx, cy)
        self._render_docking_bay(surface, cx, cy)
        self._render_bridge(surface, cx, cy)
        self._render_details(surface, cx, cy)
        self._render_engines(surface, cx, cy)

    # ── Phantom preview ───────────────────────────────────────────────────

    def _render_phantom(self, surface: pygame.Surface) -> None:
        """Draw a holographic preview matching the actual mothership silhouette."""
        motion = self._mother_ship._motion
        reveal = self._get_phantom_reveal()
        if reveal <= 0:
            return

        cx = motion._initial_x
        cy = motion._initial_y + int((1.0 - reveal) * 22)
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

        base_alpha = int((35 + 20 * pulse) * reveal)
        glow_alpha = int((15 + 10 * pulse) * reveal)
        teal = (55, 188, 225)

        glow_color = (*teal, glow_alpha)
        self._draw_phantom_hull(phantom, cx, cy, glow_color, 6)
        self._draw_phantom_sponsons(phantom, cx, cy, glow_color, 6)

        wire_color = (*teal, base_alpha)
        self._draw_phantom_hull(phantom, cx, cy, wire_color, 2)
        self._draw_phantom_sponsons(phantom, cx, cy, wire_color, 2)
        self._draw_phantom_docking_bay(phantom, cx, cy, wire_color)
        self._draw_phantom_engines(phantom, cx, cy, pulse)

        surface.blit(phantom, (0, 0))

    def _get_phantom_reveal(self, now_ms: int | None = None) -> float:
        motion = self._mother_ship._motion
        if not motion._phantom_visible:
            return 0.0

        now = pygame.time.get_ticks() if now_ms is None else now_ms
        elapsed = max(0, now - motion._phantom_started_at)
        t = min(1.0, elapsed / motion._phantom_fade_duration_ms)
        return 1 - (1 - t) ** 3

    def _draw_phantom_hull(self, surface: pygame.Surface, cx: int, cy: int, color: tuple, width: int) -> None:
        """Hull outline matching the carrier hull_outer polygon."""
        hull = [
            (cx, cy - 124),
            (cx + 78, cy - 82),
            (cx + 108, cy - 20),
            (cx + 92, cy + 56),
            (cx + 54, cy + 108),
            (cx - 54, cy + 108),
            (cx - 92, cy + 56),
            (cx - 108, cy - 20),
            (cx - 78, cy - 82),
        ]
        pygame.draw.polygon(surface, color, hull, width)

    def _draw_phantom_sponsons(self, surface: pygame.Surface, cx: int, cy: int, color: tuple, width: int) -> None:
        """Side sponson outlines matching the actual carrier silhouette."""
        left_sponson = [
            (cx - 68, cy - 58),
            (cx - 230, cy - 20),
            (cx - 252, cy + 34),
            (cx - 222, cy + 76),
            (cx - 116, cy + 70),
            (cx - 92, cy + 22),
        ]
        right_sponson = [
            (cx + 68, cy - 58),
            (cx + 230, cy - 20),
            (cx + 252, cy + 34),
            (cx + 222, cy + 76),
            (cx + 116, cy + 70),
            (cx + 92, cy + 22),
        ]
        pygame.draw.polygon(surface, color, left_sponson, width)
        pygame.draw.polygon(surface, color, right_sponson, width)

    def _draw_phantom_docking_bay(self, surface: pygame.Surface, cx: int, cy: int, color: tuple) -> None:
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

    def _draw_phantom_engines(self, surface: pygame.Surface, cx: int, cy: int, pulse: float) -> None:
        """Engine glow indicators on the phantom."""
        engine_alpha = int(40 + 30 * pulse)
        engine_color = (55, 188, 225, engine_alpha)
        for nx in [cx - 198, cx - 132, cx + 132, cx + 198]:
            pygame.draw.ellipse(surface, engine_color, (nx - 11, cy + 72, 22, 9))
        pygame.draw.ellipse(surface, engine_color, (cx - 18, cy + 100, 36, 12))

    # ── Engine glow (back layer) ───────────────────────────────────────────

    def _render_engine_glow(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        engine_spots = [
            (cx - 198, cy + 78),
            (cx - 132, cy + 82),
            (cx + 132, cy + 82),
            (cx + 198, cy + 78),
            (cx, cy + 106),
        ]
        for ex, ey in engine_spots:
            pulse = 1.0 + 0.3 * self._mother_ship._motion._engine_pulse
            glow_radius = int(28 * pulse)
            draw_glow_circle(surface, (ex, ey), 14, self._colors["engine_glow"], glow_radius)
            core_radius = int(7 + 3 * self._mother_ship._motion._engine_pulse)
            draw_glow_circle(surface, (ex, ey), core_radius, self._colors["engine_core"], 7)

    # ── Side weapon sponsons ───────────────────────────────────────────────

    def _render_side_sponsons(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        for side in [-1, 1]:
            outer = [
                (cx + side * 68, cy - 58),
                (cx + side * 230, cy - 20),
                (cx + side * 252, cy + 34),
                (cx + side * 222, cy + 76),
                (cx + side * 116, cy + 70),
                (cx + side * 92, cy + 22),
            ]
            mid = [
                (cx + side * 78, cy - 46),
                (cx + side * 210, cy - 14),
                (cx + side * 226, cy + 30),
                (cx + side * 204, cy + 62),
                (cx + side * 124, cy + 58),
                (cx + side * 104, cy + 18),
            ]
            top = [
                (cx + side * 94, cy - 30),
                (cx + side * 182, cy - 8),
                (cx + side * 194, cy + 22),
                (cx + side * 174, cy + 44),
                (cx + side * 128, cy + 42),
                (cx + side * 112, cy + 10),
            ]
            pygame.draw.polygon(surface, self._colors["armor_shadow"], outer)
            pygame.draw.polygon(surface, self._colors["wing_dark"], outer, 2)
            pygame.draw.polygon(surface, self._colors["wing_mid"], mid)
            pygame.draw.polygon(surface, self._colors["wing_light"], top)
            pygame.draw.line(
                surface,
                self._colors["accent_dim"],
                (cx + side * 92, cy - 36),
                (cx + side * 218, cy + 4),
                2,
            )
            pygame.draw.line(
                surface,
                self._colors["panel_line"],
                (cx + side * 126, cy + 12),
                (cx + side * 196, cy + 32),
                1,
            )

            for offset in [132, 198]:
                nx = cx + side * offset
                nacelle = pygame.Rect(nx - 18, cy + 58, 36, 34)
                pygame.draw.rect(surface, self._colors["weapon_dark"], nacelle, border_radius=3)
                pygame.draw.rect(surface, self._colors["hull_highlight"], nacelle, 1, border_radius=3)
                pygame.draw.rect(surface, self._colors["engine_outer"], (nx - 12, cy + 76, 24, 9))
                pygame.draw.rect(surface, self._colors["engine_glow"], (nx - 7, cy + 80, 14, 5))

    # ── Main hull ──────────────────────────────────────────────────────────

    def _render_body(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        # Layer 0: outer silhouette
        hull_outer = [
            (cx, cy - 124),
            (cx + 78, cy - 82),
            (cx + 108, cy - 20),
            (cx + 92, cy + 56),
            (cx + 54, cy + 108),
            (cx - 54, cy + 108),
            (cx - 92, cy + 56),
            (cx - 108, cy - 20),
            (cx - 78, cy - 82),
        ]
        pygame.draw.polygon(surface, self._colors["hull_dark"], hull_outer)

        # Layer 1
        hull_mid = [
            (cx, cy - 108),
            (cx + 62, cy - 70),
            (cx + 84, cy - 16),
            (cx + 70, cy + 50),
            (cx + 42, cy + 92),
            (cx - 42, cy + 92),
            (cx - 70, cy + 50),
            (cx - 84, cy - 16),
            (cx - 62, cy - 70),
        ]
        pygame.draw.polygon(surface, self._colors["hull_mid"], hull_mid)

        # Layer 2
        hull_light = [
            (cx, cy - 92),
            (cx + 44, cy - 54),
            (cx + 58, cy - 6),
            (cx + 48, cy + 44),
            (cx + 24, cy + 74),
            (cx - 24, cy + 74),
            (cx - 48, cy + 44),
            (cx - 58, cy - 6),
            (cx - 44, cy - 54),
        ]
        pygame.draw.polygon(surface, self._colors["hull_light"], hull_light)

        # Layer 3: spine highlight
        hull_highlight = [
            (cx, cy - 76),
            (cx + 26, cy - 30),
            (cx + 24, cy + 22),
            (cx + 10, cy + 54),
            (cx - 10, cy + 54),
            (cx - 24, cy + 22),
            (cx - 26, cy - 30),
        ]
        pygame.draw.polygon(surface, self._colors["hull_highlight"], hull_highlight)

        # Outline
        pygame.draw.polygon(surface, self._colors["hull_highlight"], hull_outer, 3)

        # Centerline
        pygame.draw.line(surface, self._colors["panel_line"], (cx, cy - 108), (cx, cy + 94), 1)

    def _render_weapon_bays(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        for side in [-1, 1]:
            bay_rect = pygame.Rect(cx + side * 92 - 18, cy - 2, 36, 42)
            pygame.draw.rect(surface, self._colors["weapon_dark"], bay_rect, border_radius=3)
            pygame.draw.rect(surface, self._colors["hull_highlight"], bay_rect, 1, border_radius=3)
            for barrel_y in [cy + 8, cy + 22]:
                pygame.draw.line(
                    surface,
                    self._colors["panel_line"],
                    (cx + side * 92, barrel_y),
                    (cx + side * 132, barrel_y + side * 4),
                    3,
                )
                pygame.draw.circle(surface, self._colors["warning_red"], (cx + side * 134, barrel_y + side * 4), 2)

    # ── Underside docking bay ──────────────────────────────────────────────

    def _render_docking_bay(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        bay_points = [
            (cx - 46, cy + 36),
            (cx - 34, cy + 96),
            (cx + 34, cy + 96),
            (cx + 46, cy + 36),
        ]
        pygame.draw.polygon(surface, (10, 12, 22), bay_points)
        pygame.draw.polygon(surface, self._colors["hull_light"], bay_points, 1)

        pygame.draw.line(surface, self._colors["panel_line"], (cx - 28, cy + 44), (cx - 20, cy + 86), 1)
        pygame.draw.line(surface, self._colors["panel_line"], (cx + 28, cy + 44), (cx + 20, cy + 86), 1)

        for side in [-1, 1]:
            for gy in [cy + 48, cy + 62, cy + 76]:
                gx = cx + side * 26
                draw_glow_circle(surface, (gx, gy), 3, self._colors["dock_guide"], 8)
                pygame.draw.circle(surface, self._colors["dock_guide"], (gx, gy), 3)
                alt_color = (
                    min(255, self._colors["dock_guide"][0] + 60),
                    min(255, self._colors["dock_guide"][1] + 40),
                    min(255, self._colors["dock_guide"][2] + 40),
                )
                pygame.draw.circle(surface, alt_color, (gx, gy), 1)

        beacon_y = cy + 66
        draw_glow_circle(surface, (cx, beacon_y), 5, self._colors["dock_guide_dim"], 14)
        pygame.draw.circle(surface, self._colors["dock_guide"], (cx, beacon_y), 5)

    # ── Bridge tower ───────────────────────────────────────────────────────

    def _render_bridge(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        # Bridge base platform
        bridge_base = [
            (cx - 36, cy - 54),
            (cx + 36, cy - 54),
            (cx + 28, cy - 38),
            (cx - 28, cy - 38),
        ]
        pygame.draw.polygon(surface, self._colors["hull_dark"], bridge_base)
        pygame.draw.polygon(surface, self._colors["hull_highlight"], bridge_base, 1)

        # Bridge superstructure
        bridge_body = [
            (cx - 22, cy - 82),
            (cx + 22, cy - 82),
            (cx + 24, cy - 54),
            (cx - 24, cy - 54),
        ]
        pygame.draw.polygon(surface, self._colors["hull_mid"], bridge_body)
        pygame.draw.polygon(surface, self._colors["hull_light"], bridge_body, 1)

        # Cyan canopy
        canopy = [
            (cx - 12, cy - 76),
            (cx + 12, cy - 76),
            (cx + 15, cy - 60),
            (cx - 15, cy - 60),
        ]
        pygame.draw.polygon(surface, self._colors["glass_dark"], canopy)
        pygame.draw.polygon(surface, self._colors["glass_mid"], canopy, 2)

        # Glass reflection
        reflection = [
            (cx - 6, cy - 72),
            (cx + 3, cy - 72),
            (cx + 4, cy - 66),
            (cx - 4, cy - 66),
        ]
        pygame.draw.polygon(surface, self._colors["glass_bright"], reflection)

        # Antenna spire
        pygame.draw.line(surface, self._colors["hull_highlight"], (cx, cy - 82), (cx, cy - 108), 2)
        pygame.draw.circle(surface, self._colors["engine_glow"], (cx, cy - 108), 3)
        draw_glow_circle(surface, (cx, cy - 108), 2, self._colors["running_light"], 7)

    # ── Hull details ───────────────────────────────────────────────────────

    def _render_details(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        # Upper hull chevron panel lines
        for offset_y in [-62, -38, -14]:
            line_w = 28 + offset_y + 62
            pygame.draw.line(
                surface, self._colors["panel_line"], (cx - line_w, cy + offset_y), (cx + line_w, cy + offset_y), 1
            )

        # Side panel seams
        for sx in [-60, 60]:
            pygame.draw.line(surface, self._colors["panel_line"], (sx + cx, cy - 24), (sx + cx, cy + 42), 1)
        for sx in [-44, 44]:
            pygame.draw.line(surface, self._colors["panel_line"], (sx + cx, cy + 4), (sx + cx, cy + 78), 1)

        # Amber running lights
        for lx in [cx - 118, cx + 118, cx - 206, cx + 206]:
            ly = cy - 10 if abs(lx - cx) < 160 else cy + 24
            draw_glow_circle(surface, (lx, ly), 3, self._colors["accent"], 9)
            pygame.draw.circle(surface, self._colors["accent"], (lx, ly), 3)

        # Stern lights
        for lx in [cx - 36, cx + 36]:
            pygame.draw.circle(surface, self._colors["accent_dim"], (lx, cy + 104), 3)

        # Bow accent chevron
        pygame.draw.line(surface, self._colors["accent_dim"], (cx - 16, cy - 92), (cx, cy - 112), 2)
        pygame.draw.line(surface, self._colors["accent_dim"], (cx + 16, cy - 92), (cx, cy - 112), 2)

        # Hull classification marks
        for mx in [cx - 54, cx - 32, cx - 10, cx + 10, cx + 32, cx + 54]:
            pygame.draw.circle(surface, self._colors["panel_line"], (mx, cy - 62), 1)

        # Docking bay approach light stripe — cached surface
        if self._stripe_cache is None:
            self._stripe_cache = pygame.Surface((40, 2), pygame.SRCALPHA)
        stripe_alpha = int(40 + 20 * self._mother_ship._motion._engine_pulse)
        self._stripe_cache.fill((0, 0, 0, 0))
        self._stripe_cache.fill((*self._colors["dock_guide"][:3], stripe_alpha))
        surface.blit(self._stripe_cache, (cx - 20, cy + 32))

    # ── Engine nozzles ─────────────────────────────────────────────────────

    def _render_engines(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        engine_defs = [
            (cx - 198, cy + 78, 0.0),
            (cx - 132, cy + 82, 0.7),
            (cx + 132, cy + 82, 1.4),
            (cx + 198, cy + 78, 2.1),
            (cx, cy + 106, 2.8),
        ]
        animation_time = self._mother_ship._motion._animation_time
        for ex, ey, phase in engine_defs:
            pulse = 0.7 + 0.3 * math.sin(animation_time * 3 + phase)

            nozzle_rect = pygame.Rect(ex - 12, ey - 5, 24, 16)
            pygame.draw.rect(surface, self._colors["hull_dark"], nozzle_rect)
            pygame.draw.rect(surface, self._colors["hull_highlight"], nozzle_rect, 2)

            inner_rect = pygame.Rect(ex - 7, ey - 2, 14, 10)
            pygame.draw.rect(surface, self._colors["engine_outer"], inner_rect)

            core_h = int(7 * pulse)
            core_rect = pygame.Rect(ex - 3, ey, 6, core_h)
            pygame.draw.rect(surface, self._colors["engine_core"], core_rect)

            flame_h = int(10 * pulse)
            if flame_h > 1:
                pygame.draw.rect(surface, (*self._colors["engine_glow"][:3], 180), (ex - 2, ey + core_h, 4, flame_h))


__all__ = ["MotherShipRenderer"]
