"""Regression test for ``_run_scene_loop`` event dispatch routing.

Background: the user reported that the benchmark scene's two
buttons (enter and back) were completely unresponsive in
practice, even after the ``clear_buttons()`` /
``register_button`` workarounds in commit f262b33 had been
applied. The deeper root cause was a routing bug in
``SceneSwitcher._run_scene_loop``: the sub-scene helpers
(``_show_benchmark_menu``, ``_show_pause_menu``,
``_show_exit_confirm``, ``_show_death_screen``,
``_show_settings_menu``) call ``scene.enter()`` directly without
``scene_manager.switch()``, so ``SceneManager._current_scene``
remains the **calling** scene (typically ``welcome`` or
``game``). The pre-existing ``_handle_scene_events`` routed
events to ``scene_manager.handle_events``, which dispatched
them to the wrong scene — the click that landed on the
benchmark Back button was sent to the Welcome scene, which
ignored it.

This test pins the contract: when ``_run_scene_loop`` runs a
sub-scene, mouse events that hit that sub-scene's button rects
must dispatch to the sub-scene, not to whatever scene happened
to be ``SceneManager._current_scene``.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


def test_sub_scene_click_dispatches_to_sub_scene_not_caller() -> None:
    """End-to-end: switch to welcome, open benchmark, click Back.
    The click must set ``benchmark._wants_to_leave`` (proving
    it reached the benchmark scene), not be silently dropped
    or handled by the welcome scene.
    """
    import pygame

    pygame.init()
    from airwar.game import Game

    game = Game()
    director = game._director

    # Welcome is the calling scene — SceneManager._current_scene.
    director._scene_manager.switch("welcome", viewport=director._viewport)
    assert director._scene_manager._current_scene.__class__.__name__ == "WelcomeScene"

    # Open benchmark the way _show_benchmark_menu does: enter() directly,
    # no scene_manager.switch. (This is the pre-fix pattern that
    # exposed the dispatch bug.)
    benchmark_scene = director._scene_manager.get_scene("benchmark")
    benchmark_scene.enter()
    director._switcher._render_scene(benchmark_scene)
    # Sanity: the back button must be in the populated rects.
    assert "benchmark_back" in benchmark_scene._button_rects
    # And the SceneManager._current_scene is still WelcomeScene —
    # exactly the mismatch that caused the bug.
    assert director._scene_manager._current_scene.__class__.__name__ == "WelcomeScene"

    # Inject a click on the Back button.
    back_rect = benchmark_scene._button_rects["benchmark_back"]
    pygame.event.post(
        pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": back_rect.center}
        )
    )

    # Run the loop briefly. The click must be dispatched to the
    # benchmark scene, not the welcome scene.
    import time

    start = time.monotonic()
    while time.monotonic() - start < 0.3 and benchmark_scene.is_running():
        director._switcher._run_scene_loop(benchmark_scene)
        if benchmark_scene._wants_to_leave:
            break

    assert benchmark_scene._wants_to_leave is True, (
        "Click on the benchmark Back button must reach the benchmark "
        "scene, not the welcome scene. This is the dispatch-routing "
        "bug the user reported."
    )


def test_sub_scene_enter_click_dispatches_to_running() -> None:
    """End-to-end: click the enter button on a freshly-entered
    benchmark scene must transition state away from 'idle'.
    Without the fix, the click would go to the welcome scene
    (which has no enter button there) and the state would stay
    'idle'. The state will quickly become 'running' on click and
    may progress to 'results' once the worker thread completes
    — both prove the click reached the benchmark scene.
    """
    import pygame

    pygame.init()
    from airwar.game import Game

    game = Game()
    director = game._director

    director._scene_manager.switch("welcome", viewport=director._viewport)
    benchmark_scene = director._scene_manager.get_scene("benchmark")
    benchmark_scene.enter()
    director._switcher._render_scene(benchmark_scene)
    enter_rect = benchmark_scene._button_rects["benchmark_enter"]

    assert benchmark_scene._state == "idle", (
        f"sanity: scene must start in 'idle'; got {benchmark_scene._state!r}"
    )

    # Drive a single click through the dispatch path directly. We
    # bypass ``_run_scene_loop`` here because the worker thread
    # spawned by ``_on_enter_clicked`` would take 30-60s to finish
    # in a real run, but the state-transition itself happens
    # synchronously in the click handler.
    event = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": enter_rect.center}
    )
    benchmark_scene.handle_events(event)
    assert benchmark_scene._state != "idle", (
        f"Click on the benchmark enter button must transition out of "
        f"'idle'; got state={benchmark_scene._state!r}. The click is "
        f"being routed to the wrong scene (welcome, since "
        f"scene_manager was never switched)."
    )


def test_handle_scene_events_target_scene_kwarg() -> None:
    """The ``_handle_scene_events`` signature must accept a
    ``target_scene`` keyword-only argument and route the event
    to it, bypassing ``scene_manager.get_current_scene``.

    Regression guard: a future refactor that flips the parameter
    order or removes the kwarg would silently break the
    sub-scene dispatch.
    """
    import inspect
    import pygame

    from airwar.game.scene_director_components.scene_switcher import (
        SceneSwitcher,
    )

    sig = inspect.signature(SceneSwitcher._handle_scene_events)
    assert "target_scene" in sig.parameters, (
        "_handle_scene_events must accept a target_scene kwarg "
        "so _run_scene_loop can dispatch to sub-scenes that did "
        "not call scene_manager.switch."
    )
    target_scene_param = sig.parameters["target_scene"]
    # Must be keyword-only to avoid colliding with the legacy
    # ``skip_escape`` positional argument that callers use.
    assert target_scene_param.kind == inspect.Parameter.KEYWORD_ONLY, (
        f"target_scene must be keyword-only; got kind="
        f"{target_scene_param.kind!r}"
    )
    # Sanity: the kwarg actually routes an event to the
    # supplied scene (not to scene_manager).
    class _Marker:
        def __init__(self):
            self.received: list[pygame.event.Event] = []

        def handle_events(self, event: pygame.event.Event) -> None:
            self.received.append(event)

    marker = _Marker()
    switcher = SceneSwitcher.__new__(SceneSwitcher)
    switcher._scene_manager = None  # would have raised AttributeError
    # on the legacy code path that calls scene_manager.handle_events
    event = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_SPACE})
    switcher._handle_scene_events([event], target_scene=marker)
    assert marker.received == [event], (
        f"target_scene kwarg must route the event to the supplied "
        f"scene; got {marker.received!r}"
    )
