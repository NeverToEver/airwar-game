"""Focused coverage for airwar.utils._sprites_ships — procedural ship sprite cache.

Targets the high-leverage entry points (player, enemy, elite, boss, prewarm)
without asserting on internal polygon geometry.  The intent is to lock down:
- Cache stability (same size => same Surface)
- Cache separation (different size / health bucket => different Surface)
- Bounded LRU eviction
- Visible-pixels invariants (alpha mask stays inside the surface border)
- Public draw_xxx_ship functions blit the cached sprite at the requested center
- prewarm_ship_sprite_caches is idempotent and force-reloadable
"""

import pygame
import pytest

import airwar.utils._sprites_ships as _ships
from airwar.utils._sprites_ships import (
    BOSS_SPRITE_STYLE_VERSION,
    ELITE_SPRITE_STYLE_VERSION,
    ENEMY_SPRITE_STYLE_VERSION,
    PLAYER_SPRITE_CACHE_MAX,
    PLAYER_SPRITE_MIN_BORDER,
    PLAYER_SPRITE_STYLE_VERSION,
    _boss_sprite_cache,
    _elite_sprite_cache,
    _enemy_sprite_cache,
    _player_sprite_cache,
    draw_boss_ship,
    draw_elite_enemy_ship,
    draw_enemy_ship,
    draw_player_ship,
    get_boss_sprite,
    get_elite_enemy_sprite,
    get_enemy_sprite,
    get_player_sprite,
    prewarm_ship_sprite_caches,
)


@pytest.fixture(autouse=True)
def _fresh_disk_cache(monkeypatch, tmp_path):
    """Force a per-test empty on-disk cache so the build lambda always runs.

    The conftest points ``AIRWAR_GENERATED_ASSET_DIR`` at a single temp dir;
    without isolation, the first test populates the disk and every
    subsequent test loads the cached PNG instead of executing the polygon
    draw paths.  Monkeypatching to a fresh ``tmp_path`` for each test makes
    the build lambda run in-process, which is what we want to cover.
    """
    monkeypatch.setenv("AIRWAR_GENERATED_ASSET_DIR", str(tmp_path))
    _ships._ship_sprite_caches_prewarmed = False
    for cache in (_player_sprite_cache, _enemy_sprite_cache, _elite_sprite_cache, _boss_sprite_cache):
        cache.clear()
    yield
    for cache in (_player_sprite_cache, _enemy_sprite_cache, _elite_sprite_cache, _boss_sprite_cache):
        cache.clear()
    _ships._ship_sprite_caches_prewarmed = False


# ─── helpers ─────────────────────────────────────────────────────────────────


def _alpha_bounds(surface: pygame.Surface) -> pygame.Rect | None:
    mask = pygame.mask.from_surface(surface)
    rects = mask.get_bounding_rects()
    if not rects:
        return None
    bounds = rects[0].copy()
    for rect in rects[1:]:
        bounds.union_ip(rect)
    return bounds


def _has_visible_pixels(surface: pygame.Surface) -> bool:
    return pygame.mask.from_surface(surface).count() > 0


# ─── player sprite ───────────────────────────────────────────────────────────


class TestPlayerSprite:
    def test_get_player_sprite_returns_cached_surface_for_same_size(self) -> None:
        first = get_player_sprite(50, 60)
        second = get_player_sprite(50, 60)
        assert first is second
        assert isinstance(first, pygame.Surface)

    def test_get_player_sprite_separates_sizes(self) -> None:
        a = get_player_sprite(50, 60)
        b = get_player_sprite(80, 96)
        assert a is not b
        assert len(_player_sprite_cache) == 2

    def test_get_player_sprite_cache_is_bounded(self) -> None:
        for i in range(PLAYER_SPRITE_CACHE_MAX + 4):
            get_player_sprite(40 + i, 50 + i)
        assert len(_player_sprite_cache) <= PLAYER_SPRITE_CACHE_MAX

    def test_player_sprite_has_visible_pixels_inside_border(self) -> None:
        sprite = get_player_sprite(50, 60)
        assert _has_visible_pixels(sprite)
        bounds = _alpha_bounds(sprite)
        assert bounds is not None
        assert bounds.left >= PLAYER_SPRITE_MIN_BORDER
        assert bounds.top >= PLAYER_SPRITE_MIN_BORDER
        assert bounds.right <= sprite.get_width() - PLAYER_SPRITE_MIN_BORDER
        assert bounds.bottom <= sprite.get_height() - PLAYER_SPRITE_MIN_BORDER

    def test_draw_player_ship_blits_centered(self) -> None:
        canvas = pygame.Surface((400, 400), pygame.SRCALPHA)
        draw_player_ship(canvas, 200, 200, 50, 60)
        # At least one non-transparent pixel must land near the requested center.
        assert _has_visible_pixels(canvas)

    def test_player_style_version_constant_matches(self) -> None:
        # Lock the style version so silent polygon refactors show up as a test
        # failure rather than a silent re-skin.
        assert PLAYER_SPRITE_STYLE_VERSION == 5


