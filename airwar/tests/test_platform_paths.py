"""Tests for ``airwar.utils.platform_paths`` — covers Windows / macOS / Linux
fallback chains, empty-string env-var handling, and the Cygwin/MSYS branch
that was previously misrouted to the Linux XDG path."""

from __future__ import annotations

import os
import sys

import pytest

from airwar.utils import platform_paths
from airwar.utils.platform_paths import APP_DIR_NAME


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip every override the function consults so each test starts blank."""
    for var in ("AIRWAR_DATA_DIR", "AIRWAR_CACHE_DIR", "APPDATA", "LOCALAPPDATA", "XDG_DATA_HOME", "XDG_CACHE_HOME"):
        monkeypatch.delenv(var, raising=False)


@pytest.mark.parametrize("platform", ["win32", "cygwin", "msys"])
def test_windows_platforms_use_appdata(monkeypatch: pytest.MonkeyPatch, clean_env, platform: str) -> None:
    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.setenv("APPDATA", r"C:\Users\Luna\AppData\Roaming")
    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\Luna\AppData\Local")

    assert platform_paths.user_data_dir() == os.path.join(
        r"C:\Users\Luna\AppData\Roaming", APP_DIR_NAME
    )
    assert platform_paths.user_cache_dir() == os.path.join(
        r"C:\Users\Luna\AppData\Local", APP_DIR_NAME, "Cache"
    )


@pytest.mark.parametrize("platform", ["win32", "cygwin", "msys"])
def test_windows_platforms_fall_back_when_appdata_empty(
    monkeypatch: pytest.MonkeyPatch, clean_env, platform: str, tmp_path
) -> None:
    """An empty APPDATA / LOCALAPPDATA string must fall back to the Windows
    home layout — never the Linux XDG path."""
    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.setenv("APPDATA", "")
    monkeypatch.setenv("LOCALAPPDATA", "")
    monkeypatch.setattr(platform_paths, "_home", lambda: str(tmp_path))

    data = platform_paths.user_data_dir()
    cache = platform_paths.user_cache_dir()

    assert data == os.path.join(str(tmp_path), "AppData", "Roaming", APP_DIR_NAME)
    assert cache == os.path.join(str(tmp_path), "AppData", "Local", APP_DIR_NAME, "Cache")
    # Sanity: the result must NOT look like a Linux XDG path.
    assert ".local" not in data
    assert ".cache" not in cache


def test_darwin_uses_library_application_support(monkeypatch: pytest.MonkeyPatch, clean_env, tmp_path) -> None:
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(platform_paths, "_home", lambda: str(tmp_path))

    assert platform_paths.user_data_dir() == os.path.join(
        str(tmp_path), "Library", "Application Support", APP_DIR_NAME
    )
    assert platform_paths.user_cache_dir() == os.path.join(
        str(tmp_path), "Library", "Caches", APP_DIR_NAME
    )


def test_linux_uses_xdg_when_set(monkeypatch: pytest.MonkeyPatch, clean_env, tmp_path) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg-data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg-cache"))

    assert platform_paths.user_data_dir() == os.path.join(str(tmp_path / "xdg-data"), APP_DIR_NAME)
    assert platform_paths.user_cache_dir() == os.path.join(str(tmp_path / "xdg-cache"), APP_DIR_NAME)


def test_linux_falls_back_to_dot_local_when_xdg_unset(
    monkeypatch: pytest.MonkeyPatch, clean_env, tmp_path
) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(platform_paths, "_home", lambda: str(tmp_path))

    assert platform_paths.user_data_dir() == os.path.join(str(tmp_path), ".local", "share", APP_DIR_NAME)
    assert platform_paths.user_cache_dir() == os.path.join(str(tmp_path), ".cache", APP_DIR_NAME)


def test_linux_falls_back_when_xdg_empty(monkeypatch: pytest.MonkeyPatch, clean_env, tmp_path) -> None:
    """Mirror of the Windows test: an explicitly empty XDG var must fall back."""
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_DATA_HOME", "")
    monkeypatch.setenv("XDG_CACHE_HOME", "")
    monkeypatch.setattr(platform_paths, "_home", lambda: str(tmp_path))

    assert platform_paths.user_data_dir() == os.path.join(str(tmp_path), ".local", "share", APP_DIR_NAME)
    assert platform_paths.user_cache_dir() == os.path.join(str(tmp_path), ".cache", APP_DIR_NAME)


def test_airwar_data_dir_override_takes_precedence(monkeypatch: pytest.MonkeyPatch, clean_env) -> None:
    monkeypatch.setenv("AIRWAR_DATA_DIR", "/custom/data")
    assert platform_paths.user_data_dir() == "/custom/data"


def test_airwar_cache_dir_override_takes_precedence(monkeypatch: pytest.MonkeyPatch, clean_env) -> None:
    monkeypatch.setenv("AIRWAR_CACHE_DIR", "/custom/cache")
    assert platform_paths.user_cache_dir() == "/custom/cache"
