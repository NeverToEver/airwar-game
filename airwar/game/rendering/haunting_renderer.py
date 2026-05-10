"""Haunting visual layer for late-game psychological distortion effects."""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Any, Iterable

import pygame

from airwar.core_bindings import RUST_AVAILABLE, batch_hallucinated_enemy_centers
from airwar.utils.fonts import get_cjk_font


def _entity_center(entity) -> tuple[float, float]:
    rect = getattr(entity, "rect", None)
    return (float(getattr(rect, "centerx", 0.0)), float(getattr(rect, "centery", 0.0)))


def _mix_color(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return (
        int(a[0] * (1 - t) + b[0] * t),
        int(a[1] * (1 - t) + b[1] * t),
        int(a[2] * (1 - t) + b[2] * t),
    )


def _draw_entity_veil(surface: pygame.Surface, entity, alpha: int) -> None:
    rect = getattr(entity, "rect", None)
    if rect is None:
        return
    width = max(24, int(getattr(rect, "width", 40) * 2.9))
    height = max(24, int(getattr(rect, "height", 40) * 2.4))
    veil = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.ellipse(veil, (8, 8, 7, alpha), veil.get_rect())
    pygame.draw.ellipse(veil, (42, 44, 34, max(20, alpha // 3)), veil.get_rect(), 2)
    surface.blit(veil, veil.get_rect(center=(int(rect.centerx), int(rect.centery))))


class HauntingRenderer:
    """Time-driven visual-only haunting layer.

    The renderer intentionally reads entity positions without mutating them. It
    replaces the visible style, jitters the final framebuffer, and overlays UI
    corruption while preserving gameplay state and collision rectangles.
    """

    START_FRAME = 3 * 60
    FULL_REPLACE_FRAME = 30 * 60
    MIN_EVENT_INTERVAL = 28
    MAX_EVENT_INTERVAL = 5 * 60
    MIN_EVENT_DURATION = 80
    MAX_EVENT_DURATION = 360
    MAX_MEMORY_FRAGMENTS = 18
    LIGHTNING_DURATION = 6
    JITTER_CYCLE_FRAMES = 44

    @dataclass
    class MemoryFragment:
        """Visual fragment for memory-flash overlays (crying face, letter, etc.)."""
        kind: str
        x: float
        y: float
        scale: float
        alpha: int
        age: int
        duration: int
        drift_x: float
        drift_y: float

    def __init__(self, seed: int = 1937) -> None:
        self._rng = random.Random(seed)
        self._frame = 0
        self._survival_frames = 0
        self._progression = 0.0
        self._strength = 0.0
        self._event_timer = 0
        self._event_duration = self.MIN_EVENT_DURATION
        self._next_event_in = self.MAX_EVENT_INTERVAL
        self._enemy_pressure = 0
        self._memory_fragments: list = []  # list[MemoryFragment]
        self._storm_cache: dict[tuple[int, int], pygame.Surface] = {}
        self._lightning_timer = 0
        self._lightning_points: list[list[tuple[int, int]]] = []
        self._lightning_size: tuple[int, int] | None = None
        self._overlay: pygame.Surface | None = None
        self._blend_surf: pygame.Surface | None = None
        self._distort_buf: pygame.Surface | None = None

    @property
    def progression(self) -> float:
        return self._progression

    @property
    def current_strength(self) -> float:
        return self._strength

    def is_active(self) -> bool:
        return self._strength > 0.025

    def dispose(self) -> None:
        self._storm_cache.clear()
        self._overlay = None
        self._blend_surf = None
        self._distort_buf = None

    def update(self, survival_frames: int, enemy_pressure: int = 0, enabled: bool = True) -> None:
        """Advance the visual scheduler for one gameplay frame."""
        if not enabled:
            return

        self._frame += 1
        self._survival_frames = max(0, int(survival_frames))
        self._enemy_pressure = max(0, int(enemy_pressure))
        self._progression = self._calculate_progression(self._survival_frames)
        self._update_event_schedule()
        self._strength = self._calculate_strength()
        self._advance_memory_fragments()
        self._update_lightning()

    def render_world_styles(self, surface: pygame.Surface, player: Any, enemies: Iterable, boss: Any = None) -> None:
        """Draw storm, WWI player craft, and haunted enemy overlays."""
        if not self.is_active():
            return

        self._render_storm_background(surface)
        self._occlude_original_hostiles(surface, enemies, boss)
        player_center = _entity_center(player) if player else None

        active_enemies = [e for e in enemies if getattr(e, "active", True)]
        if active_enemies and RUST_AVAILABLE:
            enemy_data = [
                (float(getattr(e.rect, "centerx", 0.0)),
                 float(getattr(e.rect, "centery", 0.0)),
                 id(e))
                for e in active_enemies
            ]
            batch_results = batch_hallucinated_enemy_centers(
                enemy_data, player_center, self._frame, self._strength, 1.0,
            )
            for enemy, (hx, hy) in zip(active_enemies, batch_results, strict=False):
                self._render_spirit_enemy_at(surface, enemy, hx, hy)
        else:
            for enemy in active_enemies:
                self._render_spirit_enemy(surface, enemy, player_center)

        if boss and getattr(boss, "active", True):
            self._render_spirit_boss(surface, boss, player_center)

        if player:
            self._render_wwi_player(surface, player)

    def distort_world(self, surface: pygame.Surface) -> None:
        """Distort only the world layer before sharp HUD text is drawn."""
        if not self.is_active():
            return
        self._apply_screen_distortion(surface)

    def render_atmosphere_overlay(self, surface: pygame.Surface) -> None:
        """Draw memories and atmospheric overlays before HUD text is rendered."""
        if not self.is_active():
            return

        self._maybe_spawn_memory_fragment(surface.get_size())
        self._render_memory_fragments(surface)
        self._render_vignette(surface)

    def render_projectile_styles(
        self, surface: pygame.Surface, player_bullets: Iterable, enemy_bullets: Iterable
    ) -> None:
        """Draw haunted projectile skins over the normal projectile render pass."""
        if not self.is_active():
            return

        overlay = self._get_overlay(*surface.get_size())
        for bullet in player_bullets:
            if getattr(bullet, "active", True):
                self._occlude_original_projectile(overlay, bullet)
                self._draw_tracer_round(overlay, bullet, player_owned=True)
        for bullet in enemy_bullets:
            if getattr(bullet, "active", True):
                self._occlude_original_projectile(overlay, bullet)
                self._draw_tracer_round(overlay, bullet, player_owned=False)
        surface.blit(overlay, (0, 0))

    def render_foreground_distortion(self, surface: pygame.Surface, state: Any = None, player: Any = None) -> None:
        """Overlay sharp corrupt UI values without resampling the HUD layer."""
        if not self.is_active():
            return

        self._render_ui_corruption(surface, state, player)

    def _calculate_progression(self, survival_frames: int) -> float:
        if survival_frames <= self.START_FRAME:
            return 0.0
        span = max(1, self.FULL_REPLACE_FRAME - self.START_FRAME)
        return min(1.0, (survival_frames - self.START_FRAME) / span)

    def _update_event_schedule(self) -> None:
        if self._progression >= 1.0:
            self._event_timer = max(self._event_timer, 1)
            return

        if self._event_timer > 0:
            self._event_timer -= 1
            return

        self._next_event_in -= 1
        if self._next_event_in <= 0 and self._progression > 0:
            self._start_event()

    def _start_event(self) -> None:
        p = self._progression
        self._event_duration = int(self.MIN_EVENT_DURATION + (self.MAX_EVENT_DURATION - self.MIN_EVENT_DURATION) * p)
        self._event_duration += self._rng.randint(-18, 54)
        self._event_duration = max(self.MIN_EVENT_DURATION, self._event_duration)
        self._event_timer = self._event_duration

        interval = int(self.MAX_EVENT_INTERVAL * (1.0 - p) + self.MIN_EVENT_INTERVAL * p)
        jitter = max(8, interval // 5)
        self._next_event_in = max(self.MIN_EVENT_INTERVAL, interval + self._rng.randint(-jitter, jitter))

    def _calculate_strength(self) -> float:
        base = self._progression**1.55
        if self._progression >= 1.0:
            return 1.0
        if self._event_timer <= 0 or self._event_duration <= 0:
            return min(1.0, base * 0.64)

        elapsed = self._event_duration - self._event_timer
        phase = max(0.0, min(1.0, elapsed / self._event_duration))
        pulse = math.sin(phase * math.pi)
        event_strength = pulse * (0.48 + self._progression * 0.58)
        return min(1.0, max(base, event_strength))

    def _advance_memory_fragments(self) -> None:
        if not self._memory_fragments:
            return

        alive: list = []  # list[MemoryFragment]
        for fragment in self._memory_fragments:
            fragment.age += 1
            fragment.x += fragment.drift_x
            fragment.y += fragment.drift_y
            if fragment.age < fragment.duration:
                alive.append(fragment)
        self._memory_fragments = alive

    def _update_lightning(self) -> None:
        if self._lightning_timer > 0:
            self._lightning_timer -= 1
            return

        chance = 0.006 + 0.030 * self._strength
        if self._rng.random() < chance:
            self._lightning_timer = self.LIGHTNING_DURATION
            self._lightning_points = []
            self._lightning_size = None

    def _render_storm_background(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        storm = self._get_storm_surface(width, height)
        alpha = min(255, int(255 * (0.16 + self._strength * 1.06)))
        if alpha >= 255:
            surface.blit(storm, (0, 0))
        else:
            if self._blend_surf is None or self._blend_surf.get_size() != (width, height):
                self._blend_surf = pygame.Surface((width, height), pygame.SRCALPHA)
            else:
                self._blend_surf.fill((0, 0, 0, 0))
            self._blend_surf.blit(storm, (0, 0))
            self._blend_surf.set_alpha(alpha)
            surface.blit(self._blend_surf, (0, 0))

        self._render_lightning(surface)

    def _get_storm_surface(self, width: int, height: int) -> pygame.Surface:
        cache_key = (width, height)
        cached = self._storm_cache.get(cache_key)
        if cached is not None:
            return cached

        storm = pygame.Surface((width, height), pygame.SRCALPHA)
        for y in range(height):
            ratio = y / max(1, height - 1)
            top = (12, 16, 22)
            mid = (38, 40, 36)
            bottom = (20, 22, 18)
            if ratio < 0.62:
                t = ratio / 0.62
                color = _mix_color(top, mid, t)
            else:
                t = (ratio - 0.62) / 0.38
                color = _mix_color(mid, bottom, t)
            pygame.draw.line(storm, color, (0, y), (width, y))

        rng = random.Random(width * 92821 + height * 6173)
        cloud = pygame.Surface((width, height), pygame.SRCALPHA)
        for _ in range(150):
            cx = rng.randint(-width // 5, width + width // 5)
            cy = rng.randint(-height // 10, int(height * 0.58))
            cw = rng.randint(max(90, width // 12), max(150, width // 4))
            ch = rng.randint(max(34, height // 24), max(70, height // 8))
            shade = rng.randint(42, 104)
            alpha = rng.randint(28, 76)
            rect = pygame.Rect(cx - cw // 2, cy - ch // 2, cw, ch)
            pygame.draw.ellipse(cloud, (shade, shade + rng.randint(0, 16), shade + rng.randint(6, 28), alpha), rect)
        storm.blit(cloud, (0, 0))

        haze = pygame.Surface((width, height), pygame.SRCALPHA)
        for index in range(11):
            y = int(height * (0.18 + index * 0.055))
            alpha = max(8, 42 - index * 3)
            pygame.draw.line(haze, (144, 146, 132, alpha), (0, y), (width, y + rng.randint(-8, 8)), 2)
        storm.blit(haze, (0, 0))

        self._storm_cache[cache_key] = storm
        return storm

    def render_hud_corruption(self, surface: pygame.Surface) -> None:
        """Apply a subtle corruption darkening over HUD layer for visual cohesion."""
        if self._strength < 0.15:
            return
        width, height = surface.get_size()
        overlay = self._get_overlay(width, height)
        alpha = int(18 + self._strength * 64)
        overlay.fill((18, 14, 10, alpha))
        surface.blit(overlay, (0, 0))

    def _render_lightning(self, surface: pygame.Surface) -> None:
        if self._lightning_timer <= 0:
            return

        width, height = surface.get_size()
        if self._lightning_size != (width, height) or not self._lightning_points:
            self._lightning_size = (width, height)
            self._lightning_points = self._make_lightning(width, height)

        flash = self._get_overlay(width, height)
        flash_alpha = int((34 + 88 * self._strength) * self._lightning_timer / self.LIGHTNING_DURATION)
        flash.fill((176, 188, 204, flash_alpha))
        for bolt in self._lightning_points:
            for start, end in zip(bolt, bolt[1:], strict=False):
                pygame.draw.line(flash, (232, 242, 255, 220), start, end, 3)
                pygame.draw.line(flash, (112, 144, 180, 180), start, end, 8)
        surface.blit(flash, (0, 0))

    def _make_lightning(self, width: int, height: int) -> list[list[tuple[int, int]]]:
        bolts: list[list[tuple[int, int]]] = []
        for _ in range(1 + int(self._strength * 2)):
            x = self._rng.randint(width // 8, width * 7 // 8)
            y = 0
            points = [(x, y)]
            while y < height * 0.56:
                x += self._rng.randint(-42, 42)
                y += self._rng.randint(26, 58)
                points.append((max(0, min(width, x)), int(y)))
            bolts.append(points)
        return bolts

    def _render_wwi_player(self, surface: pygame.Surface, player) -> None:
        width = max(42, int(getattr(player.rect, "width", 68) * 2.25))
        height = max(54, int(getattr(player.rect, "height", 82) * 1.90))
        plane = pygame.Surface((width * 2, height * 2), pygame.SRCALPHA)
        center = (plane.get_width() // 2, plane.get_height() // 2)
        scale = min(width / 150.0, height / 150.0) * 1.35
        self._draw_broken_biplane(plane, center, scale)

        base_angle = getattr(player, "get_facing_angle_degrees", lambda: 0.0)()
        jitter_mode = (self._frame // self.JITTER_CYCLE_FRAMES) % 3
        angle_jitter = math.sin(self._frame * 0.19) * (7 + 22 * self._strength)
        if jitter_mode == 1:
            angle_jitter *= -1.8
        angle = base_angle + angle_jitter

        rotated = pygame.transform.rotate(plane, -angle)
        rotated.set_alpha(min(255, int(96 + self._strength * 188)))

        cx, cy = _entity_center(player)
        visual_dx = math.sin(self._frame * 0.31) * (6 + 24 * self._strength)
        visual_dy = math.cos(self._frame * 0.27) * (4 + 17 * self._strength)
        if jitter_mode == 2:
            visual_dx *= -1.35
            visual_dy *= 1.5
        visual_center = (int(cx + visual_dx), int(cy + visual_dy))

        if self._strength > 0.28:
            self._render_player_desync_trails(surface, player, visual_center, rotated)

        surface.blit(rotated, rotated.get_rect(center=visual_center))

    def _occlude_original_hostiles(self, surface: pygame.Surface, enemies: Iterable, boss=None) -> None:
        alpha = int(max(0.0, self._strength - 0.32) / 0.68 * 210)
        if alpha <= 0:
            return

        veil = self._get_overlay(*surface.get_size())
        for enemy in enemies:
            _draw_entity_veil(veil, enemy, alpha)
        if boss:
            _draw_entity_veil(veil, boss, min(230, alpha + 20))
        surface.blit(veil, (0, 0))

    def _draw_tracer_round(self, surface: pygame.Surface, bullet, player_owned: bool) -> None:
        rect = getattr(bullet, "rect", None)
        if rect is None:
            return

        cx = int(getattr(rect, "centerx", getattr(rect, "x", 0)))
        cy = int(getattr(rect, "centery", getattr(rect, "y", 0)))
        velocity = getattr(bullet, "velocity", None)
        vx = float(getattr(velocity, "x", 0.0))
        vy = float(getattr(velocity, "y", -1.0 if player_owned else 1.0))
        length = math.hypot(vx, vy)
        if length <= 0.001:
            vx, vy = 0.0, -1.0 if player_owned else 1.0
            length = 1.0
        nx, ny = vx / length, vy / length
        alpha = int(70 + 150 * self._strength)

        if player_owned:
            start = (int(cx - nx * 24), int(cy - ny * 24))
            end = (int(cx + nx * 8), int(cy + ny * 8))
            pygame.draw.line(surface, (226, 184, 94, alpha), start, end, 3)
            pygame.draw.circle(surface, (92, 58, 30, alpha), (cx, cy), 3)
            return

        start = (int(cx - nx * 18), int(cy - ny * 18))
        end = (int(cx + nx * 9), int(cy + ny * 9))
        pygame.draw.line(surface, (82, 232, 120, alpha), start, end, 4)
        pygame.draw.line(surface, (124, 14, 26, max(24, alpha - 50)), start, end, 1)
        pygame.draw.circle(surface, (70, 162, 88, max(30, alpha // 2)), (cx, cy), 8)

    def _occlude_original_projectile(self, surface: pygame.Surface, bullet) -> None:
        alpha = int(max(0.0, self._strength - 0.42) / 0.58 * 185)
        if alpha <= 0:
            return
        rect = getattr(bullet, "rect", None)
        if rect is None:
            return
        veil_rect = pygame.Rect(0, 0, max(18, int(rect.width * 3.4)), max(18, int(rect.height * 3.4)))
        veil_rect.center = (int(rect.centerx), int(rect.centery))
        pygame.draw.ellipse(surface, (8, 8, 7, alpha), veil_rect)

    def _draw_broken_biplane(self, surface: pygame.Surface, center: tuple[int, int], scale: float) -> None:
        cx, cy = center
        wing_span = int(118 * scale)
        wing_h = max(7, int(13 * scale))
        fuselage_w = max(9, int(16 * scale))
        fuselage_h = int(108 * scale)
        wood = (96, 64, 39, 245)
        bone = (194, 180, 144, 230)
        soot = (18, 18, 15, 210)
        blood = (96, 18, 16, 180)

        self._draw_biplane_wings(surface, cx, cy, wing_span, wing_h, scale)
        self._draw_biplane_tail(surface, cx, cy, scale)

        fuselage = [
            (cx, cy - fuselage_h // 2),
            (cx + fuselage_w, cy - int(22 * scale)),
            (cx + int(8 * scale), cy + fuselage_h // 2),
            (cx, cy + int(58 * scale)),
            (cx - int(8 * scale), cy + fuselage_h // 2),
            (cx - fuselage_w, cy - int(22 * scale)),
        ]
        pygame.draw.polygon(surface, wood, fuselage)
        pygame.draw.polygon(surface, (42, 32, 24, 250), fuselage, max(1, int(2 * scale)))

        pygame.draw.circle(surface, (24, 28, 27, 245), (cx, cy - int(18 * scale)), max(5, int(8 * scale)))
        pygame.draw.line(surface, bone, (cx, cy - fuselage_h // 2), (cx, cy + int(54 * scale)), 1)

        nose_y = cy - fuselage_h // 2 - int(4 * scale)
        pygame.draw.circle(surface, (38, 34, 30, 245), (cx, nose_y), max(5, int(8 * scale)))
        pygame.draw.line(
            surface, (170, 152, 120, 210), (cx - int(26 * scale), nose_y), (cx + int(26 * scale), nose_y), 2
        )
        pygame.draw.line(
            surface, (170, 152, 120, 150), (cx, nose_y - int(20 * scale)), (cx, nose_y + int(20 * scale)), 2
        )

        for side in (-1, 1):
            x = cx + side * int(32 * scale)
            pygame.draw.line(
                surface, soot, (x, cy - int(33 * scale)), (x - side * int(13 * scale), cy + int(27 * scale)), 2
            )
            pygame.draw.line(
                surface, soot, (x - side * int(13 * scale), cy - int(28 * scale)), (x, cy + int(33 * scale)), 2
            )

        for index in range(5):
            smoke_alpha = max(18, int(80 - index * 11 + self._strength * 45))
            pygame.draw.circle(
                surface,
                (28, 28, 24, smoke_alpha),
                (cx - int((16 + index * 9) * scale), cy + int((42 + index * 7) * scale)),
                max(5, int((8 + index * 2) * scale)),
            )
        pygame.draw.line(
            surface, blood, (cx + int(14 * scale), cy - int(5 * scale)), (cx + int(34 * scale), cy + int(30 * scale)), 2
        )

    @staticmethod
    def _draw_biplane_wings(
        surface: pygame.Surface, cx: int, cy: int, wing_span: int, wing_h: int, scale: float
    ) -> None:
        canvas = (118, 102, 72, 235)
        canvas_dark = (72, 62, 45, 240)
        bone = (194, 180, 144, 230)
        soot = (18, 18, 15, 210)
        for offset in (-28, 26):
            rect = pygame.Rect(0, 0, wing_span, wing_h)
            rect.center = (cx, cy + int(offset * scale))
            pygame.draw.rect(surface, canvas, rect, border_radius=2)
            pygame.draw.rect(surface, canvas_dark, rect, max(1, int(2 * scale)), border_radius=2)
            for rib in range(-4, 5):
                x = cx + int(rib * wing_span / 10)
                pygame.draw.line(surface, bone, (x, rect.top), (x, rect.bottom), 1)
        broken = [
            (cx + wing_span // 2 - int(20 * scale), cy - int(34 * scale)),
            (cx + wing_span // 2 + int(18 * scale), cy - int(43 * scale)),
            (cx + wing_span // 2 + int(4 * scale), cy - int(25 * scale)),
        ]
        pygame.draw.polygon(surface, soot, broken)

    @staticmethod
    def _draw_biplane_tail(
        surface: pygame.Surface, cx: int, cy: int, scale: float
    ) -> None:
        canvas_dark = (72, 62, 45, 240)
        tail_y = cy + int(56 * scale)
        pygame.draw.polygon(
            surface, canvas_dark,
            [(cx, tail_y - int(6 * scale)),
             (cx - int(34 * scale), tail_y + int(16 * scale)),
             (cx - int(8 * scale), tail_y + int(18 * scale))],
        )
        pygame.draw.polygon(
            surface, canvas_dark,
            [(cx, tail_y - int(6 * scale)),
             (cx + int(34 * scale), tail_y + int(16 * scale)),
             (cx + int(8 * scale), tail_y + int(18 * scale))],
        )

    def _render_player_desync_trails(
        self, surface: pygame.Surface, player, visual_center: tuple[int, int], sprite: pygame.Surface
    ) -> None:
        actual = tuple(map(int, _entity_center(player)))
        trail = self._get_overlay(*surface.get_size())
        line_alpha = int(35 + 76 * self._strength)
        pygame.draw.line(trail, (216, 30, 34, line_alpha), actual, visual_center, max(1, int(1 + 3 * self._strength)))
        for index, offset in enumerate(((-24, 9), (18, -14), (36, 18))):
            ghost = sprite.copy()
            ghost.set_alpha(int((32 + index * 16) * self._strength))
            center = (actual[0] + int(offset[0] * self._strength), actual[1] + int(offset[1] * self._strength))
            trail.blit(ghost, ghost.get_rect(center=center))
        surface.blit(trail, (0, 0))

    def _render_spirit_enemy(self, surface: pygame.Surface, enemy, player_center: tuple[float, float] | None) -> None:
        cx, cy = _entity_center(enemy)
        cx, cy = self._hallucinated_enemy_center(cx, cy, enemy, player_center)
        width = max(36, int(getattr(enemy.rect, "width", 50) * 1.7))
        height = max(36, int(getattr(enemy.rect, "height", 50) * 1.7))
        alpha = int(82 + self._strength * 158)
        self._draw_spirit_ship(surface, cx, cy, width, height, alpha, elite=getattr(enemy, "_is_elite", False))

    def _render_spirit_enemy_at(
        self, surface: pygame.Surface, enemy, hx: float, hy: float
    ) -> None:
        width = max(36, int(getattr(enemy.rect, "width", 50) * 1.7))
        height = max(36, int(getattr(enemy.rect, "height", 50) * 1.7))
        alpha = int(82 + self._strength * 158)
        self._draw_spirit_ship(surface, hx, hy, width, height, alpha, elite=getattr(enemy, "_is_elite", False))

    def _render_spirit_boss(self, surface: pygame.Surface, boss, player_center: tuple[float, float] | None) -> None:
        cx, cy = _entity_center(boss)
        cx, cy = self._hallucinated_enemy_center(cx, cy, boss, player_center, lunge_scale=0.55)
        width = max(92, int(getattr(boss.rect, "width", 160) * 1.15))
        height = max(72, int(getattr(boss.rect, "height", 130) * 1.05))
        self._draw_spirit_ship(surface, cx, cy, width, height, int(108 + self._strength * 132), elite=True, boss=True)

    def _hallucinated_enemy_center(
        self,
        cx: float,
        cy: float,
        enemy,
        player_center: tuple[float, float] | None,
        lunge_scale: float = 1.0,
    ) -> tuple[float, float]:
        pulse = max(0.0, math.sin(self._frame * 0.13 + (id(enemy) % 31)))
        jitter_x = math.sin(self._frame * 0.21 + id(enemy) % 17) * 8 * self._strength
        jitter_y = math.cos(self._frame * 0.18 + id(enemy) % 23) * 6 * self._strength
        if player_center is None:
            return cx + jitter_x, cy + jitter_y

        dx = player_center[0] - cx
        dy = player_center[1] - cy
        length = math.hypot(dx, dy)
        if length <= 0.001:
            return cx + jitter_x, cy + jitter_y
        lunge = pulse * (12 + 36 * self._strength) * lunge_scale
        return cx + dx / length * lunge + jitter_x, cy + dy / length * lunge + jitter_y

    def _draw_spirit_ship(
        self,
        surface: pygame.Surface,
        cx: float,
        cy: float,
        width: int,
        height: int,
        alpha: int,
        elite: bool = False,
        boss: bool = False,
    ) -> None:
        pad = max(width, height)
        spirit = pygame.Surface((width + pad, height + pad), pygame.SRCALPHA)
        sx = spirit.get_width() // 2
        sy = spirit.get_height() // 2
        w = width
        h = height
        bone = (214, 210, 180, alpha)
        old_bone = (128, 120, 96, max(38, alpha - 54))
        toxic = (70, 170, 88, int(alpha * 0.38))
        blood = (130, 12, 20, int(alpha * 0.62))
        shadow = (10, 13, 10, int(alpha * 0.68))
        eye = (230, 28, 34, min(255, alpha + 25))

        mist_count = 8 + int(8 * self._strength) + (7 if boss else 0)
        for index in range(mist_count):
            phase = self._frame * 0.035 + index * 1.7
            mx = sx + math.sin(phase) * w * (0.18 + index % 3 * 0.05)
            my = sy + math.cos(phase * 0.8) * h * 0.22
            radius = int((w * 0.16 + index * 2) * (1.25 if boss else 1.0))
            pygame.draw.circle(spirit, toxic, (int(mx), int(my)), max(5, radius))

        self._draw_spirit_hull(spirit, sx, sy, w, h, bone, shadow)
        self._draw_spirit_wings(spirit, sx, sy, w, h, bone, old_bone)

        skull_radius = max(5, int(w * (0.08 if not boss else 0.055)))
        skull_y = sy - int(h * 0.11)
        pygame.draw.circle(spirit, bone, (sx, skull_y), skull_radius)
        pygame.draw.circle(spirit, (20, 8, 10, alpha), (sx - skull_radius // 3, skull_y - 1), max(1, skull_radius // 4))
        pygame.draw.circle(spirit, (20, 8, 10, alpha), (sx + skull_radius // 3, skull_y - 1), max(1, skull_radius // 4))
        pygame.draw.circle(spirit, eye, (sx - skull_radius // 3, skull_y - 1), max(1, skull_radius // 7))
        pygame.draw.circle(spirit, eye, (sx + skull_radius // 3, skull_y - 1), max(1, skull_radius // 7))

        for index in range(3 + int(self._strength * 4)):
            bx = sx + int((index - 2) * w * 0.07)
            pygame.draw.line(spirit, blood, (bx, sy + int(h * 0.04)), (bx + (index % 2) * 7 - 3, sy + int(h * 0.26)), 2)

        if elite:
            ring = pygame.Rect(0, 0, int(w * 0.74), int(h * 0.56))
            ring.center = (sx, sy)
            pygame.draw.ellipse(spirit, (116, 16, 22, int(alpha * 0.55)), ring, max(2, int(w * 0.025)))

        if boss:
            pygame.draw.line(spirit, (24, 230, 120, int(alpha * 0.55)), (sx - w * 0.42, sy), (sx + w * 0.42, sy), 2)

        spirit = pygame.transform.rotate(spirit, math.sin(self._frame * 0.035 + sx) * 5 * self._strength)
        surface.blit(spirit, spirit.get_rect(center=(int(cx), int(cy))))

    @staticmethod
    def _draw_spirit_hull(
        spirit: pygame.Surface,
        sx: int, sy: int, w: int, h: int,
        bone: tuple[int, int, int, int],
        shadow: tuple[int, int, int, int],
    ) -> None:
        hull = [
            (sx, sy - h * 0.47),
            (sx + w * 0.18, sy - h * 0.15),
            (sx + w * 0.50, sy - h * 0.02),
            (sx + w * 0.24, sy + h * 0.16),
            (sx + w * 0.13, sy + h * 0.44),
            (sx, sy + h * 0.33),
            (sx - w * 0.13, sy + h * 0.44),
            (sx - w * 0.24, sy + h * 0.16),
            (sx - w * 0.50, sy - h * 0.02),
            (sx - w * 0.18, sy - h * 0.15),
        ]
        pygame.draw.polygon(spirit, shadow, hull)
        pygame.draw.lines(spirit, bone, True, hull, max(2, int(w * 0.035)))

    @staticmethod
    def _draw_spirit_wings(
        spirit: pygame.Surface,
        sx: int, sy: int, w: int, h: int,
        bone: tuple[int, int, int, int],
        old_bone: tuple[int, int, int, int],
    ) -> None:
        for side in (-1, 1):
            wing = [
                (sx + side * w * 0.12, sy - h * 0.08),
                (sx + side * w * 0.55, sy - h * 0.26),
                (sx + side * w * 0.70, sy - h * 0.08),
                (sx + side * w * 0.26, sy + h * 0.10),
            ]
            pygame.draw.lines(spirit, bone, False, wing, max(2, int(w * 0.03)))
            pygame.draw.line(spirit, old_bone, wing[0], wing[-1], 1)
            for rib in range(1, 5):
                t = rib / 5
                x1 = sx + side * w * (0.12 + 0.42 * t)
                y1 = sy - h * (0.08 + 0.18 * t)
                x2 = sx + side * w * (0.16 + 0.12 * t)
                y2 = sy + h * (0.02 + 0.08 * t)
                pygame.draw.line(spirit, old_bone, (x1, y1), (x2, y2), 1)

    def _maybe_spawn_memory_fragment(self, size: tuple[int, int]) -> None:
        if len(self._memory_fragments) >= self.MAX_MEMORY_FRAGMENTS:
            return

        pressure_bonus = min(0.020, self._enemy_pressure * 0.0025)
        chance = 0.004 + self._strength * 0.030 + pressure_bonus
        if self._rng.random() > chance:
            return

        width, height = size
        kind = self._rng.choice(("skull", "departure", "black_hole"))
        scale = self._rng.uniform(0.72, 1.65) * (0.75 + self._strength * 0.55)
        fragment = self.MemoryFragment(
            kind=kind,
            x=self._rng.uniform(width * 0.06, width * 0.94),
            y=self._rng.uniform(height * 0.08, height * 0.84),
            scale=scale,
            alpha=self._rng.randint(40, 118 + int(self._strength * 80)),
            age=0,
            duration=self._rng.randint(110, 260 + int(self._strength * 190)),
            drift_x=self._rng.uniform(-0.22, 0.22),
            drift_y=self._rng.uniform(-0.18, 0.28),
        )
        self._memory_fragments.append(fragment)

    def _render_memory_fragments(self, surface: pygame.Surface) -> None:
        if not self._memory_fragments:
            return

        overlay = self._get_overlay(*surface.get_size())
        for fragment in self._memory_fragments:
            life = fragment.age / max(1, fragment.duration)
            envelope = math.sin(min(1.0, life) * math.pi)
            alpha = int(fragment.alpha * envelope * (0.55 + self._strength * 0.72))
            if alpha <= 2:
                continue
            if fragment.kind == "skull":
                self._draw_skull(overlay, fragment, alpha)
            elif fragment.kind == "departure":
                self._draw_departure_scene(overlay, fragment, alpha)
            else:
                self._draw_black_hole(overlay, fragment, alpha)
        surface.blit(overlay, (0, 0))

    def _draw_skull(self, overlay: pygame.Surface, fragment: MemoryFragment, alpha: int) -> None:
        x, y = int(fragment.x), int(fragment.y)
        r = max(16, int(36 * fragment.scale))
        bone_color = (212, 208, 190, alpha)
        shadow_color = (28, 24, 20, max(20, alpha // 2))
        eye_color = (10, 6, 8, alpha)

        pygame.draw.ellipse(overlay, shadow_color, pygame.Rect(x - r, y - r, r * 2, r * 2))
        pygame.draw.ellipse(overlay, bone_color, pygame.Rect(x - r, y - r, r * 2, r * 2), 2)
        # Jaw
        jaw_h = max(6, int(r * 0.55))
        pygame.draw.ellipse(overlay, bone_color, pygame.Rect(x - r * 3 // 4, y + r // 3, r * 3 // 2, jaw_h), 2)
        # Eye sockets
        eye_r = max(3, r // 4)
        eye_y = y - r // 4
        for side in (-1, 1):
            ex = x + side * r // 3
            pygame.draw.circle(overlay, shadow_color, (ex, eye_y), eye_r + 1)
            pygame.draw.circle(overlay, eye_color, (ex, eye_y), eye_r)
        # Nose
        nose_y = y + r // 6
        pygame.draw.polygon(
            overlay, shadow_color,
            [(x - 3, nose_y - 3), (x + 3, nose_y - 3), (x, nose_y + 4)],
        )
        # Crack lines
        crack_alpha = max(16, alpha // 3)
        pygame.draw.line(overlay, (64, 56, 48, crack_alpha), (x + r // 3, y - r // 2), (x + r // 4, y + r // 5), 1)
        pygame.draw.line(overlay, (64, 56, 48, crack_alpha), (x - r // 4, y - r // 5), (x - r // 2, y), 1)

    def _draw_departure_scene(self, overlay: pygame.Surface, fragment: MemoryFragment, alpha: int) -> None:
        x, y = int(fragment.x), int(fragment.y)
        scale = fragment.scale
        line = (210, 205, 184, alpha)
        dark = (20, 18, 18, max(24, alpha))
        distance = int(82 * scale)
        pygame.draw.line(overlay, line, (x - distance, y + int(38 * scale)), (x + distance, y + int(38 * scale)), 1)
        self._draw_silhouette(overlay, x - distance // 2, y, scale, dark)
        self._draw_silhouette(overlay, x + distance // 2, y - int(8 * scale), scale * 0.9, dark)
        pygame.draw.line(
            overlay, line, (x - int(12 * scale), y - int(12 * scale)), (x + int(18 * scale), y - int(26 * scale)), 1
        )
        pygame.draw.rect(
            overlay,
            (98, 72, 52, alpha // 2),
            pygame.Rect(x + distance // 2 + int(16 * scale), y - int(36 * scale), int(22 * scale), int(74 * scale)),
            1,
        )

    def _draw_black_hole(self, overlay: pygame.Surface, fragment: MemoryFragment, alpha: int) -> None:
        x, y = int(fragment.x), int(fragment.y)
        r = max(14, int(38 * fragment.scale))
        core_alpha = max(180, alpha)
        ring_alpha = int(alpha * 0.45)
        glow_alpha = int(alpha * 0.18)

        # Outer glow
        for i in range(3):
            glow_r = r + 6 + i * 5
            glow_a = max(4, glow_alpha - i * 8)
            pygame.draw.circle(overlay, (64, 28, 80, glow_a), (x, y), glow_r)
        # Event horizon ring
        pygame.draw.circle(overlay, (0, 0, 0, core_alpha), (x, y), r)
        # Accretion disk ellipse
        disk_w = int(r * 2.0)
        disk_h = max(6, int(r * 0.28))
        angle = self._frame * 0.04 + x * 0.003
        rx = int(math.cos(angle) * r * 0.55)
        ry = int(math.sin(angle) * r * 0.55) if abs(math.sin(angle)) > 0.01 else 0
        disk_rect = pygame.Rect(x - disk_w // 2, y - disk_h // 2, disk_w, disk_h)
        pygame.draw.ellipse(overlay, (120, 40, 140, ring_alpha), disk_rect, max(1, int(r * 0.06)))
        # Accretion bright spot
        spot_x = x + rx
        spot_y = y + ry
        pygame.draw.circle(overlay, (200, 100, 220, int(ring_alpha * 1.3)), (spot_x, spot_y), max(2, int(r * 0.15)))

    @staticmethod
    def _draw_silhouette(
        overlay: pygame.Surface, x: int, y: int, scale: float, color: tuple[int, int, int, int]
    ) -> None:
        head_r = max(4, int(8 * scale))
        pygame.draw.circle(overlay, color, (x, y - int(22 * scale)), head_r)
        body = pygame.Rect(0, 0, max(8, int(16 * scale)), max(20, int(36 * scale)))
        body.center = (x, y)
        pygame.draw.ellipse(overlay, color, body)

    def _render_ui_corruption(self, surface: pygame.Surface, state=None, player=None) -> None:
        if self._strength < 0.10:
            return

        width, height = surface.get_size()
        overlay = self._get_overlay(width, height)
        font = get_cjk_font(18)
        small = get_cjk_font(14)
        rows = [
            (34, 56, "SCORE", getattr(state, "score", 0)),
            (34, 82, "HP", getattr(player, "health", 0)),
            (34, 108, "KILLS", getattr(state, "kill_count", 0)),
            (width - 220, 56, "FUEL", getattr(player, "boost_current", 0)),
        ]
        color = (232, 48, 54)
        green = (72, 214, 116)
        for index, (x, y, label, value) in enumerate(rows):
            jitter_x = int(math.sin(self._frame * 0.22 + index) * 10 * self._strength)
            display = f"{label} {self._garbled_number(value, index)}"
            text = font.render(display, True, color if index % 2 == 0 else green)
            text.set_alpha(int(68 + 154 * self._strength))
            overlay.blit(text, (x + jitter_x, y))

        stream_count = int(5 + self._strength * 18)
        for index in range(stream_count):
            base = (self._frame // 4) * 181 + index * 41
            x = self._lcg_randint(base, 0, max(1, width - 90))
            y = self._lcg_randint(base + 1, 0, max(1, height - 20))
            text_len = self._lcg_randint(base + 2, 5, 13)
            text = small.render(self._garbled_string(text_len, base + 3), True, (204, 210, 188))
            text.set_alpha(int(self._lcg_randint(base + 4, 20, 82) * self._strength))
            overlay.blit(text, (x, y))
        surface.blit(overlay, (0, 0))

    def _garbled_number(self, value, salt: int) -> str:
        text_len = max(4, len(str(int(value))) + 2 if isinstance(value, (int, float)) else 5)
        return self._garbled_string(text_len, (self._frame // 5 + 1) * 997 + salt * 53)

    @staticmethod
    def _garbled_string(length: int, seed: int) -> str:
        chars = "01#%?E-7/\\"
        result = []
        for i in range(length):
            s = ((seed + i) * 1103515245 + 12345) & 0x7FFFFFFF
            result.append(chars[s % len(chars)])
        return "".join(result)

    @staticmethod
    def _lcg_randint(seed: int, lo: int, hi: int) -> int:
        return lo + (((seed * 1103515245 + 12345) & 0x7FFFFFFF) % (hi - lo + 1))

    def _render_vignette(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        overlay = self._get_overlay(width, height)
        tint_alpha = int(30 + self._strength * 88)
        overlay.fill((52, 38, 24, tint_alpha))

        vignette_alpha = int(64 + self._strength * 118)
        border = max(24, int(min(width, height) * 0.10))
        pygame.draw.rect(overlay, (0, 0, 0, vignette_alpha), pygame.Rect(0, 0, width, border))
        pygame.draw.rect(overlay, (0, 0, 0, vignette_alpha), pygame.Rect(0, height - border, width, border))
        pygame.draw.rect(overlay, (0, 0, 0, vignette_alpha), pygame.Rect(0, 0, border, height))
        pygame.draw.rect(overlay, (0, 0, 0, vignette_alpha), pygame.Rect(width - border, 0, border, height))
        surface.blit(overlay, (0, 0))

    def _apply_screen_distortion(self, surface: pygame.Surface) -> None:
        strength = self._strength
        if strength <= 0.03:
            return

        width, height = surface.get_size()
        if self._distort_buf is None or self._distort_buf.get_size() != (width, height):
            self._distort_buf = pygame.Surface((width, height), pygame.SRCALPHA)
        else:
            self._distort_buf.fill((0, 0, 0, 0))
        self._distort_buf.blit(surface, (0, 0))

        band_height = max(4, int(18 - 10 * strength))
        max_shift = int(2 + 24 * strength)
        for y in range(0, height, band_height):
            phase = self._frame * 0.09 + y * 0.035
            saw = ((self._frame + y * 3) % 29) / 29.0 - 0.5
            shift = int(math.sin(phase) * max_shift + saw * max_shift * 0.55)
            rect = pygame.Rect(0, y, width, min(band_height, height - y))
            surface.blit(self._distort_buf, (shift, y), rect)

        if strength > 0.18:
            offset = max(1, int(3 + 9 * strength))
            self._distort_buf.set_alpha(int(20 + 38 * strength))
            surface.blit(self._distort_buf, (-offset, 0))
            surface.blit(self._distort_buf, (offset, 0))
            self._distort_buf.set_alpha(255)

    def _get_overlay(self, width: int, height: int) -> pygame.Surface:
        if self._overlay is None or self._overlay.get_size() != (width, height):
            self._overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        else:
            self._overlay.fill((0, 0, 0, 0))
        return self._overlay