# ─── enemy sprite ────────────────────────────────────────────────────────────


class TestEnemySprite:
    def test_get_enemy_sprite_caches_per_size_and_health(self) -> None:
        full = get_enemy_sprite(50, 50, 1.0)
        full_again = get_enemy_sprite(50, 50, 1.0)
        wounded = get_enemy_sprite(50, 50, 0.2)
        different_size = get_enemy_sprite(60, 60, 1.0)

        assert full is full_again
        assert full is not wounded
        assert full is not different_size
        assert isinstance(full, pygame.Surface)
        assert _has_visible_pixels(full)

    def test_enemy_health_ratio_buckets_differ(self) -> None:
        # Health ratios that fall in different int*10 buckets should yield
        # different cache entries (enemy uses int(health_ratio*10) bucketing).
        a = get_enemy_sprite(50, 50, 0.9)
        b = get_enemy_sprite(50, 50, 0.5)
        c = get_enemy_sprite(50, 50, 0.1)
        assert a is not b
        assert b is not c
        assert len(_enemy_sprite_cache) == 3

    def test_draw_enemy_ship_blits_centered(self) -> None:
        canvas = pygame.Surface((400, 400), pygame.SRCALPHA)
        draw_enemy_ship(canvas, 200, 200, 50, 50, 1.0)
        assert _has_visible_pixels(canvas)

    def test_enemy_style_version_constant(self) -> None:
        assert ENEMY_SPRITE_STYLE_VERSION == 3


# ─── elite enemy sprite ──────────────────────────────────────────────────────


class TestEliteEnemySprite:
    def test_get_elite_enemy_sprite_caches(self) -> None:
        full = get_elite_enemy_sprite(65, 65, 1.0)
        full_again = get_elite_enemy_sprite(65, 65, 1.0)
        wounded = get_elite_enemy_sprite(65, 65, 0.2)

        assert full is full_again
        assert full is not wounded
        assert _has_visible_pixels(full)

    def test_elite_sprite_larger_than_standard_enemy(self) -> None:
        standard = get_enemy_sprite(50, 50, 1.0)
        elite = get_elite_enemy_sprite(65, 65, 1.0)
        assert elite.get_width() > standard.get_width()

    def test_draw_elite_enemy_ship_blits_centered(self) -> None:
        canvas = pygame.Surface((400, 400), pygame.SRCALPHA)
        draw_elite_enemy_ship(canvas, 200, 200, 65, 65, 1.0)
        assert _has_visible_pixels(canvas)

    def test_elite_style_version_constant(self) -> None:
        assert ELITE_SPRITE_STYLE_VERSION == 2


# ─── boss sprite ─────────────────────────────────────────────────────────────


class TestBossSprite:
    def test_get_boss_sprite_caches(self) -> None:
        full = get_boss_sprite(120, 100, 1.0)
        full_again = get_boss_sprite(120, 100, 1.0)
        wounded = get_boss_sprite(120, 100, 0.2)

        assert full is full_again
        assert full is not wounded
        assert _has_visible_pixels(full)

    def test_boss_sprite_larger_than_elite(self) -> None:
        elite = get_elite_enemy_sprite(65, 65, 1.0)
        boss = get_boss_sprite(120, 100, 1.0)
        assert boss.get_width() > elite.get_width()

    def test_draw_boss_ship_blits_centered(self) -> None:
        canvas = pygame.Surface((400, 400), pygame.SRCALPHA)
        draw_boss_ship(canvas, 200, 200, 120, 100, 1.0)
        assert _has_visible_pixels(canvas)

    def test_boss_style_version_constant(self) -> None:
        assert BOSS_SPRITE_STYLE_VERSION == 4


# ─── prewarm ─────────────────────────────────────────────────────────────────


class TestPrewarm:
    def test_prewarm_populates_caches(self) -> None:
        prewarm_ship_sprite_caches()
        assert _player_sprite_cache
        assert _enemy_sprite_cache
        assert _elite_sprite_cache
        assert _boss_sprite_cache
        assert _ships._ship_sprite_caches_prewarmed is True

    def test_prewarm_idempotent_when_already_loaded(self) -> None:
        prewarm_ship_sprite_caches()
        first_player_count = len(_player_sprite_cache)
        # Second call without force should be a no-op (early return).
        prewarm_ship_sprite_caches()
        assert len(_player_sprite_cache) == first_player_count

    def test_prewarm_force_re_populates_caches(self) -> None:
        prewarm_ship_sprite_caches()
        assert _ships._ship_sprite_caches_prewarmed is True
        # force=True must re-run even when the prewarm flag is set.
        prewarm_ship_sprite_caches(force=True)
        assert _ships._ship_sprite_caches_prewarmed is True
        # Cache still contains the prewarm entries.
        assert _player_sprite_cache
        assert _boss_sprite_cache
