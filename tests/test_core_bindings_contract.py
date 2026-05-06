import airwar.core_bindings as core_bindings


def test_batch_update_bullets_contract():
    result = core_bindings.batch_update_bullets([
        (7, 10.0, 20.0, 1.5, -2.0, 0, False, 100.0),
    ])

    assert result == [(7, 11.5, 18.0, True)]
