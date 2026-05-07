import airwar.core_bindings as core_bindings


def test_batch_update_bullets_contract():
    result = core_bindings.batch_update_bullets([
        (7, 10.0, 20.0, 1.5, -2.0, 0, False, 100.0),
    ])

    assert result == [(7, 11.5, 18.0, True)]


def test_core_bindings_fallback_when_rust_module_is_missing(monkeypatch):
    import importlib
    import importlib.abc
    import sys

    class BlockAirwarCore(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname == "airwar_core":
                raise ImportError("blocked for fallback test")
            return None

    original_module = sys.modules.pop("airwar.core_bindings", None)
    original_core = sys.modules.pop("airwar_core", None)
    monkeypatch.syspath_prepend("/tmp/airwar-core-fallback-missing")
    sys.meta_path.insert(0, BlockAirwarCore())
    try:
        fallback = importlib.import_module("airwar.core_bindings")
        result = fallback.batch_update_bullets([
            (9, 10.0, 20.0, 1.0, -2.0, 0, False, 100.0),
        ])

        assert fallback.RUST_AVAILABLE is False
        assert result == [(9, 11.0, 18.0, True)]
    finally:
        sys.meta_path = [finder for finder in sys.meta_path if not isinstance(finder, BlockAirwarCore)]
        sys.modules.pop("airwar.core_bindings", None)
        if original_module is not None:
            sys.modules["airwar.core_bindings"] = original_module
            sys.modules["airwar"].core_bindings = original_module
        if original_core is not None:
            sys.modules["airwar_core"] = original_core
