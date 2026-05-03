import pytest

import airwar.core_bindings as core_bindings


def test_core_bindings_exports_availability_flag():
    assert isinstance(core_bindings.RUST_AVAILABLE, bool)


@pytest.mark.skipif(not core_bindings.RUST_AVAILABLE, reason="Rust extension is optional")
def test_batch_update_bullets_contract_when_rust_available():
    result = core_bindings.batch_update_bullets([
        (7, 10.0, 20.0, 1.5, -2.0, 0, False, 100.0),
    ])

    assert result == [(7, 11.5, 18.0, True)]
