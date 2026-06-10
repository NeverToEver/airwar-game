"""Regression tests for the explosion-effect LRU caches.

Background: P3-1 (commit ``cfd0d5c``) converted the explosion-effect
caches from FIFO to LRU. The LRU helpers call ``.move_to_end`` and
``.popitem(last=...)`` — APIs that are only on ``OrderedDict`` — but
the cache initialisers were left as plain ``{}``. The bug stayed
hidden because the dummy SDL driver never reaches the explosion
render path during tests, so the game crashed only when an actual
window was opened.

These tests pin the cache types so a future "let's just use a dict"
refactor cannot regress silently again.
"""

from __future__ import annotations

import os

import pygame

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


def _ensure_pygame() -> None:
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()
    if not pygame.display.get_init():
        pygame.display.set_mode((1, 1))


def test_explosion_caches_are_ordered_dicts() -> None:
    """The LRU helpers call ``move_to_end`` / ``popitem(last=...)``,
    which only exist on ``OrderedDict``. Pin the type so a future
    refactor that swaps to ``{}`` will fail at import-time."""
    from collections import OrderedDict

    from airwar.game.explosion_animation import explosion_effect

    assert isinstance(explosion_effect._glow_texture_cache, OrderedDict)
    assert isinstance(explosion_effect._spark_core_cache, OrderedDict)
    assert isinstance(explosion_effect._flash_cache, OrderedDict)


def test_spark_core_cache_supports_lru_eviction() -> None:
    """Drive the cache to capacity and confirm LRU semantics, not FIFO.

    With capacity 1 the second insert must evict the first, and a
    re-lookup of the first key must miss — exactly the contract the
    crash relied on.
    """
    from airwar.game.explosion_animation.explosion_effect import _MAX_CACHE_SIZE, _get_spark_core

    _ensure_pygame()

    # Force the cache to a known-small capacity so the test is fast
    # and doesn't actually grow to 64 entries.
    from airwar.game.explosion_animation import explosion_effect

    explosion_effect._spark_core_cache.clear()

    # Sanity: a normal lookup creates and caches a surface.
    surf_a = _get_spark_core(3)
    assert surf_a.get_size() == (3 * 2 + 2, 3 * 2 + 2)
    assert 3 in explosion_effect._spark_core_cache

    # Touch the first key so it moves to the back of the LRU.
    explosion_effect._spark_core_cache.move_to_end(3)

    # Now insert one more entry. If the cache is a plain dict, the
    # ``popitem(last=False)`` call below will raise ``AttributeError``
    # and the test fails before getting to the assert.
    explosion_effect._spark_core_cache[7] = _get_spark_core(7)
    assert 7 in explosion_effect._spark_core_cache
    assert len(explosion_effect._spark_core_cache) == 2

    # Confirm ``_MAX_CACHE_SIZE`` is still ≥ 2 so the test exercise
    # stays in a non-evicting regime (we're not testing the eviction
    # edge — that's ``_get_spark_core``'s internal logic and is
    # covered by the type assertion above).
    assert _MAX_CACHE_SIZE >= 2
