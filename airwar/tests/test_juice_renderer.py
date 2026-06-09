"""Unit tests for JuiceController (trauma-based screen shake).

Covers:
- Initial state (trauma=0 → offset=(0,0))
- Trauma injection (clamp, accumulate, no-op for invalid input)
- Decay (linear, clamps to zero)
- Offset (non-zero at trauma>0, always integer, deterministic with seed)
- Realistic damage / explosion cycle
"""

from __future__ import annotations

import pytest

from airwar.game.rendering.juice_renderer import JuiceController


class TestJuiceControllerInit:
    def test_initial_trauma_is_zero(self):
        jc = JuiceController()
        assert jc.trauma == 0.0
        assert jc.offset() == (0, 0)

    def test_seed_makes_offset_deterministic(self):
        a = JuiceController(seed=42)
        b = JuiceController(seed=42)
        a.add_trauma(0.5)
        b.add_trauma(0.5)
        # Same seed → same sequence of offsets.
        for _ in range(10):
            assert a.offset() == b.offset()


class TestJuiceControllerInjection:
    def test_add_trauma_sets_value(self):
        jc = JuiceController()
        jc.add_trauma(0.5)
        assert jc.trauma == 0.5

    def test_add_trauma_clamps_to_one(self):
        jc = JuiceController()
        jc.add_trauma(0.7)
        jc.add_trauma(0.5)
        # accumulate then clamp to 1.0
        assert jc.trauma == 1.0

    def test_add_trauma_negative_is_noop(self):
        jc = JuiceController()
        jc.add_trauma(-0.5)
        assert jc.trauma == 0.0

    def test_add_trauma_zero_is_noop(self):
        jc = JuiceController()
        jc.add_trauma(0.0)
        assert jc.trauma == 0.0

    def test_add_trauma_none_is_noop(self):
        jc = JuiceController()
        jc.add_trauma(None)  # type: ignore[arg-type]
        assert jc.trauma == 0.0


class TestJuiceControllerDecay:
    def test_update_reduces_trauma(self):
        jc = JuiceController()
        jc.add_trauma(1.0)
        jc.update()
        assert jc.trauma == pytest.approx(1.0 - 0.075)

    def test_update_clamps_to_zero(self):
        jc = JuiceController()
        jc.add_trauma(0.01)
        for _ in range(20):
            jc.update()
        assert jc.trauma == 0.0
        assert jc.offset() == (0, 0)

    def test_full_decay_cycle_returns_to_zero(self):
        jc = JuiceController()
        jc.add_trauma(1.0)
        # Full trauma should decay in ~13 frames (1.0 / 0.075 ≈ 13.3)
        for _ in range(20):
            jc.update()
        assert jc.trauma == 0.0
        assert jc.offset() == (0, 0)

    def test_update_at_zero_is_noop(self):
        jc = JuiceController()
        jc.update()
        assert jc.trauma == 0.0


class TestJuiceControllerOffset:
    def test_offset_at_zero_trauma(self):
        jc = JuiceController()
        assert jc.offset() == (0, 0)
        # Repeat — must always be (0, 0) at rest.
        for _ in range(5):
            assert jc.offset() == (0, 0)

    def test_offset_is_integer(self):
        jc = JuiceController(seed=123)
        jc.add_trauma(0.5)
        for _ in range(10):
            dx, dy = jc.offset()
            assert isinstance(dx, int)
            assert isinstance(dy, int)

    def test_offset_bounded_by_max_offset_px(self):
        jc = JuiceController(seed=999)
        jc.add_trauma(1.0)
        for _ in range(10):
            dx, dy = jc.offset()
            # trauma=1.0, power=2 → magnitude=1.0 * MAX_OFFSET_PX
            assert -8 <= dx <= 8
            assert -8 <= dy <= 8

    def test_offset_scales_quadratically(self):
        # trauma=0.5 → 0.25 of MAX_OFFSET_PX = 2px
        jc = JuiceController(seed=42)
        jc.add_trauma(0.5)
        for _ in range(20):
            dx, dy = jc.offset()
            # trauma decays during these calls, so check the first call only
            # — but with the same seed, sequence is deterministic.
        # We just check that no individual offset exceeds 2 in absolute value
        # when trauma is ~0.5 (decay has run some frames).
        jc2 = JuiceController(seed=42)
        jc2.add_trauma(0.5)
        max_abs = 0
        for _ in range(5):
            dx, dy = jc2.offset()
            max_abs = max(max_abs, abs(dx), abs(dy))
        # After 5 calls trauma is ~0.625, then ~0.5 → bounded by 2px
        # (0.5^2 * 8 = 2.0). Be generous: up to 3.
        assert max_abs <= 3, f"offset too large for trauma=0.5: max_abs={max_abs}"


class TestJuiceControllerRealisticScenarios:
    def test_player_damage_cycle(self):
        """Simulate a player hit: trauma=0.4, decays over time, no offset at rest."""
        jc = JuiceController(seed=7)
        jc.add_trauma(0.4)
        assert jc.trauma == 0.4
        # First few frames should have non-zero offset.
        offsets = [jc.offset() for _ in range(3)]
        assert any(o != (0, 0) for o in offsets)
        # Decay fully.
        for _ in range(15):
            jc.update()
        assert jc.trauma == 0.0
        assert jc.offset() == (0, 0)

    def test_rapid_damage_accumulates(self):
        """Three small hits before decay should accumulate to ~0.7 (clamped to 1.0 if needed)."""
        jc = JuiceController()
        jc.add_trauma(0.3)
        jc.add_trauma(0.2)
        jc.add_trauma(0.2)
        # 0.3 + 0.2 + 0.2 = 0.7
        assert jc.trauma == pytest.approx(0.7)
