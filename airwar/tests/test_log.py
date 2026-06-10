"""Tests for ``airwar._log`` -- logging configuration and cache resolution."""

from __future__ import annotations

import logging
import logging.handlers

import pytest

from airwar import _log
from airwar._log import LOGGER_NAME, get_cache_dir, setup_logging


@pytest.fixture
def redirect_cache(tmp_path, monkeypatch):
    """Redirect the airwar cache to a per-test temp directory."""
    monkeypatch.setenv("AIRWAR_CACHE_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture(autouse=True)
def _reset_logging():
    """Reset the airwar logger so dictConfig side effects don't leak across tests."""
    logger = logging.getLogger(LOGGER_NAME)
    saved = (list(logger.handlers), logger.propagate, logger.level, logger.disabled)
    yield
    logger.handlers, logger.propagate, logger.level, logger.disabled = saved


class TestGetCacheDir:
    def test_env_override_wins(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AIRWAR_CACHE_DIR", str(tmp_path / "custom"))
        assert get_cache_dir() == tmp_path / "custom"

    def test_xdg_cache_home(self, tmp_path, monkeypatch):
        monkeypatch.delenv("AIRWAR_CACHE_DIR", raising=False)
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
        assert get_cache_dir() == tmp_path / "airwar"

    def test_default_posix(self, tmp_path, monkeypatch):
        monkeypatch.delenv("AIRWAR_CACHE_DIR", raising=False)
        monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))
        assert get_cache_dir() == tmp_path / ".cache" / "airwar"


class TestSetupLogging:
    def test_info_mode_creates_console_handler_only(self, redirect_cache):
        setup_logging(debug=False)
        logger = logging.getLogger(LOGGER_NAME)
        handler_classes = [type(h).__name__ for h in logger.handlers]
        assert "StreamHandler" in handler_classes
        assert "FileHandler" not in handler_classes
        assert not (redirect_cache / "airwar.log").exists()

    def test_debug_mode_writes_file(self, redirect_cache):
        setup_logging(debug=True)
        logger = logging.getLogger(LOGGER_NAME)
        handler_classes = [type(h).__name__ for h in logger.handlers]
        assert "StreamHandler" in handler_classes
        assert "FileHandler" in handler_classes
        log_path = redirect_cache / "airwar.log"
        assert log_path.exists()

        logger.debug("hello from test")
        for handler in logger.handlers:
            handler.flush()
        contents = log_path.read_text(encoding="utf-8")
        assert "hello from test" in contents

    def test_debug_mode_creates_cache_dir(self, tmp_path, monkeypatch):
        target = tmp_path / "deep" / "nested" / "cache"
        assert not target.exists()
        monkeypatch.setenv("AIRWAR_CACHE_DIR", str(target))
        setup_logging(debug=True)
        assert target.is_dir()
        assert (target / "airwar.log").exists()

    def test_debug_logging_emits_debug_records(self, redirect_cache):
        setup_logging(debug=True)
        logger = logging.getLogger(LOGGER_NAME)
        logger.debug("diagnostic message")
        for handler in logger.handlers:
            handler.flush()
        log_path = redirect_cache / "airwar.log"
        assert "diagnostic message" in log_path.read_text(encoding="utf-8")

    def test_info_mode_suppresses_debug(self, redirect_cache):
        setup_logging(debug=False)
        logger = logging.getLogger(LOGGER_NAME)
        # Console handler is at INFO; debug records should be filtered out.
        console = next(
            h for h in logger.handlers if type(h).__name__ == "StreamHandler"
        )
        assert console.level == logging.INFO
        assert logger.getEffectiveLevel() == logging.INFO

    def test_idempotent(self, redirect_cache):
        setup_logging(debug=True)
        first_count = len(logging.getLogger(LOGGER_NAME).handlers)
        setup_logging(debug=True)
        second_count = len(logging.getLogger(LOGGER_NAME).handlers)
        # dictConfig replaces handlers, so count should not grow on repeat calls.
        assert first_count == second_count

    def test_unwritable_cache_falls_back_to_console(self, tmp_path, monkeypatch):
        # Point the cache at a path that cannot be created.
        impossible = tmp_path / "file" / "airwar.log"
        assert impossible.exists() is False
        # A path whose parent is an existing file -- mkdir will fail.
        blocker = tmp_path / "blocker"
        blocker.write_text("not a directory")
        monkeypatch.setenv("AIRWAR_CACHE_DIR", str(blocker / "nested"))
        setup_logging(debug=True)
        # No exception is raised, only console handler installed.
        handler_classes = [
            type(h).__name__ for h in logging.getLogger(LOGGER_NAME).handlers
        ]
        assert "StreamHandler" in handler_classes
        assert "FileHandler" not in handler_classes


class TestLogModule:
    def test_logger_name(self):
        assert LOGGER_NAME == "airwar"

    def test_module_exports(self):
        for name in ("setup_logging", "crash_dump", "install_crash_hook", "get_cache_dir"):
            assert hasattr(_log, name), f"missing export: {name}"
