from types import SimpleNamespace

import pygame

from airwar.entities.base import EnemyData
from airwar.entities.enemy import Enemy
from airwar.entities.player import Player
from airwar.game.rendering.haunting_renderer import HauntingRenderer
from airwar.input.input_handler import MockInputHandler


def test_haunting_renderer_reaches_full_replacement_strength() -> None:
    renderer = HauntingRenderer()

    renderer.update(HauntingRenderer.FULL_REPLACE_FRAME)

    assert renderer.progression == 1.0
    assert renderer.current_strength == 1.0
    assert renderer.is_active()


def test_haunting_renderer_does_not_mutate_gameplay_entities_or_state() -> None:
    pygame.font.init()
    renderer = HauntingRenderer()
    renderer.update(HauntingRenderer.FULL_REPLACE_FRAME, enemy_pressure=4)
    surface = pygame.Surface((640, 480), pygame.SRCALPHA)
    player = Player(260, 360, MockInputHandler())
    enemy = Enemy(250, 110, EnemyData(health=120, enemy_type="sine"))
    enemy._state = "active"
    enemy.sync_rects()
    state = SimpleNamespace(score=12345, kill_count=7)

    player_rect_before = (player.rect.x, player.rect.y, player.rect.width, player.rect.height)
    player_hitbox_before = player.get_hitbox().copy()
    enemy_rect_before = (enemy.rect.x, enemy.rect.y, enemy.rect.width, enemy.rect.height)
    enemy_collision_before = enemy.collision_rect.copy()
    state_before = (state.score, state.kill_count, player.health, enemy.health)

    renderer.render_world_styles(surface, player, [enemy])
    renderer.render_projectile_styles(surface, [], [])
    renderer.distort_world(surface)
    renderer.render_atmosphere_overlay(surface)
    renderer.render_foreground_distortion(surface, state, player)

    assert (player.rect.x, player.rect.y, player.rect.width, player.rect.height) == player_rect_before
    assert player.get_hitbox() == player_hitbox_before
    assert (enemy.rect.x, enemy.rect.y, enemy.rect.width, enemy.rect.height) == enemy_rect_before
    assert enemy.collision_rect == enemy_collision_before
    assert (state.score, state.kill_count, player.health, enemy.health) == state_before


def test_haunting_renderer_does_not_draw_black_player_veil() -> None:
    renderer = HauntingRenderer()
    renderer.update(HauntingRenderer.FULL_REPLACE_FRAME, enemy_pressure=1)
    surface = pygame.Surface((640, 480), pygame.SRCALPHA)
    player = Player(260, 360, MockInputHandler())

    renderer.render_world_styles(surface, player, [])

    center = (int(player.rect.centerx), int(player.rect.centery))
    center_color = surface.get_at(center)

    assert center_color.a > 0
    assert max(center_color.r, center_color.g, center_color.b) > 24


def test_haunting_renderer_rotated_sprites_do_not_add_black_alpha_edges() -> None:
    renderer = HauntingRenderer()
    renderer.update(HauntingRenderer.FULL_REPLACE_FRAME, enemy_pressure=1)
    surface = pygame.Surface((640, 480), pygame.SRCALPHA)
    player = Player(260, 360, MockInputHandler())
    enemy = Enemy(250, 110, EnemyData(health=120, enemy_type="sine"))
    enemy._state = "active"
    enemy.sync_rects()

    renderer.render_world_styles(surface, player, [enemy])

    assert _count_black_alpha_edge_pixels(surface) == 0


def test_haunting_renderer_inactive_before_start_frame() -> None:
    renderer = HauntingRenderer()
    renderer.update(0)
    assert not renderer.is_active()
    assert renderer.progression == 0.0
    assert renderer.current_strength == 0.0


def test_haunting_renderer_progression_increases_over_time() -> None:
    renderer = HauntingRenderer()
    halfway = (HauntingRenderer.FULL_REPLACE_FRAME + HauntingRenderer.START_FRAME) // 2
    renderer.update(halfway)
    assert 0.0 < renderer.progression < 1.0


def test_haunting_renderer_dispose_clears_state() -> None:
    renderer = HauntingRenderer()
    renderer.update(HauntingRenderer.FULL_REPLACE_FRAME)
    assert renderer.is_active()

    renderer.dispose()

    assert not renderer._storm_cache
    assert renderer._overlay is None
    assert renderer._blend_surf is None


def test_haunting_renderer_memory_fragments_expire() -> None:
    renderer = HauntingRenderer()
    fragment = HauntingRenderer.MemoryFragment(
        kind="letter", x=100, y=100, scale=1.0, alpha=200,
        age=0, duration=5, drift_x=0.0, drift_y=0.0,
    )
    renderer._memory_fragments.append(fragment)

    for _ in range(10):
        renderer.update(0)

    assert len(renderer._memory_fragments) == 0


def test_memory_fragment_does_not_expire_before_duration() -> None:
    renderer = HauntingRenderer()
    fragment = HauntingRenderer.MemoryFragment(
        kind="letter", x=100, y=100, scale=1.0, alpha=200,
        age=0, duration=120, drift_x=0.0, drift_y=0.0,
    )
    renderer._memory_fragments.append(fragment)

    for _ in range(60):
        renderer.update(0)

    assert len(renderer._memory_fragments) == 1
    assert renderer._memory_fragments[0].age == 60


def _count_black_alpha_edge_pixels(surface: pygame.Surface) -> int:
    count = 0
    for y in range(surface.get_height()):
        for x in range(surface.get_width()):
            color = surface.get_at((x, y))
            if 0 < color.a <= 64 and max(color.r, color.g, color.b) <= 10:
                count += 1
    return count
