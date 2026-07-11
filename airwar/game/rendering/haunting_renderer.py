"""CRT glitch flashback — brief ~3s TV-interference effect triggered during combat."""

from __future__ import annotations

import math
import random
from collections.abc import Iterable
from typing import Any

import pygame


class HauntingRenderer:
    """Trigger-driven CRT glitch flashback — instant on/off, ~3s TV interference.

    Static filter (tint + scanlines + vignette) is pre-rendered once and
    blitted every frame. Only the noise offset changes per frame.
    distort_world uses a small reusable band buffer.
    Total per-frame cost during flashback: 2-3 blits, no draws, no fills.
    """

    FLASHBACK_DURATION = 180
    FLASHBACK_COOLDOWN = 10 * 60
    FLICKER_DURATION = 18

    TINT_COLOR = (28, 18, 48, 32)
    SCANLINE_COLOR = (0, 0, 0, 80)
    SCANLINE_SPACING = 4
    VIGNETTE_ALPHA = 182
    VIGNETTE_BORDER_RATIO = 0.10
    NOISE_ALPHA = 76
    NOISE_DENSITY = 0.0025
    FLICKER_COLOR = (198, 200, 210)
    FLICKER_MAX_ALPHA = 64
    TRIGGER_CHANCE_PER_PRESSURE = 0.0005
    TRIGGER_MIN_PRESSURE = 2

    def __init__(self, seed: int = 1937) -> None:
        self._rng = random.Random(seed)
        self._frame = 0
        self._strength = 0.0
        self._flashback_timer = 0
        self._flashback_cooldown = self.FLASHBACK_COOLDOWN // 2
        self._enemy_pressure = 0
        self._static_filter: pygame.Surface | None = None
        self._flicker_overlay: pygame.Surface | None = None
        self._band_buf: pygame.Surface | None = None
        self._noise_tex: pygame.Surface | None = None
        self._was_active = False
        self._flicker_timer = 0

    @property
    def current_strength(self) -> float:
        return self._strength

    @property
    def flashback_timer(self) -> int:
        """Frames remaining in the active flashback effect (0 = idle)."""
        return self._flashback_timer

    @property
    def flashback_cooldown(self) -> int:
        """Frames remaining before another flashback can trigger (0 = ready)."""
        return self._flashback_cooldown

    def is_active(self) -> bool:
        return self._strength > 0.025

    def dispose(self) -> None:
        self._static_filter = None
        self._flicker_overlay = None
        self._band_buf = None
        self._noise_tex = None

    def update(self, enemy_pressure: int = 0, enabled: bool = True) -> None:
        if not enabled:
            return

        self._frame += 1
        self._enemy_pressure = max(0, int(enemy_pressure))

        if self._flashback_cooldown > 0:
            self._flashback_cooldown -= 1

        if self._flashback_timer > 0:
            self._flashback_timer -= 1
            self._strength = 1.0
            was_active = self._was_active
            self._was_active = True
            if not was_active:
                self._flicker_timer = self.FLICKER_DURATION
            if self._flashback_timer <= 0:
                self._strength = 0.0
                self._was_active = False
                self._flicker_timer = self.FLICKER_DURATION
                self._flashback_cooldown = self.FLASHBACK_COOLDOWN
        else:
            self._strength = 0.0
            self._was_active = False
            if self._flashback_cooldown <= 0:
                self._maybe_trigger_flashback()

    def render_world_styles(self, surface: pygame.Surface, player: Any, enemies: Iterable, boss: Any = None) -> None:
        """Intentional no-op — flashback does not replace world entities."""
        pass

    def distort_world(self, surface: pygame.Surface) -> None:
        """Single-band CRT glitch displacement — small reusable buffer."""
        if not self.is_active():
            return
        width, height = surface.get_size()
        if height < 4:
            return
        y = self._rng.randint(0, max(1, height - 1))
        band_h = self._rng.randint(4, 10)
        band_h = max(1, min(band_h, height - y))
        shift = self._rng.randint(-10, 10)
        if -1 <= shift <= 1:
            return

        if self._band_buf is None or self._band_buf.get_width() != width or self._band_buf.get_height() < band_h:
            self._band_buf = pygame.Surface((width, band_h), pygame.SRCALPHA)
        self._band_buf.blit(surface, (0, 0), (0, y, width, band_h))
        surface.fill((0, 0, 0, 0), (0, y, width, band_h))
        surface.blit(self._band_buf, (shift, y))

    def render_atmosphere_overlay(self, surface: pygame.Surface) -> None:
        """Pre-rendered static filter + noise blit. Two blits, zero draws."""
        if not self.is_active():
            return
        width, height = surface.get_size()

        sf = self.get_static_filter(width, height)
        surface.blit(sf, (0, 0))

        noise = self.get_noise_tex(width, height)
        ox = self._rng.randint(-3, 3)
        oy = self._rng.randint(-2, 2)
        surface.blit(noise, (ox, oy))

    def render_projectile_styles(
        self, surface: pygame.Surface, player_bullets: Iterable, enemy_bullets: Iterable
    ) -> None:
        """Intentional no-op — flashback does not replace projectile visuals."""
        pass

    def render_foreground_distortion(self, surface: pygame.Surface, state: Any = None, player: Any = None) -> None:
        """Intentional no-op — flashback does not corrupt UI text."""
        pass

    def render_hud_corruption(self, surface: pygame.Surface) -> None:
        """Intentional no-op — HUD darkening is merged into render_atmosphere_overlay."""
        pass

    def render_transition_flicker(self, surface: pygame.Surface) -> None:
        """Brief white flash on flashback enter/exit — dedicated overlay."""
        if self._flicker_timer <= 0:
            return
        self._flicker_timer -= 1
        progress = 1.0 - self._flicker_timer / self.FLICKER_DURATION
        alpha = int(math.sin(progress * math.pi) * self.FLICKER_MAX_ALPHA)
        if alpha <= 2:
            return
        width, height = surface.get_size()
        if self._flicker_overlay is None or self._flicker_overlay.get_size() != (width, height):
            self._flicker_overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        self._flicker_overlay.fill((*self.FLICKER_COLOR, alpha))
        surface.blit(self._flicker_overlay, (0, 0))

    def _maybe_trigger_flashback(self) -> None:
        if self._enemy_pressure <= self.TRIGGER_MIN_PRESSURE:
            return
        if self._rng.random() < self.TRIGGER_CHANCE_PER_PRESSURE * self._enemy_pressure:
            self._flashback_timer = self.FLASHBACK_DURATION

    def get_static_filter(self, width: int, height: int) -> pygame.Surface:
        width = max(1, width)
        height = max(1, height)
        if self._static_filter is not None and self._static_filter.get_size() == (width, height):
            return self._static_filter

        sf = pygame.Surface((width, height), pygame.SRCALPHA)
        sf.fill(self.TINT_COLOR)

        for y in range(0, height, self.SCANLINE_SPACING):
            pygame.draw.line(sf, self.SCANLINE_COLOR, (0, y), (width, y))

        border = max(24, int(min(width, height) * self.VIGNETTE_BORDER_RATIO))
        sf.fill((0, 0, 0, self.VIGNETTE_ALPHA), (0, 0, width, border))
        sf.fill((0, 0, 0, self.VIGNETTE_ALPHA), (0, height - border, width, border))
        sf.fill((0, 0, 0, self.VIGNETTE_ALPHA), (0, 0, border, height))
        sf.fill((0, 0, 0, self.VIGNETTE_ALPHA), (width - border, 0, border, height))

        self._static_filter = sf
        return sf

    def get_noise_tex(self, width: int, height: int) -> pygame.Surface:
        width = max(1, width)
        height = max(1, height)
        if self._noise_tex is not None and self._noise_tex.get_size() == (width, height):
            return self._noise_tex

        tex = pygame.Surface((width, height), pygame.SRCALPHA)
        rng = random.Random(width * 918273 + height * 374651)
        count = int(width * height * self.NOISE_DENSITY)
        for _ in range(count):
            x = rng.randint(0, width - 1)
            y = rng.randint(0, height - 1)
            b = rng.randint(60, 255)
            a = rng.randint(24, 110)
            tex.set_at((x, y), (b, b, b, a))
        tex.set_alpha(self.NOISE_ALPHA)

        self._noise_tex = tex
        return tex
