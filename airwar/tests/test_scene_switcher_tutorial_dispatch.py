"""Regression test for the SceneSwitcher tutorial-flow dispatch.

Background: the welcome scene requests the tutorial via
``welcome.should_open_tutorial()`` returning True. The switcher
must then delegate to ``self.run_tutorial_flow()``. A previous
typo ``self._run_tutorial_flow()`` (with leading underscore) caused
an ``AttributeError`` the moment any user clicked the tutorial
button on the welcome screen. The dummy SDL driver never reached
this branch during tests, so the typo stayed hidden.

This test pins the public method name ``run_tutorial_flow`` so a
future rename cannot silently break the dispatch from
``run_welcome_flow`` again.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


def test_scene_switcher_has_public_run_tutorial_flow() -> None:
    """The dispatcher in ``run_welcome_flow`` must be able to call
    ``self.run_tutorial_flow()`` (no leading underscore)."""
    from airwar.game.scene_director_components.scene_switcher import (
        SceneSwitcher,
    )

    assert hasattr(SceneSwitcher, "run_tutorial_flow"), (
        "SceneSwitcher.run_tutorial_flow is the public method the "
        "welcome-flow dispatcher calls. If you renamed it, update "
        "the dispatcher in run_welcome_flow too."
    )
    # Pin the absence of the typo'd alias that the bug introduced.
    assert not hasattr(SceneSwitcher, "_run_tutorial_flow"), (
        "SceneSwitcher must not have a private ``_run_tutorial_flow`` "
        "alias — the typo'd name caused the welcome -> tutorial "
        "dispatch to AttributeError on first user click."
    )


def test_welcome_flow_dispatch_uses_public_method_name() -> None:
    """The source of ``run_welcome_flow`` must reference the public
    ``run_tutorial_flow`` (no underscore) when dispatching to the
    tutorial."""
    import inspect

    from airwar.game.scene_director_components.scene_switcher import (
        SceneSwitcher,
    )

    source = inspect.getsource(SceneSwitcher.run_welcome_flow)
    assert "self.run_tutorial_flow()" in source, (
        "run_welcome_flow must dispatch to self.run_tutorial_flow() — "
        "the previous typo used self._run_tutorial_flow() (with a "
        "leading underscore) and crashed the moment the user clicked "
        "the tutorial button on the welcome screen."
    )
    assert "self._run_tutorial_flow()" not in source, (
        "Do not reintroduce the typo'd self._run_tutorial_flow() "
        "call — it references a non-existent method and crashes."
    )


def test_welcome_scene_should_open_tutorial_hook() -> None:
    """The welcome scene must expose the hook the switcher checks.

    The switcher dispatches on
    ``hasattr(welcome, 'should_open_tutorial') and welcome.should_open_tutorial()``,
    so the welcome scene must implement the hook. If the hook is
    removed, the test fails fast with a clear message rather than
    failing later inside the switcher.
    """
    from airwar.scenes.welcome_scene import WelcomeScene

    assert hasattr(WelcomeScene, "should_open_tutorial")
    scene = WelcomeScene.__new__(WelcomeScene)  # bypass __init__ to keep
    # the test hermetic; only the attribute contract matters here.
    scene.tutorial_requested = False
    assert scene.should_open_tutorial() is False
    scene.tutorial_requested = True
    assert scene.should_open_tutorial() is True
