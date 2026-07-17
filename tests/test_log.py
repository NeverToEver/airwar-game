"""Tests for the centralized logging / crash-dump wiring (airwar._log)."""

from __future__ import annotations

import json
import logging
import sys

import pytest

from airwar import _log


@pytest.fixture()
def log_env(tmp_path, monkeypatch):
    """Point the cache dir at a tmp path and restore mutated global state."""
    monkeypatch.setenv("AIRWAR_CACHE_DIR", str(tmp_path))

    root = logging.getLogger()
    airwar_logger = logging.getLogger(_log.LOGGER_NAME)
    saved_root_handlers = list(root.handlers)
    saved_root_level = root.level
    saved_airwar_handlers = list(airwar_logger.handlers)
    saved_airwar_level = airwar_logger.level
    saved_airwar_propagate = airwar_logger.propagate
    saved_excepthook = sys.excepthook
    saved_providers = list(_log._CRASH_CONTEXT_PROVIDERS)

    yield tmp_path

    for handler in list(root.handlers):
        root.removeHandler(handler)
        if handler not in saved_root_handlers:
            handler.close()
    for handler in saved_root_handlers:
        root.addHandler(handler)
    root.level = saved_root_level

    for handler in list(airwar_logger.handlers):
        airwar_logger.removeHandler(handler)
        if handler not in saved_airwar_handlers:
            handler.close()
    for handler in saved_airwar_handlers:
        airwar_logger.addHandler(handler)
    airwar_logger.level = saved_airwar_level
    airwar_logger.propagate = saved_airwar_propagate

    sys.excepthook = saved_excepthook
    _log._CRASH_CONTEXT_PROVIDERS[:] = saved_providers


def _read_log(log_path) -> str:
    for handler in logging.getLogger().handlers:
        handler.flush()
    return log_path.read_text(encoding="utf-8")


class TestSetupLogging:
    def test_file_handler_installed_without_debug(self, log_env):
        _log.setup_logging(debug=False)

        log_path = _log.get_log_file_path()
        assert log_path.parent == log_env
        logging.getLogger(_log.LOGGER_NAME).info("hello-airwar")

        assert "hello-airwar" in _read_log(log_path)

    def test_stray_class_named_logger_reaches_file(self, log_env):
        """Regression: loggers like ``SceneDirector`` used to propagate to a
        handler-less root, so frame errors never reached the log file."""
        _log.setup_logging(debug=False)

        logging.getLogger("SceneDirector").error("boom-stray-logger")

        assert "boom-stray-logger" in _read_log(_log.get_log_file_path())

    def test_debug_records_gated_by_flag(self, log_env):
        _log.setup_logging(debug=False)
        logging.getLogger(_log.LOGGER_NAME).debug("hidden-debug")
        assert "hidden-debug" not in _read_log(_log.get_log_file_path())

        _log.setup_logging(debug=True)
        logging.getLogger("airwar.SceneDirector").debug("visible-debug")
        assert "visible-debug" in _read_log(_log.get_log_file_path())

    def test_idempotent_single_file_handler(self, log_env):
        _log.setup_logging(debug=False)
        _log.setup_logging(debug=False)

        file_handlers = [h for h in logging.getLogger().handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 1


class TestCrashHook:
    def _trigger(self, exc: BaseException) -> None:
        sys.excepthook(type(exc), exc, exc.__traceback__)

    def test_dump_contains_provider_and_static_context(self, log_env):
        _log.setup_logging(debug=False)
        _log.install_crash_hook(extra_context={"debug": False})
        _log.register_crash_context_provider(lambda: {"scene": "game", "frames_since_reset": 42})

        try:
            raise ValueError("kaboom")
        except ValueError as exc:
            self._trigger(exc)

        dumps = list(log_env.glob("crash-*.json"))
        assert len(dumps) == 1
        payload = json.loads(dumps[0].read_text(encoding="utf-8"))
        assert payload["exception"]["type"] == "ValueError"
        assert payload["exception"]["message"] == "kaboom"
        assert "ValueError: kaboom" in payload["traceback"]
        assert payload["context"]["debug"] is False
        assert payload["context"]["scene"] == "game"
        assert payload["context"]["frames_since_reset"] == 42

        # The full traceback also lands in the always-on log file.
        assert "kaboom" in _read_log(_log.get_log_file_path())

    def test_broken_provider_does_not_mask_crash(self, log_env):
        _log.install_crash_hook()
        _log.register_crash_context_provider(lambda: 1 / 0)

        try:
            raise RuntimeError("still-dumped")
        except RuntimeError as exc:
            self._trigger(exc)

        dumps = list(log_env.glob("crash-*.json"))
        assert len(dumps) == 1
        payload = json.loads(dumps[0].read_text(encoding="utf-8"))
        assert payload["exception"]["type"] == "RuntimeError"
