"""Tutorial scene render smoke tests.

Regression coverage for the B2 bug: a local variable named ``t`` inside
``UIRenderer.render_stage_title_card`` shadowed the module-level
``from airwar.i18n import t`` translator, raising
``TypeError: 'float' object is not callable`` once the title card
entered the fade-out phase.
"""

from __future__ import annotations

# Headless mode MUST be set before importing pygame so the dummy SDL
# video driver is selected during initialization.
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from airwar.scenes.tutorial_scene import TutorialScene

# Markers mirror the rest of the test suite.
pytestmark = pytest.mark.smoke


def _make_scene() -> TutorialScene:
    """Construct a fresh TutorialScene and run enter() so all the
    expected attributes are present (mirrors how the director wires it
    in production)."""
    pygame.init()
    pygame.font.init()
    # Init a dummy display so the scene's mouse-position query inside
    # ``enter()`` (via ``pygame.mouse.get_pos()``) doesn't fail.
    pygame.display.set_mode((1280, 720))
    scene = TutorialScene()
    scene.enter()
    return scene


def test_stage_title_card_does_not_shadow_translator() -> None:
    """Drive the stage title card through slide-in, hold, AND fade-out
    phases; the local ``t`` (time progress) must not shadow the
    ``airwar.i18n.t`` translator (would raise ``TypeError``)."""
    scene = _make_scene()
    surface = pygame.Surface((1280, 720), pygame.SRCALPHA)

    # Run for the full slide+hold+fade cycle plus a few extra frames so
    # the title card reaches (and exits) the fade-out branch.
    total = (
        scene.STAGE_CARD_SLIDE_FRAMES
        + scene.STAGE_CARD_HOLD_FRAMES
        + scene.STAGE_CARD_FADE_FRAMES
        + 5
    )
    for _ in range(total):
        scene.update()
        scene.render(surface)  # must not raise


def test_tutorial_scene_renders_multiple_frames_without_crash() -> None:
    """Broader smoke: run a few hundred tutorial frames and assert the
    scene stays renderable. Catches any later regressions of the same
    shape (translator shadowing by future local ``t`` variables)."""
    scene = _make_scene()
    surface = pygame.Surface((1280, 720), pygame.SRCALPHA)
    for _ in range(300):
        scene.update()
        scene.render(surface)
