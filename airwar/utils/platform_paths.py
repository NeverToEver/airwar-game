"""Platform-specific runtime directories for AirWar data and caches."""

from __future__ import annotations

import os
import sys

APP_DIR_NAME = "airwar"

# Platforms that use the Windows-style "AppData" / "APPDATA" layout. Cygwin
# and MSYS report `sys.platform == "cygwin"` / `"msys"`, but their users still
# expect the Windows convention (and `LOCALAPPDATA` / `APPDATA` are usually
# exported correctly by the cygwin/msys runtime).
_WINDOWS_PLATFORMS = frozenset({"win32", "cygwin", "msys"})


def _home() -> str:
    return os.path.expanduser("~")


def user_data_dir() -> str:
    """Return the directory for persistent user data such as accounts and saves."""
    override = os.environ.get("AIRWAR_DATA_DIR")
    if override:
        return os.path.abspath(os.path.expanduser(override))

    if sys.platform in _WINDOWS_PLATFORMS:
        # An empty APPDATA ("" or unset) must fall back to the Windows home
        # layout — NOT the Linux XDG path. Using `or` would work for None but
        # conflates intent; an explicit `if` keeps the empty-string behavior
        # clear.
        appdata = os.environ.get("APPDATA")
        root = appdata if appdata else os.path.join(_home(), "AppData", "Roaming")
        return os.path.join(root, APP_DIR_NAME)
    if sys.platform == "darwin":
        return os.path.join(_home(), "Library", "Application Support", APP_DIR_NAME)

    xdg = os.environ.get("XDG_DATA_HOME")
    root = xdg if xdg else os.path.join(_home(), ".local", "share")
    return os.path.join(root, APP_DIR_NAME)


def user_cache_dir() -> str:
    """Return the directory for disposable runtime caches."""
    override = os.environ.get("AIRWAR_CACHE_DIR")
    if override:
        return os.path.abspath(os.path.expanduser(override))

    if sys.platform in _WINDOWS_PLATFORMS:
        localappdata = os.environ.get("LOCALAPPDATA")
        root = localappdata if localappdata else os.path.join(_home(), "AppData", "Local")
        return os.path.join(root, APP_DIR_NAME, "Cache")
    if sys.platform == "darwin":
        return os.path.join(_home(), "Library", "Caches", APP_DIR_NAME)

    xdg = os.environ.get("XDG_CACHE_HOME")
    root = xdg if xdg else os.path.join(_home(), ".cache")
    return os.path.join(root, APP_DIR_NAME)


def generated_asset_cache_dir() -> str:
    """Return the generated image asset cache directory.

    Defaults to the platform user cache so the game also works from
    read-only install locations (Program Files, /opt, pip site-packages,
    PyInstaller ``_internal``). ``AIRWAR_GENERATED_ASSET_DIR`` overrides.
    """
    override = os.environ.get("AIRWAR_GENERATED_ASSET_DIR")
    if override:
        return os.path.abspath(os.path.expanduser(override))
    return os.path.join(user_cache_dir(), "generated_assets")


def redact_home_path(path: str) -> str:
    """Return ``path`` with the user's home directory replaced by ``~``.

    This keeps logs useful while avoiding accidental leakage of the system
    username in shared crash reports or build logs.
    """
    home = os.path.expanduser("~")
    if not home or home == "~":
        return path
    # Normalise separators so Windows paths are also redacted.
    normalised = path.replace("\\", "/")
    home_normalised = home.replace("\\", "/")
    if not home_normalised.endswith("/"):
        home_normalised += "/"
    if normalised.startswith(home_normalised) or normalised == home_normalised.rstrip("/"):
        return "~" + normalised[len(home_normalised.rstrip("/")) :]
    return path
