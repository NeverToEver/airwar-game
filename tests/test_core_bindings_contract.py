import importlib.abc
import math

import pytest

import airwar.core_bindings as core_bindings


def test_batch_update_bullets_contract():
    result = core_bindings.batch_update_bullets(
        [
            (7, 10.0, 20.0, 1.5, -2.0, 0, False, 100.0),
        ]
    )

    assert result == [(7, 11.5, 18.0, True)]


class _BlockAirwarCore(importlib.abc.MetaPathFinder):
    """Prevent ``airwar_core`` from being imported so the Python fallback loads."""

    def find_spec(self, fullname, path=None, target=None):
        if fullname == "airwar_core":
            raise ImportError("blocked for fallback test")
        return None


@pytest.fixture
def fallback_core_bindings(monkeypatch):
    """Import ``airwar.core_bindings`` with the Rust extension blocked."""
    import importlib
    import sys

    original_module = sys.modules.pop("airwar.core_bindings", None)
    original_core = sys.modules.pop("airwar_core", None)
    monkeypatch.syspath_prepend("/tmp/airwar-core-fallback-missing")
    sys.meta_path.insert(0, _BlockAirwarCore())
    try:
        fallback = importlib.import_module("airwar.core_bindings")
        yield fallback
    finally:
        sys.meta_path = [finder for finder in sys.meta_path if not isinstance(finder, _BlockAirwarCore)]
        sys.modules.pop("airwar.core_bindings", None)
        if original_module is not None:
            sys.modules["airwar.core_bindings"] = original_module
            sys.modules["airwar"].core_bindings = original_module
        if original_core is not None:
            sys.modules["airwar_core"] = original_core


def test_fallback_batch_update_movements_buf_format(fallback_core_bindings) -> None:
    """Fallback batch_update_movements_buf must correctly unpack a 48-byte base buffer."""
    import struct

    fallback = fallback_core_bindings
    assert fallback.RUST_AVAILABLE is False

    base_buf = struct.pack("<Bxxx" + "f" * 11, 0, *range(1, 12))
    extra_buf = struct.pack("<fffffffI", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0)
    result = fallback.batch_update_movements_buf(base_buf, extra_buf)

    assert len(result) == 1
    x, y, new_timer = result[0]
    assert x == 2.0
    assert y == pytest.approx(3.0 + math.sin(0.1) * 1.5)
    assert new_timer == 2.0


def test_core_bindings_fallback_when_rust_module_is_missing(fallback_core_bindings) -> None:
    fallback = fallback_core_bindings
    result = fallback.batch_update_bullets(
        [
            (9, 10.0, 20.0, 1.0, -2.0, 0, False, 100.0),
        ]
    )

    assert fallback.RUST_AVAILABLE is False
    assert result == [(9, 11.0, 18.0, True)]
