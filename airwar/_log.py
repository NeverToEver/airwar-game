"""Centralized logging + crash-dump configuration for AirWar.

Public API:
    setup_logging(debug: bool = False) -> None
        Configure the ``airwar`` logger via ``logging.config.dictConfig``.
        ``debug=True`` adds a file handler at ``<cache>/airwar.log`` and
        raises the level to DEBUG. ``debug=False`` keeps console-only INFO
        output and writes no file.

    get_cache_dir() -> Path
        Return the cache directory used for both the log file and crash
        dumps. Honors ``$AIRWAR_CACHE_DIR`` (used by tests) and falls back
        to ``$XDG_CACHE_HOME/airwar`` or ``~/.cache/airwar`` on POSIX and
        ``%LOCALAPPDATA%\\airwar`` on Windows.

    crash_dump(exception, context: dict | None = None) -> Path | None
        Serialize ``exception`` + ``context`` to a timestamped JSON file
        under the cache directory and return the path. Returns ``None`` if
        the dump itself fails -- the original exception is never re-raised.

    install_crash_hook(extra_context: dict | None = None) -> None
        Register :func:`crash_dump` as ``sys.excepthook``. ``extra_context``
        is merged into every dump and is the place to attach live game
        state (scene name, frame counter, ...).
"""

from __future__ import annotations

import json
import logging
import logging.config
import os
import platform
import sys
import tempfile
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOGGER_NAME = "airwar"
_LOG_FILE_NAME = "airwar.log"
_CRASH_PREFIX = "crash-"


def get_cache_dir() -> Path:
    """Return the on-disk cache directory used for logs and crash dumps."""
    env_override = os.environ.get("AIRWAR_CACHE_DIR")
    if env_override:
        return Path(env_override)

    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg) / "airwar"

    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            return Path(base) / "airwar"
        return Path(tempfile.gettempdir()) / "airwar"

    home = Path.home() if os.environ.get("HOME") else None
    if home is not None:
        return home / ".cache" / "airwar"
    return Path(tempfile.gettempdir()) / "airwar"


def _console_formatter() -> logging.Formatter:
    return logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _file_formatter() -> logging.Formatter:
    return logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def setup_logging(debug: bool = False) -> None:
    """Configure the ``airwar`` logger.

    Idempotent: safe to call multiple times. The console handler is always
    installed; the file handler is added only when ``debug=True``.
    """
    cache_dir = get_cache_dir()

    handlers: dict[str, dict[str, Any]] = {
        "console": {
            "class": "logging.StreamHandler",
            "stream": sys.stderr,
            "formatter": "console",
            "level": "DEBUG" if debug else "INFO",
        },
    }
    root_handlers: list[str] = ["console"]

    if debug:
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            handlers["file"] = {
                "class": "logging.FileHandler",
                "filename": str(cache_dir / _LOG_FILE_NAME),
                "mode": "a",
                "encoding": "utf-8",
                "formatter": "file",
                "level": "DEBUG",
            }
            root_handlers.append("file")
        except OSError:
            logging.getLogger(LOGGER_NAME).warning(
                "Could not open log file under %s; continuing without file handler.",
                cache_dir,
            )

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "console": {"()": _console_formatter},
            "file": {"()": _file_formatter},
        },
        "handlers": handlers,
        "loggers": {
            LOGGER_NAME: {
                "handlers": root_handlers,
                "level": "DEBUG" if debug else "INFO",
                "propagate": False,
            },
        },
        "root": {
            "handlers": [],
            "level": "WARNING",
        },
    }
    logging.config.dictConfig(config)


def _coerce(value: Any) -> Any:
    """Coerce ``value`` to a JSON-serializable form, falling back to ``repr``."""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple, set)):
        return [_coerce(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _coerce(v) for k, v in value.items()}
    if isinstance(value, BaseException):
        return f"{type(value).__name__}: {value}"
    if isinstance(value, Path):
        return str(value)
    return repr(value)


def crash_dump(exception: BaseException, context: dict[str, Any] | None = None) -> Path | None:
    """Write a JSON crash dump and return the resulting path (or ``None``)."""
    try:
        cache_dir = get_cache_dir()
        cache_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S-%f")
        path = cache_dir / f"{_CRASH_PREFIX}{stamp}.json"
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "unix_time": time.time(),
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "python": sys.version,
            },
            "exception": {
                "type": type(exception).__name__,
                "module": type(exception).__module__,
                "message": str(exception),
                "args": [_coerce(a) for a in exception.args],
            },
            "traceback": "".join(
                traceback.format_exception(type(exception), exception, exception.__traceback__)
            ),
            "context": _coerce(context or {}),
        }
        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False, default=repr)
        return path
    except Exception as dump_error:  # noqa: BLE001 -- last-resort logging
        logging.getLogger(LOGGER_NAME).error("crash_dump failed: %s", dump_error)
        return None


def _make_excepthook(extra_context: dict[str, Any] | None):
    def _hook(exc_type, exc_value, exc_tb):
        # Preserve normal Ctrl-C behavior.
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        merged: dict[str, Any] = {}
        if extra_context:
            merged.update(extra_context)
        # Original traceback on stderr (so the player still sees the error).
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        try:
            exc_value.__traceback__ = exc_tb
            path = crash_dump(exc_value, merged)
            if path is not None:
                sys.stderr.write(f"\n[airwar] crash dump written to: {path}\n")
        except Exception:  # noqa: BLE001 -- must not mask the original crash
            pass
    return _hook


def install_crash_hook(extra_context: dict[str, Any] | None = None) -> None:
    """Install :func:`crash_dump` as ``sys.excepthook``."""
    sys.excepthook = _make_excepthook(extra_context)


__all__ = [
    "LOGGER_NAME",
    "get_cache_dir",
    "setup_logging",
    "crash_dump",
    "install_crash_hook",
]
