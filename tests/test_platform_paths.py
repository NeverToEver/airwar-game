"""Deployment robustness: runtime directories must resolve outside the
install tree, so the game works when extracted/placed at any path —
including read-only locations (Program Files, /opt, site-packages,
PyInstaller ``_internal``).
"""

import os

from airwar.utils import platform_paths

_PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(platform_paths.__file__)))


def _clear_overrides(monkeypatch):
    for var in (
        "AIRWAR_DATA_DIR",
        "AIRWAR_CACHE_DIR",
        "AIRWAR_GENERATED_ASSET_DIR",
        "XDG_DATA_HOME",
        "XDG_CACHE_HOME",
    ):
        monkeypatch.delenv(var, raising=False)


def test_runtime_dirs_resolve_outside_install_tree(monkeypatch):
    _clear_overrides(monkeypatch)
    for path in (
        platform_paths.user_data_dir(),
        platform_paths.user_cache_dir(),
        platform_paths.generated_asset_cache_dir(),
    ):
        assert not os.path.abspath(path).startswith(_PACKAGE_DIR + os.sep), path


def test_generated_asset_cache_defaults_to_user_cache(monkeypatch):
    _clear_overrides(monkeypatch)
    monkeypatch.setenv("AIRWAR_CACHE_DIR", "/tmp/airwar-test-cache")
    assert platform_paths.generated_asset_cache_dir() == os.path.join("/tmp/airwar-test-cache", "generated_assets")


def test_generated_asset_cache_env_override(monkeypatch, tmp_path):
    custom = str(tmp_path / "custom-assets")
    monkeypatch.setenv("AIRWAR_GENERATED_ASSET_DIR", custom)
    assert platform_paths.generated_asset_cache_dir() == custom
