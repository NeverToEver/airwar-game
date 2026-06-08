"""Unit tests for GameSceneEventDispatcher (Phase 5-ε sub-component).

Covers the 3 event types routed by the dispatcher:
- KEYDOWN + K_l → toggle integrated HUD
- MOUSEMOTION → aim assist + sync + base console hover + scene hover
- MOUSEBUTTONDOWN → aim assist + sync + (optional) base console click →
  (optional) scene click + (optional) registered button click

The dispatcher is stateless across frames; the scene owns the
persistent state (pause request, hover, button registry, etc.).
Pattern follows ``test_game_scene_updater.py``: stub the scene with
``SimpleNamespace`` + ``MagicMock`` for collaborators.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pygame

from airwar.scenes.game_scene_event_dispatcher import GameSceneEventDispatcher


# ════════════════════════════════════════════════════════════════════════
# Fixtures
# ════════════════════════════════════════════════════════════════════════


def _make_scene(**overrides):
    """Build a minimal scene stub for the dispatcher to dispatch into."""
    scene = SimpleNamespace(
        _input_coordinator=MagicMock(),
        game_renderer=None,
        _aim_assist=MagicMock(),
        _sync_player_aim_target=MagicMock(),
        _homecoming_base_pending=False,
        _base_talent_console=None,
        handle_mouse_motion=MagicMock(),
        _handle_base_console_click=MagicMock(return_value=False),
        handle_mouse_click=MagicMock(return_value=False),
        _handle_button_click=MagicMock(),
        get_hovered_button=MagicMock(return_value=None),
    )
    for key, value in overrides.items():
        setattr(scene, key, value)
    return scene


def _keydown_event(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, {"key": key, "mod": 0, "unicode": "", "scancode": 0})


def _mousemotion_event(pos=(100, 200)) -> pygame.event.Event:
    return pygame.event.Event(pygame.MOUSEMOTION, {"pos": pos, "rel": (0, 0), "buttons": (0, 0, 0)})


def _mousebuttondown_event(button: int = 1, pos=(100, 200)) -> pygame.event.Event:
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": button, "pos": pos})


# ════════════════════════════════════════════════════════════════════════
# KEYDOWN
# ════════════════════════════════════════════════════════════════════════


def test_keydown_l_toggles_hud() -> None:
    hud = MagicMock()
    scene = _make_scene(game_renderer=SimpleNamespace(integrated_hud=hud))
    dispatcher = GameSceneEventDispatcher(scene)

    dispatcher.dispatch(_keydown_event(pygame.K_l))

    hud.toggle.assert_called_once_with()


def test_keydown_l_no_op_when_no_hud() -> None:
    scene = _make_scene(game_renderer=SimpleNamespace(integrated_hud=None))
    dispatcher = GameSceneEventDispatcher(scene)
    # Should not raise.
    dispatcher.dispatch(_keydown_event(pygame.K_l))


def test_keydown_other_key_ignored() -> None:
    scene = _make_scene()
    dispatcher = GameSceneEventDispatcher(scene)
    dispatcher.dispatch(_keydown_event(pygame.K_ESCAPE))
    # Only the input coordinator saw the event.
    scene._input_coordinator.handle_events.assert_called_once()


# ════════════════════════════════════════════════════════════════════════
# MOUSEMOTION
# ════════════════════════════════════════════════════════════════════════


def test_mousemotion_updates_aim_assist_and_syncs() -> None:
    scene = _make_scene()
    dispatcher = GameSceneEventDispatcher(scene)
    event = _mousemotion_event(pos=(300, 400))

    dispatcher.dispatch(event)

    scene._aim_assist.set_raw_aim_position.assert_called_once_with((300, 400))
    scene._sync_player_aim_target.assert_called_once_with()


def test_mousemotion_dispatches_to_base_console_when_pending() -> None:
    console = MagicMock()
    scene = _make_scene(
        _homecoming_base_pending=True,
        _base_talent_console=console,
    )
    dispatcher = GameSceneEventDispatcher(scene)
    event = _mousemotion_event(pos=(150, 250))

    dispatcher.dispatch(event)

    console.handle_mouse_motion.assert_called_once_with((150, 250))


def test_mousemotion_skips_base_console_when_not_pending() -> None:
    console = MagicMock()
    scene = _make_scene(
        _homecoming_base_pending=False,
        _base_talent_console=console,
    )
    dispatcher = GameSceneEventDispatcher(scene)
    dispatcher.dispatch(_mousemotion_event())

    console.handle_mouse_motion.assert_not_called()


def test_mousemotion_dispatches_to_scene_hover() -> None:
    scene = _make_scene()
    dispatcher = GameSceneEventDispatcher(scene)
    event = _mousemotion_event(pos=(10, 20))

    dispatcher.dispatch(event)

    scene.handle_mouse_motion.assert_called_once_with((10, 20))


# ════════════════════════════════════════════════════════════════════════
# MOUSEBUTTONDOWN
# ════════════════════════════════════════════════════════════════════════


def test_mousebuttondown_updates_aim_assist_and_syncs() -> None:
    scene = _make_scene()
    dispatcher = GameSceneEventDispatcher(scene)
    event = _mousebuttondown_event(button=1, pos=(50, 60))

    dispatcher.dispatch(event)

    scene._aim_assist.set_raw_aim_position.assert_called_once_with((50, 60))
    scene._sync_player_aim_target.assert_called_once_with()


def test_mousebuttondown_left_console_consumes_event() -> None:
    """Left button + base pending + console handles click → early return."""
    scene = _make_scene(
        _homecoming_base_pending=True,
        _handle_base_console_click=MagicMock(return_value=True),
    )
    dispatcher = GameSceneEventDispatcher(scene)
    event = _mousebuttondown_event(button=1, pos=(80, 90))

    dispatcher.dispatch(event)

    scene._handle_base_console_click.assert_called_once_with((80, 90))
    scene.handle_mouse_click.assert_not_called()
    scene._handle_button_click.assert_not_called()


def test_mousebuttondown_left_no_console_pending_dispatches_scene_click() -> None:
    scene = _make_scene(
        _homecoming_base_pending=False,
        handle_mouse_click=MagicMock(return_value=True),
        get_hovered_button=MagicMock(return_value="pause"),
    )
    dispatcher = GameSceneEventDispatcher(scene)
    event = _mousebuttondown_event(button=1, pos=(70, 80))

    dispatcher.dispatch(event)

    scene._handle_base_console_click.assert_not_called()
    scene.handle_mouse_click.assert_called_once_with((70, 80))
    scene._handle_button_click.assert_called_once_with("pause")


def test_mousebuttondown_left_scene_click_not_consumed() -> None:
    """handle_mouse_click returns False → button click not dispatched."""
    scene = _make_scene(
        _homecoming_base_pending=False,
        handle_mouse_click=MagicMock(return_value=False),
    )
    dispatcher = GameSceneEventDispatcher(scene)
    dispatcher.dispatch(_mousebuttondown_event(button=1, pos=(70, 80)))

    scene._handle_button_click.assert_not_called()


def test_mousebuttondown_right_button_skips_scene_click() -> None:
    """Right button (button != 1) skips handle_mouse_click + button click."""
    scene = _make_scene()
    dispatcher = GameSceneEventDispatcher(scene)
    dispatcher.dispatch(_mousebuttondown_event(button=3, pos=(70, 80)))

    scene.handle_mouse_click.assert_not_called()
    scene._handle_button_click.assert_not_called()
    # Aim assist still ran.
    scene._aim_assist.set_raw_aim_position.assert_called_once()


def test_mousebuttondown_console_click_must_be_left_button() -> None:
    """Right button + base pending → console click not attempted (button != 1)."""
    scene = _make_scene(
        _homecoming_base_pending=True,
        _handle_base_console_click=MagicMock(return_value=True),
    )
    dispatcher = GameSceneEventDispatcher(scene)
    dispatcher.dispatch(_mousebuttondown_event(button=3, pos=(70, 80)))

    scene._handle_base_console_click.assert_not_called()
