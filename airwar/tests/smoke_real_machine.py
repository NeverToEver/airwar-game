"""Real-machine smoke test for airwar-game.

Boots a real SDL display, instantiates ``Game``, drives the main loop for a
short bounded window with synthetic pygame events, and asserts that:

- the game constructs without error,
- the main loop runs for the full duration (i.e. no immediate crash or
  infinite-loop hang),
- synthetic events are dispatched into the SDL queue,
- the director reaches a clean shutdown state.

The smoke test runs for ``AIRWAR_SMOKE_DURATION`` seconds (default 3.0;
target production value 60) and is automatically skipped in CI where
``SDL_VIDEODRIVER=dummy`` is forced by the project ``conftest.py``.

Use ``./scripts/smoke_real.sh`` to launch on a developer machine.
"""

from __future__ import annotations

import os
import threading
import time

import pytest

# Marking is duplicated at module level AND on the test function so that
# `pytest --markers` reports them even if individual tests are filtered out.
pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        os.environ.get("SDL_VIDEODRIVER") == "dummy",
        reason="smoke_real_machine requires a real SDL display (not the dummy driver)",
    ),
]


def _duration() -> float:
    """Smoke test wall-clock budget in seconds. Override via env var."""
    try:
        return float(os.environ.get("AIRWAR_SMOKE_DURATION", "3.0"))
    except (TypeError, ValueError):
        return 3.0


def test_game_runs_for_short_window_on_real_display() -> None:
    """Run Game on a real display for a bounded window; assert clean shutdown.

    Verifies:
    1. No uncaught exceptions during the run.
    2. Main loop ran for the expected duration (not a hang or instant exit).
    3. Synthetic events reached the SDL queue.
    4. The director reached a clean ``_running=False`` state.
    5. The scene manager still has registered scenes after shutdown.
    """
    # Imports kept local so the skipif decorator can short-circuit the
    # module before pulling in pygame + the full game stack.
    import pygame

    from airwar.game import Game

    duration = _duration()
    # Reserve a sliver of the budget for shutdown / event-feed teardown.
    feed_budget = max(0.2, duration - 0.4)

    exceptions: list[BaseException] = []
    events_posted = 0
    feed_stop = threading.Event()
    started_monotonic = time.monotonic()

    def _feed_events() -> None:
        """Background thread: post synthetic events into the SDL queue.

        MOUSEMOTION exercises the aim-assist / crosshair path; KEYDOWN/KEYUP
        for ``K_d`` exercises the movement path. Auto-fire is on by default
        in the game, so bullets are emitted whenever the ship is alive.
        """
        nonlocal events_posted
        frame = 0
        deadline = started_monotonic + feed_budget
        while not feed_stop.is_set() and time.monotonic() < deadline:
            x = 640 + (frame * 7) % 800
            y = 360 + (frame * 5) % 400
            pygame.event.post(
                pygame.event.Event(
                    pygame.MOUSEMOTION,
                    {"pos": (x, y), "buttons": (0, 0, 0), "rel": (7, 5)},
                )
            )
            events_posted += 1
            if frame % 30 == 0:
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_d}))
            if frame % 30 == 15:
                pygame.event.post(pygame.event.Event(pygame.KEYUP, {"key": pygame.K_d}))
            frame += 1
            time.sleep(0.016)  # ~60 FPS pacing

    # Build the real game. Will raise on systems without an SDL display.
    game = Game()

    # Bypass the welcome flow so the director enters the game scene directly.
    # The original welcome flow blocks on user input — we short-circuit to
    # (ready=True, save_data=None) with a fixed user + difficulty.
    def _fake_welcome_flow() -> tuple:
        game._director._current_user = "smoketest"
        game._director._selected_difficulty = "medium"
        return (True, None)

    game._director._run_welcome_flow = _fake_welcome_flow

    # Bound the test: schedule director.stop() after `duration` seconds.
    stop_timer = threading.Timer(duration, game._director.stop)
    stop_timer.daemon = True

    feed_thread = threading.Thread(target=_feed_events, daemon=True)

    elapsed = 0.0
    try:
        stop_timer.start()
        feed_thread.start()
        game.run()  # blocks until director._running flips to False
    except Exception as exc:  # surface any uncaught loop error
        exceptions.append(exc)
    finally:
        feed_stop.set()
        stop_timer.cancel()
        feed_thread.join(timeout=2.0)
        elapsed = time.monotonic() - started_monotonic

    # Assertion 1: no uncaught exceptions during the run.
    assert not exceptions, f"Exceptions during smoke run: {exceptions!r}"

    # Assertion 2: the main loop actually ran (not blocked or hung).
    # Allow a small grace window on the lower bound; the upper bound catches
    # infinite-loop regressions (a 3s budget should not exceed ~13s).
    assert elapsed >= duration - 0.5, (
        f"Game loop returned too early: {elapsed:.2f}s (expected ~{duration:.2f}s)"
    )
    assert elapsed < duration + 10.0, (
        f"Game loop took too long: {elapsed:.2f}s (expected ~{duration:.2f}s)"
    )

    # Assertion 3: synthetic events were actually delivered to the queue.
    assert events_posted > 0, "No synthetic events were posted to the SDL queue"

    # Assertion 4: director reached a clean shutdown state.
    assert game._director._running is False, "Director is still running after stop"

    # Assertion 5: scene manager survived the run with registered scenes.
    scene_manager = game._director._scene_manager
    assert scene_manager is not None
    assert scene_manager.get_scene("game") is not None
    assert scene_manager.get_scene("welcome") is not None
