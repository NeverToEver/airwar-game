"""Project-wide pytest setup."""

import os
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
# Mirror the new default cache root (airwar/data/generated_assets/) but
# redirect to a per-process tempdir so tests never touch the on-disk cache.
os.environ.setdefault(
    "AIRWAR_GENERATED_ASSET_DIR",
    os.path.join(tempfile.gettempdir(), "airwar-test-data", "generated_assets"),
)
