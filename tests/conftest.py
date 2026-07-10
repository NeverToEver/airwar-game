"""Shared pytest configuration for Air War architecture tests."""

import os

import pygame
import pytest


@pytest.fixture(scope="session", autouse=True)
def _init_pygame():
    """Initialize pygame once for the test session.

    Uses the dummy video driver when no display is available so that
    Surface-based tests can run headlessly. Audio failures are ignored.
    """
    if os.environ.get("SDL_VIDEODRIVER") is None and not os.environ.get("DISPLAY"):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    yield
    pygame.quit()
