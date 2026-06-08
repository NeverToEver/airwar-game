"""Unit tests for GameSceneUpdater (Phase 5-ε sub-component).

Covers:
- The 15 PIPELINE_ORDER step methods (smoke + delegation)
- Short-circuit semantics for the 5 short-circuit-capable steps
- Cross-step ``_docked`` flag handoff between
  ``_step_mothership integrator`` and ``_step_core_logic``
- ``reset_state()`` resets per-frame state
- The 7 migrated helpers (``_update_haunting_effect``,
  ``_try_auto_save``, ``_sync_player_phase_dash_invincibility``,
  ``_update_mothership_ammo_warning``, ``_on_player_damaged``,
  ``_clear_nearby_enemy_bullets``, ``_on_give_up_complete``)

Pattern follows ``test_phase_5_gamma_subcomponents.py``: stub the scene
with ``SimpleNamespace`` + ``MagicMock`` for collaborators, isolated
from the real GameScene graph.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pygame

from airwar.game.constants import GAME_CONSTANTS
from airwar.game.managers.game_controller import GameplayState
from airwar.scenes.game_scene_updater import GameSceneUpdater
from airwar.scenes.update_pipeline import PIPELINE_ORDER


# ════════════════════════════════════════════════════════════════════════
# Fixtures
# ════════════════════════════════════════════════════════════════════════


def _make_player(rect=None, invincible=False, controls_locked=False):
    player = MagicMock()
    player.rect = rect or pygame.Rect(0, 0, 10, 10)
    player.health = 100
    player.max_health = 100
    player.is_phase_dash_invincible.return_value = invincible
    player.is_controls_locked = controls_locked
    return player


def _make_scene(**overrides):
    """Build a minimal scene stub for the updater to read.

    The updater holds ``self._scene`` typed as ``object`` and reads
    many scene attrs at runtime; this fixture sets just enough for
    the per-step tests below to run without raising AttributeError.
    """
    scene = SimpleNamespace(
        reward_selector=SimpleNamespace(update=MagicMock(), visible=False),
        _homecoming_coordinator=None,
        game_controller=SimpleNamespace(
            state=SimpleNamespace(
                is_paused=False, gameplay_state=GameplayState.PLAYING
            ),
            is_playing=MagicMock(return_value=True),
            is_game_over=MagicMock(return_value=False),
        ),
        notification_manager=MagicMock(),
        spawn_controller=SimpleNamespace(
            enemies=[],
            boss=None,
            enemy_bullets=[],
            cleanup=MagicMock(),
        ),
        _aim_assist=MagicMock(),
        _get_logical_mouse_pos=MagicMock(return_value=(0, 0)),
        _sync_player_aim_target=MagicMock(),
        _aim_crosshair=MagicMock(),
        _update_homecoming=MagicMock(),
        game_renderer=None,
        reward_system=SimpleNamespace(unlocked_buffs=[]),
        player=None,
        _warning_banner=None,
        _game_loop_manager=MagicMock(is_entrance_playing=MagicMock(return_value=False)),
        _mother_ship_integrator=None,
        _input_coordinator=MagicMock(),
        _milestone_manager=MagicMock(),
        _bullet_manager=MagicMock(),
        _lock_manager=MagicMock(),
        _haunting_renderer=None,
        _sync_lock_manager_targets=MagicMock(),
        event_bus=None,
        _is_homecoming_active=MagicMock(return_value=False),
        AUTO_SAVE_INTERVAL=GAME_CONSTANTS.PERSISTENCE.AUTO_SAVE_INTERVAL,
    )
    for key, value in overrides.items():
        setattr(scene, key, value)
    return scene


# ════════════════════════════════════════════════════════════════════════
# Construction
# ════════════════════════════════════════════════════════════════════════


def test_construction_creates_pipeline_with_all_15_steps() -> None:
    scene = _make_scene()
    updater = GameSceneUpdater(scene)

    # All 15 PIPELINE_ORDER steps must be registered.
    assert updater._pipeline.get_unwired_steps() == []
    assert len(updater._pipeline._steps) == len(PIPELINE_ORDER)


def test_construction_initializes_per_frame_state() -> None:
    scene = _make_scene()
    updater = GameSceneUpdater(scene)

    assert updater._docked is False
    assert updater._phase_dash_invincibility_active is False
    assert updater._survival_frames == 0
    assert updater._auto_save_timer == 0
    # _last_bullet_clear_frame is initialized to a sentinel (very negative).
    assert updater._last_bullet_clear_frame < 0


def test_reset_state_resets_all_per_frame_state() -> None:
    scene = _make_scene()
    updater = GameSceneUpdater(scene)

    updater._docked = True
    updater._phase_dash_invincibility_active = True
    updater._survival_frames = 9999
    updater._auto_save_timer = 500

    updater.reset_state()

    assert updater._docked is False
    assert updater._phase_dash_invincibility_active is False
    assert updater._survival_frames == 0
    assert updater._auto_save_timer == 0


# ════════════════════════════════════════════════════════════════════════
# Step smoke tests
# ════════════════════════════════════════════════════════════════════════


def test_step_reward_selector_delegates_to_scene() -> None:
    scene = _make_scene()
    updater = GameSceneUpdater(scene)
    result = updater._step_reward_selector()

    scene.reward_selector.update.assert_called_once_with()
    # No short-circuit (preserves pre-extraction behavior).
    assert result is None


def test_step_aim_assist_runs_homecoming_aim_and_hud() -> None:
    scene = _make_scene(
        game_renderer=SimpleNamespace(
            integrated_hud=SimpleNamespace(
                update_scroll=MagicMock(),
                update_health_tank=MagicMock(),
                update=MagicMock(),
            )
        ),
        player=_make_player(),
    )
    updater = GameSceneUpdater(scene)
    updater._step_aim_assist()

    scene._aim_assist.update.assert_called_once()
    scene._sync_player_aim_target.assert_called_once_with()
    scene._aim_crosshair.update.assert_called_once_with()
    scene._update_homecoming.assert_called_once_with()
    scene.game_renderer.integrated_hud.update_scroll.assert_called_once_with(0)
    scene.game_renderer.integrated_hud.update_health_tank.assert_called_once_with(100, 100)
    scene.game_renderer.integrated_hud.update.assert_called_once_with()


def test_step_aim_assist_skips_hud_when_no_renderer() -> None:
    scene = _make_scene(game_renderer=None)
    updater = GameSceneUpdater(scene)
    # Should not raise.
    updater._step_aim_assist()


def test_step_aim_assist_calls_update_base_when_coordinator_present() -> None:
    coordinator = MagicMock()
    scene = _make_scene(_homecoming_coordinator=coordinator)
    updater = GameSceneUpdater(scene)
    updater._step_aim_assist()

    coordinator.update_base.assert_called_once_with(
        scene.game_controller, scene.notification_manager
    )


def test_step_warning_banner_no_op_when_none() -> None:
    scene = _make_scene()
    updater = GameSceneUpdater(scene)
    # Should not raise.
    updater._step_warning_banner()


def test_step_warning_banner_updates_when_present() -> None:
    banner = MagicMock()
    scene = _make_scene(_warning_banner=banner)
    updater = GameSceneUpdater(scene)
    updater._step_warning_banner()

    banner.update.assert_called_once_with()


def test_step_entrance_animation_returns_false_when_playing() -> None:
    scene = _make_scene(
        _game_loop_manager=MagicMock(is_entrance_playing=MagicMock(return_value=True)),
        player=_make_player(),
    )
    updater = GameSceneUpdater(scene)
    result = updater._step_entrance_animation()

    scene._game_loop_manager.update_entrance.assert_called_once_with(scene.player)
    assert result is False


def test_step_entrance_animation_returns_none_when_not_playing() -> None:
    scene = _make_scene()
    updater = GameSceneUpdater(scene)
    result = updater._step_entrance_animation()

    scene._game_loop_manager.update_entrance.assert_not_called()
    assert result is None


def test_step_dying_animation_returns_false_when_dying() -> None:
    scene = _make_scene(
        game_controller=SimpleNamespace(
            state=SimpleNamespace(gameplay_state=GameplayState.DYING, is_paused=False)
        ),
        player=_make_player(),
    )
    updater = GameSceneUpdater(scene)
    result = updater._step_dying_animation()

    scene._game_loop_manager.update_game.assert_called_once_with(scene.player)
    assert result is False


def test_step_dying_animation_returns_none_when_alive() -> None:
    scene = _make_scene()
    updater = GameSceneUpdater(scene)
    result = updater._step_dying_animation()

    assert result is None


def test_step_pause_check_short_circuits_on_paused() -> None:
    scene = _make_scene(
        game_controller=SimpleNamespace(
            state=SimpleNamespace(is_paused=True, gameplay_state=GameplayState.PLAYING)
        )
    )
    updater = GameSceneUpdater(scene)
    assert updater._step_pause_check() is False


def test_step_pause_check_short_circuits_on_reward_visible() -> None:
    scene = _make_scene()
    scene.reward_selector.visible = True
    updater = GameSceneUpdater(scene)
    assert updater._step_pause_check() is False


def test_step_pause_check_returns_none_when_unpaused_and_hidden() -> None:
    scene = _make_scene()
    updater = GameSceneUpdater(scene)
    assert updater._step_pause_check() is None


def test_step_give_up_detector_delegates() -> None:
    scene = _make_scene()
    updater = GameSceneUpdater(scene)
    updater._step_give_up_detector()
    scene._input_coordinator.update_give_up.assert_called_once_with()


def test_step_milestone_check_passes_player() -> None:
    player = _make_player()
    scene = _make_scene(player=player)
    updater = GameSceneUpdater(scene)
    updater._step_milestone_check()
    scene._milestone_manager.check_and_trigger.assert_called_once_with(player)


def test_step_collision_passes_bullets_and_damage_callback() -> None:
    bullets = [MagicMock(), MagicMock()]
    player = _make_player()
    scene = _make_scene(
        player=player,
        spawn_controller=SimpleNamespace(enemy_bullets=bullets, cleanup=MagicMock()),
    )
    updater = GameSceneUpdater(scene)
    updater._step_collision()

    scene._game_loop_manager.check_collisions.assert_called_once()
    args = scene._game_loop_manager.check_collisions.call_args.args
    assert args[0] is player
    assert args[1] is bullets
    # Third arg is the _on_player_damaged callback.
    assert callable(args[2])


def test_step_post_collision_cleanup_runs_three_cleanups() -> None:
    scene = _make_scene(
        spawn_controller=SimpleNamespace(cleanup=MagicMock()),
        _bullet_manager=SimpleNamespace(cleanup=MagicMock()),
        player=_make_player(),
    )
    updater = GameSceneUpdater(scene)
    updater._step_post_collision_cleanup()

    scene.spawn_controller.cleanup.assert_called_once_with()
    scene._bullet_manager.cleanup.assert_called_once_with()
    scene.player.cleanup_inactive_bullets.assert_called_once_with()


# ════════════════════════════════════════════════════════════════════════
# Short-circuit behavior
# ════════════════════════════════════════════════════════════════════════


def test_run_short_circuits_when_homecoming_active() -> None:
    scene = _make_scene()
    scene._is_homecoming_active.return_value = True
    updater = GameSceneUpdater(scene)
    updater._pipeline.last_executed = []

    updater.run()

    # Should have run reward_selector + aim_assist + homecoming, then stopped.
    assert updater._pipeline.last_executed == ["reward_selector", "aim_assist", "homecoming"]


def test_run_short_circuits_on_pause_check() -> None:
    scene = _make_scene(
        game_controller=SimpleNamespace(
            state=SimpleNamespace(is_paused=True, gameplay_state=GameplayState.PLAYING)
        )
    )
    updater = GameSceneUpdater(scene)
    updater._pipeline.last_executed = []

    updater.run()

    # reward_selector + aim_assist + homecoming + warning_banner + entrance +
    # dying + pause_check. After pause_check returns False, stops.
    assert updater._pipeline.last_executed[-1] == "pause_check"
    # Nothing after pause_check ran.
    later = PIPELINE_ORDER[PIPELINE_ORDER.index("pause_check") + 1 :]
    for name in later:
        assert name not in updater._pipeline.last_executed


def test_run_full_pipeline_when_no_short_circuits() -> None:
    scene = _make_scene(
        _game_loop_manager=MagicMock(is_entrance_playing=MagicMock(return_value=False)),
        player=_make_player(),
    )
    updater = GameSceneUpdater(scene)
    updater._pipeline.last_executed = []

    updater.run()

    # All 15 steps ran.
    assert updater._pipeline.last_executed == PIPELINE_ORDER


# ════════════════════════════════════════════════════════════════════════
# Cross-step _docked flag
# ════════════════════════════════════════════════════════════════════════


def test_docked_flag_set_by_mothership_step_read_by_core_logic() -> None:
    """The mothership integrator step sets _docked; core_logic uses it for player rect lock."""
    integrator = MagicMock(
        is_docked=MagicMock(return_value=True),
        get_docking_position=MagicMock(return_value=(500, 300)),
    )
    player = _make_player(rect=pygame.Rect(0, 0, 10, 10))
    scene = _make_scene(
        _mother_ship_integrator=integrator,
        player=player,
    )
    updater = GameSceneUpdater(scene)

    updater._step_mothership_integrator()
    assert updater._docked is True

    updater._step_core_logic()
    # Player rect should be locked to the docking position.
    assert player.rect.x == 500 - 10 // 2
    assert player.rect.y == 300 - 10 // 2


def test_core_logic_does_not_lock_when_not_docked() -> None:
    integrator = MagicMock(is_docked=MagicMock(return_value=False))
    player = _make_player(rect=pygame.Rect(100, 100, 10, 10))
    scene = _make_scene(_mother_ship_integrator=integrator, player=player)
    updater = GameSceneUpdater(scene)

    updater._step_mothership_integrator()
    assert updater._docked is False

    updater._step_core_logic()
    # Player rect unchanged.
    assert (player.rect.x, player.rect.y) == (100, 100)


# ════════════════════════════════════════════════════════════════════════
# Auto-save step
# ════════════════════════════════════════════════════════════════════════


def test_step_auto_save_increments_survival_frames_and_timer() -> None:
    scene = _make_scene()
    updater = GameSceneUpdater(scene)

    updater._step_auto_save()

    assert updater._survival_frames == 1
    assert updater._auto_save_timer == 1
    # _try_auto_save not called yet (interval not reached).
    # _update_haunting_effect is no-op when _haunting_renderer is None.
    assert updater._auto_save_timer < scene.AUTO_SAVE_INTERVAL


def test_step_auto_save_fires_save_at_interval() -> None:
    scene = _make_scene()
    updater = GameSceneUpdater(scene)
    updater._auto_save_timer = scene.AUTO_SAVE_INTERVAL

    updater._step_auto_save()

    # Timer reset after firing.
    assert updater._auto_save_timer == 0


# ════════════════════════════════════════════════════════════════════════
# Migrated helpers
# ════════════════════════════════════════════════════════════════════════


def test_update_haunting_effect_no_op_when_renderer_missing() -> None:
    scene = _make_scene(_haunting_renderer=None)
    updater = GameSceneUpdater(scene)
    # Should not raise.
    updater._update_haunting_effect()


def test_update_haunting_effect_computes_pressure() -> None:
    renderer = MagicMock()
    enemies = [1, 2, 3]
    bullets = [1] * 12  # 12 bullets → adds 2 to pressure
    scene = _make_scene(
        _haunting_renderer=renderer,
        spawn_controller=SimpleNamespace(enemies=enemies, boss=None, enemy_bullets=bullets),
    )
    updater = GameSceneUpdater(scene)
    updater._update_haunting_effect()

    # 3 enemies + 2 (12//6 capped at 8 → 2) = 5
    renderer.update.assert_called_once_with(5)


def test_update_haunting_effect_adds_pressure_for_boss() -> None:
    renderer = MagicMock()
    scene = _make_scene(
        _haunting_renderer=renderer,
        spawn_controller=SimpleNamespace(
            enemies=[1, 2], boss=True, enemy_bullets=[]
        ),
    )
    updater = GameSceneUpdater(scene)
    updater._update_haunting_effect()

    # 2 enemies + 3 (boss) + 0 = 5
    renderer.update.assert_called_once_with(5)


def test_try_auto_save_no_op_when_docked() -> None:
    integrator = MagicMock(is_docked=MagicMock(return_value=True))
    scene = _make_scene(_mother_ship_integrator=integrator)
    updater = GameSceneUpdater(scene)
    updater._try_auto_save()
    # No save attempted.
    assert not integrator.create_save_data.called


def test_try_auto_save_no_op_when_not_playing() -> None:
    integrator = MagicMock(is_docked=MagicMock(return_value=False))
    scene = _make_scene(_mother_ship_integrator=integrator)
    scene.game_controller.is_playing.return_value = False
    updater = GameSceneUpdater(scene)
    updater._try_auto_save()
    assert not integrator.create_save_data.called


def test_on_give_up_complete_instant_kills_player() -> None:
    player = _make_player()
    controller = MagicMock()
    scene = _make_scene(player=player, game_controller=controller)
    updater = GameSceneUpdater(scene)
    updater._on_give_up_complete()

    controller.on_player_hit.assert_called_once_with(
        GAME_CONSTANTS.DAMAGE.INSTANT_KILL, player
    )


def test_on_player_damaged_applies_damage_and_clears_bullets() -> None:
    player = _make_player()
    controller = MagicMock()
    scene = _make_scene(player=player, game_controller=controller)
    updater = GameSceneUpdater(scene)
    updater._survival_frames = 1000

    updater._on_player_damaged(50, player)

    controller.on_player_hit.assert_called_once_with(50, player)
    assert updater._last_bullet_clear_frame == 1000


def test_clear_nearby_enemy_bullets_dedups_within_window() -> None:
    """The BULLET_CLEAR_DEDUP_FRAMES dedup window prevents re-clearing too soon."""
    player = _make_player(rect=pygame.Rect(100, 100, 10, 10))
    scene = _make_scene(
        player=player,
        spawn_controller=SimpleNamespace(enemy_bullets=[]),
    )
    updater = GameSceneUpdater(scene)
    # With BULLET_CLEAR_DEDUP_FRAMES=1, the dedup window blocks when
    # ``_survival_frames - _last_bullet_clear_frame < 1`` (i.e. same frame).
    updater._survival_frames = 1000
    updater._last_bullet_clear_frame = 1000  # same frame → dedup active

    updater._clear_nearby_enemy_bullets(player)
    # _last_bullet_clear_frame not updated (dedup active).
    assert updater._last_bullet_clear_frame == 1000


def test_clear_nearby_enemy_bullets_deactivates_close_bullets() -> None:
    """Bullets within BULLET_CLEAR_RADIUS get deactivated."""
    close = MagicMock(active=True, rect=pygame.Rect(120, 120, 4, 4))  # center 122,122
    far = MagicMock(active=True, rect=pygame.Rect(1000, 1000, 4, 4))
    player = _make_player(rect=pygame.Rect(100, 100, 10, 10))
    scene = _make_scene(
        player=player,
        spawn_controller=SimpleNamespace(enemy_bullets=[close, far]),
    )
    updater = GameSceneUpdater(scene)
    updater._survival_frames = 1000
    updater._last_bullet_clear_frame = -999  # outside dedup window

    updater._clear_nearby_enemy_bullets(player)
    assert close.active is False
    assert far.active is True  # outside radius
