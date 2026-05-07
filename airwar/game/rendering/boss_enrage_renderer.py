"""Screen-space boss enrage overlay renderer."""

import pygame


class BossEnrageRenderer:
    def __init__(self) -> None:
        self._enrage_overlay_cache = None
        self._enrage_overlay_cache_key = None
        self._enrage_distortion_buffer = None
        self._enrage_ripple_surface = None
        self._enrage_sin_a = None
        self._enrage_cos_a = None
        self._enrage_sin_b = None
        self._enrage_cos_b = None
        self._enrage_band_cache_key = None

    def render(self, surface: pygame.Surface, boss) -> None:
        self._render_boss_enrage_overlay(surface, boss)

    def _render_boss_enrage_overlay(self, surface: pygame.Surface, boss) -> None:
        if not boss:
            return

        intensity = boss.enrage_visual_intensity()
        if intensity <= 0:
            return
        sw, sh = surface.get_size()

        # Ensure persistent buffers are allocated (re-create on resize)
        buf_key = (sw, sh)
        if self._enrage_band_cache_key != buf_key:
            self._enrage_distortion_buffer = pygame.Surface((sw, sh))
            self._enrage_ripple_surface = pygame.Surface((sw, sh), pygame.SRCALPHA)
            self._enrage_overlay_cache = pygame.Surface((sw, sh), pygame.SRCALPHA)
            self._enrage_sin_a = None
            self._enrage_cos_a = None
            self._enrage_sin_b = None
            self._enrage_cos_b = None
            self._enrage_band_cache_key = buf_key

        ticks = pygame.time.get_ticks()

        # Phase B: ripple circles from the boss center on a pre-allocated surface
        self._enrage_ripple_surface.fill((0, 0, 0, 0))
        center_x = getattr(boss.rect, "centerx", sw // 2)
        center_y = getattr(boss.rect, "centery", sh // 2)
        ring_phase = ticks * 0.0018
        max_dim = max(sw, sh)
        for index in range(3):
            radius = int((ring_phase * 76 + index * 116) % max_dim)
            if radius < 20:
                continue
            alpha = int(12 * intensity * (1.0 - radius / max_dim))
            if alpha <= 0:
                continue
            pygame.draw.circle(self._enrage_ripple_surface, (160, 220, 255, alpha),
                               (int(center_x), int(center_y)), radius, 2)

        surface.blit(self._enrage_ripple_surface, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        # Phase C: dark vignette overlay (persistent cache, resize-aware)
        self._enrage_overlay_cache.fill((34, 28, 42, int(12 * intensity)))
        surface.blit(self._enrage_overlay_cache, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
