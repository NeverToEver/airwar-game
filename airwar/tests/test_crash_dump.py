"""Tests for ``airwar._log.crash_dump`` and ``install_crash_hook``."""

from __future__ import annotations

import json
import logging
import sys

import pytest

from airwar._log import (
    LOGGER_NAME,
    crash_dump,
    install_crash_hook,
)


@pytest.fixture
def redirect_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("AIRWAR_CACHE_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture(autouse=True)
def _restore_excepthook():
    original = sys.excepthook
    yield
    sys.excepthook = original


@pytest.fixture(autouse=True)
def _reset_logging():
    logger = logging.getLogger(LOGGER_NAME)
    saved = (list(logger.handlers), logger.propagate, logger.level, logger.disabled)
    yield
    logger.handlers, logger.propagate, logger.level, logger.disabled = saved


def _make_exception() -> RuntimeError:
    try:
        raise RuntimeError("boom")
    except RuntimeError as exc:
        return exc


class TestCrashDump:
    def test_writes_file_to_cache(self, redirect_cache):
        exc = _make_exception()
        path = crash_dump(exc, {"scene": "game", "frame": 42})
        assert path is not None
        assert path.parent == redirect_cache
        assert path.name.startswith("crash-")
        assert path.suffix == ".json"
        assert path.exists()

    def test_dump_payload_shape(self, redirect_cache):
        path = crash_dump(_make_exception(), {"scene": "game"})
        assert path is not None
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["exception"]["type"] == "RuntimeError"
        assert data["exception"]["message"] == "boom"
        assert "RuntimeError" in data["traceback"]
        assert "raise RuntimeError" in data["traceback"]
        assert data["context"]["scene"] == "game"
        assert "timestamp" in data
        assert "platform" in data
        assert "python" in data["platform"]

    def test_dump_handles_non_serializable_context(self, redirect_cache):
        class Opaque:
            def __repr__(self) -> str:
                return "<Opaque instance>"

        path = crash_dump(_make_exception(), {"obj": Opaque(), "path": __file__})
        assert path is not None
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["context"]["obj"] == "<Opaque instance>"
        # File paths are coerced to strings.
        assert isinstance(data["context"]["path"], str)

    def test_dump_returns_none_on_failure(self, tmp_path, monkeypatch):
        # Block the cache directory creation.
        blocker = tmp_path / "blocker"
        blocker.write_text("not a directory")
        monkeypatch.setenv("AIRWAR_CACHE_DIR", str(blocker / "nested"))
        result = crash_dump(_make_exception())
        assert result is None

    def test_empty_context_is_allowed(self, redirect_cache):
        path = crash_dump(_make_exception())
        assert path is not None
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["context"] == {}

    def test_two_dumps_get_distinct_filenames(self, redirect_cache):
        paths = [crash_dump(_make_exception()) for _ in range(2)]
        assert all(p is not None for p in paths)
        assert len({p.name for p in paths}) == 2


class TestInstallCrashHook:
    def test_installs_excepthook(self):
        assert sys.excepthook != install_crash_hook  # not equal to the function itself
        install_crash_hook()
        assert sys.excepthook.__name__ == "_hook"

    def test_keyboard_interrupt_passthrough(self, capsys):
        install_crash_hook(extra_context={"scene": "game"})
        try:
            raise KeyboardInterrupt("user ctrl-c")
        except KeyboardInterrupt:
            exc_type, exc_value, exc_tb = sys.exc_info()
            assert exc_type is not None
            sys.excepthook(exc_type, exc_value, exc_tb)
        # No crash dump marker should be written; the original hook is restored.
        captured = capsys.readouterr()
        assert "crash dump written" not in captured.err

    def test_excepthook_writes_dump(self, redirect_cache, capsys):
        install_crash_hook(extra_context={"scene": "game", "frame": 99})
        try:
            raise ValueError("nope")
        except ValueError:
            exc_type, exc_value, exc_tb = sys.exc_info()
            assert exc_type is not None
            sys.excepthook(exc_type, exc_value, exc_tb)
        crash_files = list(redirect_cache.glob("crash-*.json"))
        assert len(crash_files) == 1
        data = json.loads(crash_files[0].read_text(encoding="utf-8"))
        assert data["exception"]["type"] == "ValueError"
        assert data["context"]["scene"] == "game"
        assert data["context"]["frame"] == 99
        captured = capsys.readouterr()
        assert "crash dump written" in captured.err
