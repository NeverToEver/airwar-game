"""Project-wide pytest setup."""

import os
import tempfile

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
# Mirror the new default cache root (airwar/data/generated_assets/) but
# redirect to a per-process tempdir so tests never touch the on-disk cache.
os.environ.setdefault(
    "AIRWAR_GENERATED_ASSET_DIR",
    os.path.join(tempfile.gettempdir(), "airwar-test-data", "generated_assets"),
)


@pytest.fixture
def reset_singletons():
    """Reset all known singletons before AND after the test.

    Opt-in (autouse=False): tests that need a clean singleton state should
    declare this fixture explicitly.
    """
    from airwar.config.game_config import GameConfig
    from airwar.utils.database import UserDB

    GameConfig.reset_instance()
    UserDB.reset_instance()
    yield
    GameConfig.reset_instance()
    UserDB.reset_instance()


@pytest.fixture(autouse=True)
def _isolate_pygame_state():
    """Reset pygame after each test that touched it.

    Regression guard: ``test_tutorial_render_smoke._make_scene`` calls
    ``pygame.display.set_mode`` and renders 300+ frames, which leaves
    the SDL dummy driver in a state that segfaults the next test
    calling ``font.render`` (e.g. ``test_talent_balance_manager``).
    The fix is to fully quit pygame after each test and clear
    ``get_cjk_font``'s lru_cache so cached font objects cannot
    reference the dead SDL context. The next test that needs pygame
    initialises it lazily via ``pygame.init()`` at import time of
    the module.
    """
    yield
    try:
        import pygame

        pygame.quit()
    except Exception:  # noqa: BLE001 — SDL teardown is best-effort
        pass
    try:
        from airwar.utils.fonts import get_cjk_font, get_font_for_locale

        get_cjk_font.cache_clear()
        get_font_for_locale.cache_clear()
    except Exception:  # noqa: BLE001 — cache_clear is best-effort
        pass
    try:
        import pygame

        pygame.init()
        pygame.font.init()
    except Exception:  # noqa: BLE001 — reinit is best-effort
        pass
