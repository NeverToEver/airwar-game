"""F07: enemy_movement_batch tests.

Covers the 0% coverage of the enemy movement batch encoder
extracted from Enemy class in Round 4 of Phase 3 refactor.
"""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestEnemyMovementBatchEncoding:
    """F07: encode_rust_movement_params returns the expected tuple shape."""

    def _make_enemy(self, move_type: str, **overrides) -> SimpleNamespace:
        from airwar.entities.enemy.enemy_movement_batch import configure_rust_movement

        enemy = SimpleNamespace(
            move_type=move_type,
            _rust_move_type_code=42,  # placeholder (overwritten by configure)
            _rust_params={},  # placeholder (overwritten by configure)
            active_position_x=100.0,
            active_position_y=200.0,
            rect=SimpleNamespace(x=300, y=400),
            # Attributes that configure() reads via getattr; provide defaults
            move_offset=0.0,
            move_amplitude=1.5,
            move_frequency=0.05,
            move_speed=3.0,
            direction=1.0,
            zigzag_interval=30,
            zigzag_speed=2.5,
            spiral_radius=50.0,
            spiral_frequency=0.04,
            spiral_speed=2.0,
            hover_timer=0.0,
            noise_timer=0.0,
            noise_speed=1.0,
            noise_scale_x=2.0,
            noise_scale_y=1.5,
            noise_amplitude_x=100.0,
            noise_amplitude_y=80.0,
            noise_seed=12345,
            agg_timer=0.0,
            agg_speed=1.5,
            agg_scale_x=2.0,
            agg_scale_y=1.5,
            agg_amplitude_x=100.0,
            agg_amplitude_y=80.0,
            agg_seed=99999,
        )
        for k, v in overrides.items():
            setattr(enemy, k, v)
        # Always run configure so _timer_attr is set correctly per move_type
        configure_rust_movement(enemy)
        return enemy

    def test_returns_none_pair_when_not_configured(self):
        """Enemy without _rust_move_type_code returns (None, None)."""
        from airwar.entities.enemy.enemy_movement_batch import (
            encode_rust_movement_params,
        )

        enemy = SimpleNamespace()  # no _rust_move_type_code
        base, extra = encode_rust_movement_params(enemy)
        assert base is None
        assert extra is None

    def test_base_tuple_has_12_fields_matching_rust_layout(self):
        """The base tuple must have exactly 12 fields matching Rust struct."""
        from airwar.entities.enemy.enemy_movement_batch import (
            MOVEMENT_TYPE_MAP,
            encode_rust_movement_params,
        )

        enemy = self._make_enemy("spiral")
        base, _extra = encode_rust_movement_params(enemy)
        assert base is not None
        assert len(base) == 12
        # First field: move_type_code from MOVEMENT_TYPE_MAP
        assert base[0] == MOVEMENT_TYPE_MAP["spiral"]
        # Index 1: timer
        # Indices 2-3: active_position (x, y)
        assert base[2] == 100.0
        assert base[3] == 200.0
        # Last field: zigzag_interval
        assert base[11] == 30

    def test_extra_tuple_has_8_fields_matching_rust_layout(self):
        """The extra tuple must have exactly 8 fields matching Rust struct."""
        from airwar.entities.enemy.enemy_movement_batch import (
            encode_rust_movement_params,
        )

        enemy = self._make_enemy("spiral")
        _base, extra = encode_rust_movement_params(enemy)
        assert extra is not None
        assert len(extra) == 8
        # Index 0: spiral_radius
        assert extra[0] == 50.0
        # Indices 1-2: current (x, y) from rect
        assert extra[1] == 300
        assert extra[2] == 400
        # Last field: noise_seed (spiral uses noise_seed=12345)
        assert extra[7] == 12345

    def test_hover_timer_scaling(self):
        """For move_type='hover', timer is divided by HOVER_TIMER_RUST_SCALE."""
        from airwar.entities.enemy.enemy_movement_batch import (
            HOVER_TIMER_RUST_SCALE,
            encode_rust_movement_params,
        )

        enemy = self._make_enemy("hover", hover_timer=120.0)
        base, _ = encode_rust_movement_params(enemy)
        # Timer is the 2nd field (index 1)
        expected = 120.0 / HOVER_TIMER_RUST_SCALE
        assert base[1] == expected

    def test_non_hover_timer_not_scaled(self):
        """For non-hover move_types, timer is the raw value."""
        from airwar.entities.enemy.enemy_movement_batch import (
            encode_rust_movement_params,
        )

        enemy = self._make_enemy("spiral", spiral_timer=200.0)
        base, _ = encode_rust_movement_params(enemy)
        assert base[1] == 200.0  # no scaling


