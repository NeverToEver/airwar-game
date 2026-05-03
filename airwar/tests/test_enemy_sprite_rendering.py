import pygame

from airwar.utils._sprites_ships import (
    _boss_sprite_cache,
    _elite_sprite_cache,
    _enemy_sprite_cache,
    get_boss_sprite,
    get_elite_enemy_sprite,
    get_enemy_sprite,
)


def _alpha_bounds(surface: pygame.Surface) -> pygame.Rect:
    mask = pygame.mask.from_surface(surface)
    rects = mask.get_bounding_rects()
    assert rects, "sprite should contain visible pixels"
    bounds = rects[0].copy()
    for rect in rects[1:]:
        bounds.union_ip(rect)
    return bounds


def _assert_visible_pixels_are_not_clipped(surface: pygame.Surface, border: int = 2):
    bounds = _alpha_bounds(surface)

    assert bounds.left >= border
    assert bounds.top >= border
    assert bounds.right <= surface.get_width() - border
    assert bounds.bottom <= surface.get_height() - border


def test_enemy_sprite_cache_separates_health_buckets():
    _enemy_sprite_cache.clear()

    healthy = get_enemy_sprite(50, 50, 1.0)
    damaged = get_enemy_sprite(50, 50, 0.4)
    repeated = get_enemy_sprite(50, 50, 1.0)

    assert healthy is repeated
    assert healthy is not damaged


def test_enemy_sprite_visible_pixels_stay_inside_cache_surface():
    _assert_visible_pixels_are_not_clipped(get_enemy_sprite(50, 50, 1.0))
    _assert_visible_pixels_are_not_clipped(get_enemy_sprite(50, 50, 0.25))


def test_elite_sprite_cache_and_bounds_are_stable():
    _elite_sprite_cache.clear()

    healthy = get_elite_enemy_sprite(78, 78, 1.0)
    damaged = get_elite_enemy_sprite(78, 78, 0.35)

    assert healthy is get_elite_enemy_sprite(78, 78, 1.0)
    assert healthy is not damaged
    _assert_visible_pixels_are_not_clipped(healthy)
    _assert_visible_pixels_are_not_clipped(damaged)


def test_boss_sprite_cache_and_bounds_are_stable():
    _boss_sprite_cache.clear()

    healthy = get_boss_sprite(150, 125, 1.0)
    damaged = get_boss_sprite(150, 125, 0.25)

    assert healthy is get_boss_sprite(150, 125, 1.0)
    assert healthy is not damaged
    _assert_visible_pixels_are_not_clipped(healthy)
    _assert_visible_pixels_are_not_clipped(damaged)
