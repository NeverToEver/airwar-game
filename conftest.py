"""Project-wide pytest setup."""

import os
import tempfile


os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("AIRWAR_GENERATED_ASSET_DIR", os.path.join(tempfile.gettempdir(), "airwar-test-generated-assets"))
