import pygame

from airwar.entities.player import Player
from airwar.input.input_handler import MockInputHandler
from airwar.utils._sprites_ships import (
    PLAYER_SPRITE_CACHE_MAX,
    PLAYER_SPRITE_MIN_BORDER,
    _player_sprite_cache,
    get_player_sprite,
)


def _alpha_bounds(surface: pygame.Surface) -> pygame.Rect:
    mask = pygame.mask.from_surface(surface)
    rects = mask.get_bounding_rects()
    assert rects, "player sprite should contain visible pixels"
    bounds = rects[0].copy()
    for rect in rects[1:]:
        bounds.union_ip(rect)
    return bounds


def test_player_sprite_uses_stable_cache_for_same_size():
    _player_sprite_cache.clear()

    first = get_player_sprite(68, 82)
    second = get_player_sprite(68, 82)

    assert first is second
    assert len(_player_sprite_cache) == 1


def test_player_sprite_cache_separates_sizes_and_is_bounded():
    _player_sprite_cache.clear()

    small = get_player_sprite(68, 82)
    large = get_player_sprite(80, 96)
    for index in range(PLAYER_SPRITE_CACHE_MAX + 4):
        get_player_sprite(50 + index, 60 + index)

    assert small is not large
    assert len(_player_sprite_cache) <= PLAYER_SPRITE_CACHE_MAX


def test_player_sprite_visible_pixels_stay_inside_cache_surface():
    sprite = get_player_sprite(68, 82)
    bounds = _alpha_bounds(sprite)

    assert bounds.left >= PLAYER_SPRITE_MIN_BORDER
    assert bounds.top >= PLAYER_SPRITE_MIN_BORDER
    assert bounds.right <= sprite.get_width() - PLAYER_SPRITE_MIN_BORDER
    assert bounds.bottom <= sprite.get_height() - PLAYER_SPRITE_MIN_BORDER


def test_player_hitbox_remains_independent_from_visual_sprite_size():
    player = Player(400, 900, MockInputHandler())
    hitbox = player.get_hitbox()
    sprite = get_player_sprite(player.rect.width, player.rect.height)

    assert hitbox.width == Player.PLAYER_HITBOX_W
    assert hitbox.height == Player.PLAYER_HITBOX_H
    assert hitbox.center == player.get_rect().center
    assert hitbox.width < player.rect.width
    assert hitbox.height < player.rect.height
    assert sprite.get_width() > player.rect.width
