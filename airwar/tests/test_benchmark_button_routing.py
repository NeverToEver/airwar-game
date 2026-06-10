"""Regression test for the BenchmarkScene button-routing bug.

Background: a user reported that the benchmark scene's two
buttons (enter and back) were completely unresponsive. The
root cause was a frame-ordering bug in
``SceneSwitcher._run_scene_loop``:

    poll_events  →  dispatch  →  update  →  render

The dispatch happens BEFORE the first render, but
``BenchmarkScene.enter()`` calls ``self.clear_buttons()`` (to
reset state from a previous visit). With empty ``_button_rects``,
``_get_button_at_pos`` returns None, the click is silently
dropped, and the scene appears frozen.

This test pins the contract: by the time ``enter()`` returns,
``_button_rects`` must contain both idle-state buttons, so the
first dispatched click has real targets.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


def test_benchmark_enter_populates_button_rects() -> None:
    """``enter()`` must register both buttons before returning, so
    the first click dispatched by ``SceneSwitcher._run_scene_loop``
    has a real target. The frame order is
    ``poll -> dispatch -> update -> render``; without this, the
    dispatch runs against an empty ``_button_rects`` dict and the
    click is silently dropped.
    """
    import pygame

    pygame.init()
    from airwar.game import Game

    game = Game()
    game._director._scene_manager.switch("benchmark")
    scene = game._director._scene_manager._current_scene
    scene.enter()  # this is the exact call SiteSwitcher does

    # After enter(), the buttons must already be registered. The
    # first render (a few lines later in _run_scene_loop) will
    # re-register them with the real surface size, but the click
    # that arrives *before* that first render needs a target.
    assert scene.ENTER_BUTTON in scene._button_rects, (
        f"{scene.ENTER_BUTTON!r} must be in _button_rects immediately "
        f"after enter(); otherwise the first click is dropped. "
        f"Got: {list(scene._button_rects.keys())}"
    )
    assert scene.BACK_BUTTON in scene._button_rects, (
        f"{scene.BACK_BUTTON!r} must be in _button_rects immediately "
        f"after enter(); otherwise the Back button never responds."
    )


def test_benchmark_enter_click_dispatches_to_running() -> None:
    """End-to-end: after enter(), a MOUSEBUTTONDOWN on the enter
    button must transition state to "running" — the same path the
    user takes when they click the button. This is the original
    bug, locked in a single test."""
    import pygame

    pygame.init()
    from airwar.game import Game

    game = Game()
    game._director._scene_manager.switch("benchmark")
    scene = game._director._scene_manager._current_scene
    scene.enter()
    assert scene._state == "idle"

    enter_rect = scene._button_rects[scene.ENTER_BUTTON]
    click = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN,
        {"button": 1, "pos": enter_rect.center},
    )
    scene.handle_events(click)
    assert scene._state == "running", (
        f"Click on the enter button must transition to running; "
        f"got state={scene._state!r}. This is the user-reported "
        f"'button does nothing' bug."
    )


def test_benchmark_back_click_sets_wants_to_leave() -> None:
    """End-to-end: the Back button must set ``_wants_to_leave`` so
    ``is_ready()`` returns True and the scene-switcher can route
    the user back to the welcome screen."""
    import pygame

    pygame.init()
    from airwar.game import Game

    game = Game()
    game._director._scene_manager.switch("benchmark")
    scene = game._director._scene_manager._current_scene
    scene.enter()
    scene._wants_to_leave = False  # reset from any prior visit

    back_rect = scene._button_rects[scene.BACK_BUTTON]
    click = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN,
        {"button": 1, "pos": back_rect.center},
    )
    scene.handle_events(click)
    assert scene._wants_to_leave is True, (
        f"Click on the Back button must set _wants_to_leave=True; "
        f"got _wants_to_leave={scene._wants_to_leave!r}. Without "
        f"this, the user is stuck on the benchmark scene."
    )
    assert scene.is_ready() is True
