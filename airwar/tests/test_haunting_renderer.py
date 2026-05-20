from types import SimpleNamespace

import pygame

from airwar.entities.base import EnemyData
from airwar.entities.enemy import Enemy
from airwar.entities.player import Player
from airwar.game.rendering.haunting_renderer import HauntingRenderer
from airwar.input.input_handler import MockInputHandler


def test_flashback_triggers_with_high_enemy_pressure() -> None:
    renderer = HauntingRenderer()

    for _ in range(2000):
        renderer.update(enemy_pressure=10)

    assert renderer._flashback_timer > 0 or renderer._flashback_cooldown > 0


def test_flashback_does_not_trigger_with_low_pressure() -> None:
    renderer = HauntingRenderer()

    for _ in range(500):
        renderer.update(enemy_pressure=1)

    assert not renderer.is_active()
    assert renderer._flashback_timer == 0


def test_flashback_activates_and_deactivates() -> None:
    renderer = HauntingRenderer()
    renderer._flashback_timer = HauntingRenderer.FLASHBACK_DURATION
    renderer.update(enemy_pressure=5)

    assert renderer.is_active()
    assert renderer.current_strength > 0.0

    for _ in range(HauntingRenderer.FLASHBACK_DURATION + 5):
        renderer.update(enemy_pressure=0)

    assert not renderer.is_active()
    assert renderer.current_strength == 0.0


def test_flashback_strength_instant_on_off() -> None:
    """Flashback hits full strength immediately and cuts to zero when expired."""
    renderer = HauntingRenderer()
    renderer._flashback_timer = HauntingRenderer.FLASHBACK_DURATION
    renderer.update(enemy_pressure=0)
    assert renderer.current_strength == 1.0

    for _ in range(HauntingRenderer.FLASHBACK_DURATION - 2):
        renderer.update(enemy_pressure=0)
    assert renderer.current_strength == 1.0

    renderer.update(enemy_pressure=0)
    assert renderer.current_strength == 0.0
    assert not renderer.is_active()


def test_flashback_inactive_by_default() -> None:
    renderer = HauntingRenderer()
    renderer.update()
    assert not renderer.is_active()
    assert renderer.current_strength == 0.0


def test_flashback_cooldown_prevents_immediate_retrigger() -> None:
    renderer = HauntingRenderer()
    renderer._flashback_timer = HauntingRenderer.FLASHBACK_DURATION
    renderer.update(enemy_pressure=5)

    for _ in range(HauntingRenderer.FLASHBACK_DURATION + 2):
        renderer.update(enemy_pressure=0)

    assert not renderer.is_active()
    assert renderer._flashback_cooldown > 0


def test_haunting_renderer_dispose_clears_state() -> None:
    renderer = HauntingRenderer()
    renderer._flashback_timer = HauntingRenderer.FLASHBACK_DURATION
    renderer.update(enemy_pressure=5)
    assert renderer.is_active()

    renderer.dispose()

    assert renderer._static_filter is None
    assert renderer._band_buf is None


def test_haunting_renderer_survives_render_after_dispose() -> None:
    renderer = HauntingRenderer()
    renderer._flashback_timer = HauntingRenderer.FLASHBACK_DURATION
    renderer.update(enemy_pressure=1)
    renderer.dispose()

    surface = pygame.Surface((640, 480), pygame.SRCALPHA)
    renderer.render_world_styles(surface, None, [])
    renderer.render_projectile_styles(surface, [], [])
    renderer.distort_world(surface)
    renderer.render_atmosphere_overlay(surface)
    renderer.render_foreground_distortion(surface, None, None)


def test_haunting_renderer_recreates_surfaces_after_dispose() -> None:
    renderer = HauntingRenderer()
    renderer._flashback_timer = HauntingRenderer.FLASHBACK_DURATION
    renderer.update(enemy_pressure=1)
    renderer.dispose()
    assert renderer._static_filter is None

    renderer._flashback_timer = HauntingRenderer.FLASHBACK_DURATION
    renderer.update(enemy_pressure=1)
    surface = pygame.Surface((640, 480), pygame.SRCALPHA)
    renderer.render_atmosphere_overlay(surface)

    assert renderer._static_filter is not None


def test_crt_glitch_effects_render_without_crash() -> None:
    """All CRT glitch passes should render without error during active flashback."""
    pygame.font.init()
    renderer = HauntingRenderer()
    renderer._flashback_timer = HauntingRenderer.FLASHBACK_DURATION
    renderer.update(enemy_pressure=4)
    surface = pygame.Surface((640, 480), pygame.SRCALPHA)
    player = Player(260, 360, MockInputHandler())
    enemy = Enemy(250, 110, EnemyData(health=120, enemy_type="sine"))
    enemy._state = "active"
    enemy.sync_rects()
    state = SimpleNamespace(score=12345, kill_count=7)

    renderer.render_world_styles(surface, player, [enemy])
    renderer.render_projectile_styles(surface, [], [])
    renderer.distort_world(surface)
    renderer.render_atmosphere_overlay(surface)
    renderer.render_foreground_distortion(surface, state, player)
    renderer.render_hud_corruption(surface)
    renderer.render_transition_flicker(surface)


def test_crt_glitch_does_not_mutate_entities() -> None:
    renderer = HauntingRenderer()
    renderer._flashback_timer = HauntingRenderer.FLASHBACK_DURATION
    renderer.update(enemy_pressure=4)
    surface = pygame.Surface((640, 480), pygame.SRCALPHA)
    player = Player(260, 360, MockInputHandler())
    enemy = Enemy(250, 110, EnemyData(health=120, enemy_type="sine"))
    enemy._state = "active"
    enemy.sync_rects()
    state = SimpleNamespace(score=12345, kill_count=7)

    player_hp_before = player.health
    enemy_hp_before = enemy.health
    state_score_before = state.score

    renderer.render_world_styles(surface, player, [enemy])
    renderer.render_projectile_styles(surface, [], [])
    renderer.distort_world(surface)
    renderer.render_atmosphere_overlay(surface)
    renderer.render_foreground_distortion(surface, state, player)

    assert player.health == player_hp_before
    assert enemy.health == enemy_hp_before
    assert state.score == state_score_before


def test_static_filter_is_cached() -> None:
    """_get_static_filter reuses the surface on same-size calls."""
    renderer = HauntingRenderer()
    w, h = 640, 480

    sf1 = renderer._get_static_filter(w, h)
    sf2 = renderer._get_static_filter(w, h)

    assert sf1 is sf2


def test_noise_tex_is_cached() -> None:
    """_get_noise_tex reuses the surface on same-size calls."""
    renderer = HauntingRenderer()
    w, h = 640, 480

    nt1 = renderer._get_noise_tex(w, h)
    nt2 = renderer._get_noise_tex(w, h)

    assert nt1 is nt2
