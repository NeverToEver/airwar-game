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
