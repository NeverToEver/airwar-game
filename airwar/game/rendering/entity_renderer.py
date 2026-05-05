"""Rendering helpers for gameplay entities."""

import math
from collections import deque
from typing import TYPE_CHECKING

import pygame

from airwar.config.design_tokens import Colors
from airwar.entities.base import Vector2
from airwar.utils.fonts import get_cjk_font
from airwar.utils.sprites import (
    draw_boss_ship,
    draw_bullet,
    draw_elite_enemy_ship,
    draw_enemy_ship,
    draw_explosive_missile,
    draw_glow_circle,
    get_boss_sprite,
)

if TYPE_CHECKING:
    from airwar.entities.bullet import Bullet
    from airwar.entities.enemy import Boss, Enemy


class EntityRenderer:
    """Draw gameplay entities without coupling entity classes to sprite/UI modules."""

    TRAIL_CACHE_MAX_SIZE = 256
    ENTRY_FONT_SIZE = 36
    ESCAPE_FONT_SIZE = 28

    _trail_surface_cache: dict = {}
    _trail_cache_order: deque = deque()
    _warning_font = None
    _escape_font = None

    @classmethod
    def _get_warning_font(cls):
        if cls._warning_font is None:
            cls._warning_font = get_cjk_font(cls.ENTRY_FONT_SIZE)
        return cls._warning_font

    @classmethod
    def _get_escape_font(cls):
        if cls._escape_font is None:
            cls._escape_font = get_cjk_font(cls.ESCAPE_FONT_SIZE)
        return cls._escape_font

    def render_enemy(self, surface: pygame.Surface, enemy: "Enemy") -> None:
        if getattr(enemy, "_sprite", None):
            surface.blit(enemy._sprite, enemy.get_rect())
            return

        health_ratio = enemy.health / enemy.max_health if enemy.max_health > 0 else 1.0
        if getattr(enemy, "_is_elite", False):
            visual_scale = getattr(enemy, "VISUAL_SCALE", 1.3)
            draw_elite_enemy_ship(
                surface,
                enemy.rect.centerx,
                enemy.rect.centery,
                enemy.rect.width * visual_scale,
                enemy.rect.height * visual_scale,
                health_ratio,
            )
            return

        draw_enemy_ship(
            surface,
            enemy.rect.centerx,
            enemy.rect.centery,
            enemy.rect.width,
            enemy.rect.height,
            health_ratio,
        )

    def render_bullet(self, surface: pygame.Surface, bullet: "Bullet") -> None:
        if getattr(bullet, "_sprite", None):
            surface.blit(bullet._sprite, bullet.get_rect())
        elif bullet.data.is_explosive:
            draw_explosive_missile(surface, bullet.rect.x, bullet.rect.y, bullet.rect.width, bullet.rect.height)
        else:
            draw_bullet(
                surface,
                bullet.rect.x,
                bullet.rect.y,
                bullet.rect.width,
                bullet.rect.height,
                bullet.data.bullet_type,
                bullet.data.owner,
            )

        if (bullet.data.bullet_type == "laser" or bullet.data.is_laser) and bullet._trail:
            self._render_bullet_trail(surface, bullet)

    def _render_bullet_trail(self, surface: pygame.Surface, bullet: "Bullet") -> None:
        trail_color = (30, 255, 100) if bullet.data.owner == "player" else (255, 30, 30)
        trail_len = len(bullet._trail)
        for i, (tx, ty, tw, th) in enumerate(bullet._trail):
            alpha = int(120 * (i / trail_len))
            cache_key = (tw, th, alpha, bullet.data.owner)
            trail_surface = self._get_trail_surface(cache_key, tw, th, trail_color, alpha)
            surface.blit(trail_surface, (tx, ty))

    @classmethod
    def _get_trail_surface(cls, cache_key, width: int, height: int, color: tuple[int, int, int], alpha: int):
        if cache_key in cls._trail_surface_cache:
            return cls._trail_surface_cache[cache_key]
        if len(cls._trail_surface_cache) >= cls.TRAIL_CACHE_MAX_SIZE:
            oldest = cls._trail_cache_order.popleft()
            cls._trail_surface_cache.pop(oldest, None)
        trail_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        trail_surface.fill(color + (alpha,))
        cls._trail_surface_cache[cache_key] = trail_surface
        cls._trail_cache_order.append(cache_key)
        return trail_surface

    def render_boss(self, surface: pygame.Surface, boss: "Boss") -> None:
        health_ratio = boss.health / boss.max_health if boss.max_health > 0 else 1.0
        self._render_enrage_trail(surface, boss)
        self._render_boss_body(surface, boss, health_ratio)
        self._render_muzzle_flash(surface, boss)

        if boss.entering:
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.002)
            warning_surf = self._get_warning_font().render("! 警告 !", True, Colors.ACCENT_DANGER)
            warning_surf.set_alpha(int(150 + 35 * pulse))
            surface.blit(warning_surf, warning_surf.get_rect(center=(surface.get_width() // 2, 20)))

        if boss._enrage_timer > 0:
            intensity = boss.enrage_visual_intensity()
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.0022)
            warning_surf = self._get_escape_font().render("核心过载", True, (178, 226, 255))
            warning_surf.set_alpha(int((105 + 42 * pulse) * max(0.42, intensity)))
            surface.blit(warning_surf, warning_surf.get_rect(center=(surface.get_width() // 2, 86)))
            self._render_enrage_transition_charge(surface, boss, intensity)

        if boss._show_escape_warning and not boss.entering:
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.002)
            warning_surf = self._get_escape_font().render("逃跑中...", True, (255, 200, 50))
            warning_surf.set_alpha(int(145 + 36 * pulse))
            surface.blit(warning_surf, warning_surf.get_rect(center=(surface.get_width() // 2, 50)))

    def _render_boss_body(self, surface: pygame.Surface, boss: "Boss", health_ratio: float) -> None:
        if boss.enrage_visual_intensity() <= 0:
            draw_boss_ship(surface, boss.rect.centerx, boss.rect.centery, boss.rect.width, boss.rect.height, health_ratio)
            return

        self._render_enrage_body_aura(surface, boss)
        sprite = get_boss_sprite(boss.rect.width, boss.rect.height, health_ratio)
        rotation = 90.0 - boss._facing_angle
        rotated = pygame.transform.rotozoom(sprite, rotation, 1.0)
        surface.blit(rotated, rotated.get_rect(center=(round(boss.rect.centerx), round(boss.rect.centery))))
        self._render_enrage_core_lines(surface, boss)

    def _render_enrage_body_aura(self, surface: pygame.Surface, boss: "Boss") -> None:
        intensity = max(0.15, boss.enrage_visual_intensity())
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.005)
        core_color = boss.ENRAGE_CORE_COLOR
        danger_color = boss.ENRAGE_DANGER_COLOR
        core_radius = max(10, int(min(boss.rect.width, boss.rect.height) * (0.19 + 0.05 * pulse)))
        draw_glow_circle(
            surface,
            (int(boss.rect.centerx), int(boss.rect.centery)),
            core_radius,
            core_color,
            int(core_radius * (3.3 + intensity)),
        )
        pygame.draw.circle(
            surface,
            (245, 248, 255),
            (int(boss.rect.centerx), int(boss.rect.centery)),
            max(2, core_radius // 5),
        )
        ring_size = (
            max(1, int(boss.rect.width * (1.26 + 0.05 * pulse))),
            max(1, int(boss.rect.height * (1.18 + 0.05 * pulse))),
        )
        ring = pygame.Surface(ring_size, pygame.SRCALPHA)
        ring_rect = ring.get_rect()
        pygame.draw.ellipse(ring, (*core_color, int(64 * intensity)), ring_rect, max(2, int(4 + 2 * pulse)))
        inner = ring_rect.inflate(-max(4, ring_size[0] // 7), -max(4, ring_size[1] // 7))
        pygame.draw.ellipse(ring, (*danger_color, int(42 * intensity)), inner, 2)
        rotated_ring = pygame.transform.rotozoom(ring, 90.0 - boss._facing_angle, 1.0)
        surface.blit(rotated_ring, rotated_ring.get_rect(center=(round(boss.rect.centerx), round(boss.rect.centery))))

        if boss._enrage_snapshot_target:
            target_x, target_y = boss._enrage_snapshot_target
            pygame.draw.line(
                surface,
                (48, 92, 122),
                (int(boss.rect.centerx), int(boss.rect.centery)),
                (int(target_x), int(target_y)),
                max(1, int(1 + 2 * intensity)),
            )

    def _render_enrage_core_lines(self, surface: pygame.Surface, boss: "Boss") -> None:
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.007)
        forward = boss._facing_vector().normalize()
        if forward.length() <= 0:
            forward = Vector2(0, 1)
        side_axis = Vector2(-forward.y, forward.x)
        center = Vector2(boss.rect.centerx, boss.rect.centery)
        core_color = boss.ENRAGE_CORE_COLOR
        danger_color = boss.ENRAGE_DANGER_COLOR
        for side in (-1, 1):
            flank = center + side_axis * (boss.rect.width * 0.34 * side)
            nose = flank + forward * (boss.rect.height * 0.35)
            tail = flank + forward * (-boss.rect.height * 0.30)
            pygame.draw.line(
                surface,
                (
                    min(255, int(danger_color[0] * (0.55 + 0.25 * pulse))),
                    min(255, int(danger_color[1] * (0.80 + 0.20 * pulse))),
                    min(255, int(danger_color[2] * (0.85 + 0.15 * pulse))),
                ),
                (int(tail.x), int(tail.y)),
                (int(nose.x), int(nose.y)),
                max(2, int(boss.rect.width * 0.018)),
            )
            pygame.draw.circle(
                surface,
                core_color,
                (int(nose.x), int(nose.y)),
                max(3, int(boss.rect.width * 0.025)),
            )

    def _render_muzzle_flash(self, surface: pygame.Surface, boss: "Boss") -> None:
        if boss._muzzle_flash_timer <= 0 or not boss._muzzle_flash_positions:
            return
        remaining = boss._muzzle_flash_timer / max(1, boss.ENRAGE_MUZZLE_FLASH_DURATION)
        elapsed = 1.0 - remaining
        pulse = 0.5 + 0.5 * math.sin(elapsed * math.tau * boss.ENRAGE_MUZZLE_FLASH_PULSES)
        strobe = (0.38 + 0.16 * pulse) * remaining
        radius = max(2, int(boss.rect.width * 0.03 + 8 * strobe))
        glow_radius = max(radius + 5, int(radius * (1.75 + 0.35 * pulse)))
        forward = boss._facing_vector().normalize()
        for muzzle_x, muzzle_y in boss._muzzle_flash_positions:
            center = (int(muzzle_x), int(muzzle_y))
            draw_glow_circle(surface, center, radius, boss.ENRAGE_CORE_COLOR, glow_radius)
            pygame.draw.line(
                surface,
                (232, 246, 255),
                center,
                (
                    int(muzzle_x + forward.x * radius * (1.7 + 0.45 * pulse)),
                    int(muzzle_y + forward.y * radius * (1.7 + 0.45 * pulse)),
                ),
                max(2, radius // 2),
            )

    def _render_enrage_trail(self, surface: pygame.Surface, boss: "Boss") -> None:
        if not boss._enrage_trail:
            return
        trail = self._sample_enrage_trail_for_render(boss)
        trail_len = len(trail)
        health_ratio = boss.health / boss.max_health if boss.max_health > 0 else 1.0
        ghost = self._get_enrage_trail_ghost(boss, health_ratio)
        render_ghost = pygame.transform.smoothscale(ghost, self._enrage_trail_render_size(boss))
        for index, center in enumerate(trail):
            alpha = int(24 + 96 * (index + 1) / trail_len)
            render_ghost.set_alpha(alpha)
            surface.blit(render_ghost, render_ghost.get_rect(center=center))
        render_ghost.set_alpha(255)

    @staticmethod
    def _sample_enrage_trail_for_render(boss: "Boss"):
        trail_len = len(boss._enrage_trail)
        if trail_len <= boss.ENRAGE_TRAIL_RENDER_MAX:
            return boss._enrage_trail
        step = (trail_len - 1) / (boss.ENRAGE_TRAIL_RENDER_MAX - 1)
        return [boss._enrage_trail[round(index * step)] for index in range(boss.ENRAGE_TRAIL_RENDER_MAX)]

    def _get_enrage_trail_ghost(self, boss: "Boss", health_ratio: float) -> pygame.Surface:
        health_bucket = int(health_ratio * 10)
        final_width, final_height = self._enrage_trail_render_size(boss)
        scaled_width = max(1, int(final_width * boss.ENRAGE_TRAIL_SCALE))
        scaled_height = max(1, int(final_height * boss.ENRAGE_TRAIL_SCALE))
        cache_key = (scaled_width, scaled_height, health_bucket, boss.ENRAGE_TRAIL_BLUR_PASSES)
        if boss._enrage_trail_ghost_key != cache_key:
            source = pygame.Surface((final_width, final_height), pygame.SRCALPHA)
            draw_boss_ship(
                source,
                final_width / 2,
                final_height / 2,
                boss.rect.width,
                boss.rect.height,
                health_ratio,
            )
            source.fill((*boss.ENRAGE_TRAIL_TINT, 255), special_flags=pygame.BLEND_RGBA_MULT)
            ghost = pygame.transform.smoothscale(source, (scaled_width, scaled_height))
            boss._enrage_trail_ghost = self._blur_enrage_trail_ghost(ghost, boss.ENRAGE_TRAIL_BLUR_PASSES)
            boss._enrage_trail_ghost_key = cache_key
        return boss._enrage_trail_ghost

    @staticmethod
    def _enrage_trail_render_size(boss: "Boss") -> tuple[int, int]:
        return (
            max(1, int(boss.rect.width * boss.ENRAGE_TRAIL_FINAL_SCALE)),
            max(1, int(boss.rect.height * boss.ENRAGE_TRAIL_FINAL_SCALE)),
        )

    @staticmethod
    def _blur_enrage_trail_ghost(ghost: pygame.Surface, blur_passes: int) -> pygame.Surface:
        blurred = ghost
        for _ in range(blur_passes):
            down_size = (max(1, blurred.get_width() // 2), max(1, blurred.get_height() // 2))
            blurred = pygame.transform.smoothscale(blurred, down_size)
            blurred = pygame.transform.smoothscale(blurred, ghost.get_size())
        return blurred

    def _render_enrage_transition_charge(
        self,
        surface: pygame.Surface,
        boss: "Boss",
        intensity: float,
    ) -> None:
        if boss._enrage_transition_timer <= 0:
            return
        transition = 1.0 - boss._enrage_transition_timer / max(1, boss.ENRAGE_TRANSITION_DURATION)
        charge = transition * transition * (3 - 2 * transition)
        pulse = 0.5 + 0.5 * math.sin(transition * math.tau * 2.0)
        alpha = int(74 * (1.0 - charge) + 38 * intensity + 16 * pulse * (1.0 - transition))
        if alpha <= 0:
            return
        glow_size = (
            max(1, int(boss.rect.width * (2.05 - 0.55 * charge))),
            max(1, int(boss.rect.height * (1.85 - 0.42 * charge))),
        )
        glow = pygame.Surface(glow_size, pygame.SRCALPHA)
        pygame.draw.ellipse(
            glow,
            (*boss.ENRAGE_CORE_COLOR, alpha),
            glow.get_rect(),
            max(2, int(8 * (1.0 - charge) + 2)),
        )
        inner_rect = glow.get_rect().inflate(-max(4, glow_size[0] // 5), -max(4, glow_size[1] // 5))
        pygame.draw.ellipse(glow, (*boss.ENRAGE_DANGER_COLOR, max(14, alpha // 4)), inner_rect, 2)
        pygame.draw.line(
            glow,
            (*boss.ENRAGE_CORE_COLOR, max(18, alpha // 3)),
            (glow_size[0] // 2, 0),
            (glow_size[0] // 2, glow_size[1]),
            2,
        )
        pygame.draw.line(
            glow,
            (*boss.ENRAGE_DANGER_COLOR, max(16, alpha // 4)),
            (0, glow_size[1] // 2),
            (glow_size[0], glow_size[1] // 2),
            2,
        )
        surface.blit(glow, glow.get_rect(center=boss.rect.center))
