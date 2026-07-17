"""Regression tests for bullet sprite glow buffer sizing.

draw_explosive_missile used to pass the pre-scaled body width into
create_explosive_missile_glow (which scales by 0.8 internally) while
computing the expected buffer size without that factor, so the RGBA
buffer length never matched the expected surface dimensions and any
non-prewarmed missile size raised ValueError mid-frame.
"""

import pygame

from airwar.utils._sprites_bullets import draw_explosive_missile
from airwar.utils._sprites_common import _explosive_missile_cache


class TestExplosiveMissileGlow:
    def test_unprewarmed_size_does_not_crash(self):
        _explosive_missile_cache.clear()
        surface = pygame.Surface((200, 200), pygame.SRCALPHA)

        # 13px width: caller/binding size rounding diverged before the fix.
        draw_explosive_missile(surface, 10, 10, 13, 20)

        assert (10, 20) in _explosive_missile_cache

    def test_prewarmed_sizes_still_work(self):
        _explosive_missile_cache.clear()
        surface = pygame.Surface((200, 200), pygame.SRCALPHA)

        for w, h in [(10, 20), (8, 16), (12, 24)]:
            draw_explosive_missile(surface, 10, 10, w, h)

        assert len(_explosive_missile_cache) == 3