class TestConfigureRustMovement:
    """F07: configure_rust_movement populates enemy state idempotently."""

    def test_configure_populates_move_type_code(self):
        from airwar.entities.enemy.enemy_movement_batch import (
            MOVEMENT_TYPE_MAP,
            configure_rust_movement,
        )

        for move_type, expected_code in MOVEMENT_TYPE_MAP.items():
            enemy = SimpleNamespace(move_type=move_type, move_timer=0.0)
            configure_rust_movement(enemy)
            assert enemy._rust_move_type_code == expected_code, (
                f"For {move_type!r}, expected code {expected_code}, got {enemy._rust_move_type_code}"
            )

    def test_configure_sets_timer_attribute_for_hover(self):
        from airwar.entities.enemy.enemy_movement_batch import configure_rust_movement

        enemy = SimpleNamespace(move_type="hover", hover_timer=0.0)
        configure_rust_movement(enemy)
        assert enemy._timer_attr == "hover_timer"

    def test_configure_sets_timer_attribute_for_zigzag(self):
        from airwar.entities.enemy.enemy_movement_batch import configure_rust_movement

        enemy = SimpleNamespace(move_type="zigzag", zigzag_timer=0.0)
        configure_rust_movement(enemy)
        assert enemy._timer_attr == "zigzag_timer"

    def test_configure_sets_timer_attribute_for_aggressive(self):
        from airwar.entities.enemy.enemy_movement_batch import configure_rust_movement

        enemy = SimpleNamespace(move_type="aggressive", agg_timer=0.0)
        configure_rust_movement(enemy)
        assert enemy._timer_attr == "aggressive_timer"

    def test_configure_falls_back_to_move_timer_for_unknown(self):
        from airwar.entities.enemy.enemy_movement_batch import configure_rust_movement

        enemy = SimpleNamespace(move_type="straight", move_timer=0.0)
        configure_rust_movement(enemy)
        assert enemy._timer_attr == "move_timer"

    def test_configure_is_idempotent(self):
        """Calling configure twice yields the same state."""
        from airwar.entities.enemy.enemy_movement_batch import configure_rust_movement

        enemy = SimpleNamespace(
            move_type="spiral",
            spiral_timer=0.0,
            spiral_frequency=0.05,
        )
        configure_rust_movement(enemy)
        first_code = enemy._rust_move_type_code
        first_timer_attr = enemy._timer_attr
        first_params = dict(enemy._rust_params)
        # Second call
        configure_rust_movement(enemy)
        assert enemy._rust_move_type_code == first_code
        assert enemy._timer_attr == first_timer_attr
        assert enemy._rust_params == first_params


class TestMovementTypeMapCompleteness:
    """F07: MOVEMENT_TYPE_MAP covers all 8 movement patterns."""

    def test_movement_type_map_has_8_entries(self):
        from airwar.entities.enemy.enemy_movement_batch import MOVEMENT_TYPE_MAP

        assert len(MOVEMENT_TYPE_MAP) == 8
        expected_keys = {
            "straight",
            "sine",
            "zigzag",
            "dive",
            "hover",
            "spiral",
            "noise",
            "aggressive",
        }
        assert set(MOVEMENT_TYPE_MAP.keys()) == expected_keys

    def test_movement_type_map_values_are_unique(self):
        from airwar.entities.enemy.enemy_movement_batch import MOVEMENT_TYPE_MAP

        values = list(MOVEMENT_TYPE_MAP.values())
        assert len(values) == len(set(values)), "Move type codes must be unique"
