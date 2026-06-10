"""Regression test for the ``run_welcome_flow`` re-entry bug.

Background: a user reported that ``python3 main.py`` crashed on
startup with::

    SceneAlreadyActiveError: Scene 'welcome' is already active

The crash happened because ``run_welcome_flow`` opened with
``self._scene_manager.switch("welcome", ...)`` INSIDE a
``while`` loop. The first iteration switched successfully;
subsequent iterations (the user opens the tutorial or benchmark
sub-scene, plays through it, the sub-scene flow returns via
``continue``) re-executed the same ``switch("welcome")`` and
hit ``SceneAlreadyActiveError`` because ``SceneManager`` now
refuses to switch to a scene that is already active.

The fix moves the initial switch BEFORE the loop, so the scene
loop is the only thing that re-runs each iteration. The
sub-scene flows (tutorial / settings / benchmark) continue to
manage their own enter/exit lifecycle, so the active scene
during their run is the sub-scene, but the switcher doesn't
need to keep telling the scene manager about it.

This test pins the contract: ``run_welcome_flow`` must
``switch("welcome")`` exactly once, before the loop.
"""

from __future__ import annotations

import inspect

import pygame

from airwar.game.scene_director_components.scene_switcher import (
    SceneSwitcher,
)


def test_run_welcome_flow_switches_to_welcome_before_loop() -> None:
    """The first ``scene_manager.switch`` call in
    ``run_welcome_flow`` must happen at most once per call to
    the method (i.e. before the ``while`` loop, not inside it).
    Otherwise the second iteration raises
    ``SceneAlreadyActiveError``."""
    pygame.init()
    from unittest.mock import MagicMock

    from airwar.game import Game

    game = Game()
    switcher = game._director._switcher

    # Wrap the scene manager to count switch calls.
    real_switch = switcher._scene_manager.switch
    switch_calls: list[str] = []

    def counting_switch(name: str, **kwargs) -> None:
        switch_calls.append(name)
        return real_switch(name, **kwargs)

    switcher._scene_manager.switch = counting_switch

    # Drive the welcome flow to completion by making the scene
    # immediately report ``is_ready() == True`` so the function
    # returns on its first iteration. This is enough to exercise
    # the "switch exactly once" contract.
    welcome = switcher._scene_manager.get_scene("welcome")
    welcome.is_ready = lambda: True
    welcome.get_username = lambda: "pilot"
    welcome.get_difficulty = lambda: "medium"

    # Stub out the rest of the welcome-flow dependencies.
    director = game._director
    director._current_user = None
    director._selected_difficulty = None
    director._mothership_dock_count = 0
    director._achievement_registry = None
    director._load_user_settings = MagicMock()
    director._create_achievement_registry = MagicMock()
    director._check_and_get_saved_game = MagicMock(return_value=None)

    # Make the scene loop exit immediately (otherwise the welcome
    # scene will sit there waiting for events until something
    # closes the window).
    welcome.is_running = lambda: False

    switcher.run_welcome_flow()

    assert "welcome" in switch_calls, (
        f"run_welcome_flow must switch to 'welcome' at least once; "
        f"got {switch_calls!r}"
    )
    assert switch_calls.count("welcome") == 1, (
        f"run_welcome_flow must call scene_manager.switch('welcome') "
        f"exactly once before the loop, not inside it. Got "
        f"{switch_calls.count('welcome')} 'welcome' switches in "
        f"{switch_calls!r}. The 'SceneAlreadyActiveError' crash "
        f"originates from the second iteration re-calling switch."
    )


def test_run_welcome_flow_source_uses_one_switch_call() -> None:
    """Static check: the source of ``run_welcome_flow`` must
    contain exactly one ``scene_manager.switch("welcome"`` call
    site. A future refactor that re-introduces a second
    ``switch`` call would silently re-introduce the crash."""
    source = inspect.getsource(SceneSwitcher.run_welcome_flow)
    # Look for the qualified call site ``scene_manager.switch("welcome"``;
    # the bare ``switch("welcome"`` form never appears in this method
    # (it is always called as ``self._scene_manager.switch(...)``).
    switch_count = source.count('scene_manager.switch("welcome"')
    assert switch_count == 1, (
        f"run_welcome_flow must call scene_manager.switch(\"welcome\") "
        f"exactly once; got {switch_count} occurrences. The second "
        f"iteration of the loop re-executed the switch and raised "
        f"SceneAlreadyActiveError. If you added a new switch call, "
        f"guard it with ``if not is_current:`` or move it out of "
        f"the loop."
    )
