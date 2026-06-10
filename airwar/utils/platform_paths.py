"""Platform-specific runtime directories for AirWar data and caches."""

from __future__ import annotations

import os
import sys

APP_DIR_NAME = "airwar"

# Default location for generated sprite/font/boss image caches, co-located with
# the package. The directory is git-ignored (see top-level .gitignore).
_PACKAGE_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
)


def _home() -> str:
    return os.path.expanduser("~")


def user_data_dir() -> str:
    """Return the directory for persistent user data such as accounts and saves."""
    override = os.environ.get("AIRWAR_DATA_DIR")
    if override:
        return os.path.abspath(os.path.expanduser(override))

    if sys.platform == "win32":
        root = os.environ.get("APPDATA") or os.path.join(_home(), "AppData", "Roaming")
        return os.path.join(root, APP_DIR_NAME)
    if sys.platform == "darwin":
        return os.path.join(_home(), "Library", "Application Support", APP_DIR_NAME)

    root = os.environ.get("XDG_DATA_HOME") or os.path.join(_home(), ".local", "share")
    return os.path.join(root, APP_DIR_NAME)


def user_cache_dir() -> str:
    """Return the directory for disposable runtime caches."""
    override = os.environ.get("AIRWAR_CACHE_DIR")
    if override:
        return os.path.abspath(os.path.expanduser(override))

    if sys.platform == "win32":
        root = os.environ.get("LOCALAPPDATA") or os.path.join(_home(), "AppData", "Local")
        return os.path.join(root, APP_DIR_NAME, "Cache")
    if sys.platform == "darwin":
        return os.path.join(_home(), "Library", "Caches", APP_DIR_NAME)

    root = os.environ.get("XDG_CACHE_HOME") or os.path.join(_home(), ".cache")
    return os.path.join(root, APP_DIR_NAME)


def generated_asset_cache_dir() -> str:
    """Return the generated image asset cache directory."""
    override = os.environ.get("AIRWAR_GENERATED_ASSET_DIR")
    if override:
        return os.path.abspath(os.path.expanduser(override))
    return os.path.join(_PACKAGE_DATA_DIR, "generated_assets")
