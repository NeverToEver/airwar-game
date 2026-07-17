"""Centralized logging + crash-dump configuration for AirWar.

Public API:
    setup_logging(debug: bool = False) -> None
        Configure logging via ``logging.config.dictConfig``. A rotating
        file handler at ``<cache>/airwar.log`` is always installed so
        crashes during normal play leave a trail; ``debug=True`` raises
        the ``airwar`` logger and the console to DEBUG. Handlers are
        attached to the root logger so every module logger -- including
        legacy class-named ones such as ``SceneDirector`` -- reaches the
        file. Also enables :mod:`faulthandler` writing to
        ``<cache>/faulthandler.log`` so native (SDL) crashes leave a
        Python stack trace.

    get_cache_dir() -> Path
        Return the cache directory used for both the log file and crash
        dumps. Honors ``$AIRWAR_CACHE_DIR`` and falls back
        to ``$XDG_CACHE_HOME/airwar`` or ``~/.cache/airwar`` on POSIX and
        ``%LOCALAPPDATA%\\airwar`` on Windows.

    get_log_file_path() -> Path
        Return the path of the always-on rotating log file.

    crash_dump(exception, context: dict | None = None) -> Path | None
        Serialize ``exception`` + ``context`` to a timestamped JSON file
        under the cache directory and return the path. Returns ``None`` if
        the dump itself fails -- the original exception is never re-raised.

    register_crash_context_provider(provider) -> None
        Register a zero-arg callable returning a mapping of live game
        state (scene name, frame counter, ...). Providers are called at
        crash time and merged into every dump; a raising provider is
        skipped so it can never mask the crash.

    install_crash_hook(extra_context: dict | None = None) -> None
        Register :func:`crash_dump` as ``sys.excepthook``. ``extra_context``
        is merged into every dump; use providers for live state. The full
        traceback is also logged at CRITICAL level so it lands in the
        log file even when stderr is lost (packaged builds, launchers).
"""

from __future__ import annotations

import faulthandler
import json
import logging
import logging.config
import os
import platform
import sys
import tempfile
import time
import traceback
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOGGER_NAME = "airwar"
_LOG_FILE_NAME = "airwar.log"
_FAULT_LOG_NAME = "faulthandler.log"
_LOG_MAX_BYTES = 1_000_000
_LOG_BACKUP_COUNT = 2
_CRASH_PREFIX = "crash-"

_CRASH_CONTEXT_PROVIDERS: list[Callable[[], Mapping[str, Any] | None]] = []
_FAULT_HANDLER_STREAM = None  # Kept alive for the process lifetime: faulthandler writes into it.


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


def get_log_file_path() -> Path:
    """Return the path of the always-on rotating log file."""
    return get_cache_dir() / _LOG_FILE_NAME


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
    """Configure root logging handlers plus the ``airwar`` logger level.

    Idempotent: safe to call multiple times. The console handler and an
    always-on rotating file handler are attached to the *root* logger, so
    every logger in the process (``airwar.*``, pygame, and any stray
    top-level logger) propagates into the same sinks. The ``airwar``
    logger itself only carries the level gate, so ``debug=True`` turns on
    DEBUG output for AirWar's own modules without enabling DEBUG for
    third-party loggers.
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

    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(get_log_file_path()),
            "maxBytes": _LOG_MAX_BYTES,
            "backupCount": _LOG_BACKUP_COUNT,
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
            # No handlers of its own: records propagate to the root
            # handlers above. The level gate lives here so --debug only
            # raises AirWar's own verbosity, not third-party loggers'.
            LOGGER_NAME: {
                "level": "DEBUG" if debug else "INFO",
                "propagate": True,
            },
        },
        "root": {
            "handlers": root_handlers,
            "level": "INFO",
        },
    }
    logging.config.dictConfig(config)
    _enable_faulthandler(cache_dir)


def _enable_faulthandler(cache_dir: Path) -> None:
    """Dump Python tracebacks on native crashes (segfaults) to a file.

    SDL/pygame can die in C code without ever raising a Python exception;
    ``sys.excepthook`` never fires for those. ``faulthandler`` catches the
    fatal signals and writes the current Python stack to
    ``<cache>/faulthandler.log`` before the process dies.
    """
    global _FAULT_HANDLER_STREAM
    if faulthandler.is_enabled():
        return
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        _FAULT_HANDLER_STREAM = (cache_dir / _FAULT_LOG_NAME).open("a", encoding="utf-8")
        faulthandler.enable(file=_FAULT_HANDLER_STREAM)
    except OSError:
        faulthandler.enable()  # Fall back to stderr rather than nothing.


def register_crash_context_provider(provider: Callable[[], Mapping[str, Any] | None]) -> None:
    """Register a callable returning live game state for crash dumps.

    Providers are called at crash time (never during normal play) and are
    allowed to fail: a raising provider is skipped so it cannot mask the
    crash being reported.
    """
    _CRASH_CONTEXT_PROVIDERS.append(provider)


def _collect_crash_context(extra_context: dict[str, Any] | None) -> dict[str, Any]:
    """Merge static ``extra_context`` with every registered provider's state."""
    merged: dict[str, Any] = dict(extra_context or {})
    for provider in list(_CRASH_CONTEXT_PROVIDERS):
        try:
            data = provider()
        except Exception:  # noqa: BLE001 -- a broken provider must not mask the crash
            continue
        if data:
            merged.update(data)
    return merged


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
        logger = logging.getLogger(LOGGER_NAME)
        # Original traceback on stderr (so the player still sees the error).
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        # Also land the full traceback in the always-on log file: stderr is
        # lost for packaged builds and double-clicked launchers.
        logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
        try:
            exc_value.__traceback__ = exc_tb
            path = crash_dump(exc_value, _collect_crash_context(extra_context))
            if path is not None:
                logger.critical("Crash dump written to %s", path)
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
    "get_log_file_path",
    "setup_logging",
    "crash_dump",
    "register_crash_context_provider",
    "install_crash_hook",
]
