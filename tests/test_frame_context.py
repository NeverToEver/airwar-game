"""Tests for the shared frame-timing abstraction."""

import pytest

from airwar.game.frame_context import (
    FixedStepAccumulator,
    FrameClock,
    FrameContext,
)


class TestFrameContext:
    def test_zero_steps_returns_empty_tuple(self):
        ctx = FrameContext(delta_seconds=0.016, elapsed_seconds=1.0, simulation_steps=0)
        assert ctx.steps() == ()

    def test_single_step_spans_full_fixed_delta(self):
        ctx = FrameContext(delta_seconds=0.016, elapsed_seconds=0.016, simulation_steps=1)
        steps = ctx.steps()
        assert len(steps) == 1
        assert steps[0].delta_seconds == pytest.approx(FrameContext.FIXED_DELTA_SECONDS)
        assert steps[0].elapsed_seconds == pytest.approx(0.016)

    def test_multiple_steps_are_sequential_fixed_deltas(self):
        ctx = FrameContext(delta_seconds=0.050, elapsed_seconds=0.050, simulation_steps=3)
        steps = ctx.steps()
        assert len(steps) == 3
        assert steps[0].elapsed_seconds == pytest.approx(
            0.050 - 2 * FrameContext.FIXED_DELTA_SECONDS
        )
        assert steps[2].elapsed_seconds == pytest.approx(0.050)


class TestFixedStepAccumulator:
    def test_rejects_non_positive_fixed_delta(self):
        with pytest.raises(ValueError):
            FixedStepAccumulator(fixed_delta_seconds=0)
        with pytest.raises(ValueError):
            FixedStepAccumulator(fixed_delta_seconds=-0.01)

    def test_rejects_fixed_delta_out_of_bounds(self):
        with pytest.raises(ValueError):
            FixedStepAccumulator(fixed_delta_seconds=1.0 / 1201.0)
        with pytest.raises(ValueError):
            FixedStepAccumulator(fixed_delta_seconds=1.0 / 9.0)

    def test_rejects_invalid_delta_seconds(self):
        acc = FixedStepAccumulator()
        with pytest.raises(ValueError):
            acc.advance(-0.1, simulate=True)
        with pytest.raises(ValueError):
            acc.advance(float("nan"), simulate=True)
        with pytest.raises(ValueError):
            acc.advance(float("inf"), simulate=True)
        with pytest.raises(ValueError):
            acc.advance(float("-inf"), simulate=True)

    def test_non_simulate_mode_emits_zero_steps(self):
        acc = FixedStepAccumulator()
        ctx = acc.advance(0.016, simulate=False)
        assert ctx.simulation_steps == 0
        assert ctx.elapsed_seconds == 0.0

    def test_exact_step_emits_one_step(self):
        acc = FixedStepAccumulator()
        ctx = acc.advance(FrameContext.FIXED_DELTA_SECONDS, simulate=True)
        assert ctx.simulation_steps == 1
        assert ctx.elapsed_seconds == pytest.approx(FrameContext.FIXED_DELTA_SECONDS)

    def test_accumulates_partial_time_across_frames(self):
        acc = FixedStepAccumulator()
        fixed = FrameContext.FIXED_DELTA_SECONDS
        # Two small frames do not yet reach one fixed step.
        ctx = acc.advance(0.005, simulate=True)
        assert ctx.simulation_steps == 0
        ctx = acc.advance(0.005, simulate=True)
        assert ctx.simulation_steps == 0
        # The accumulated 0.01 s plus another 0.01 s exceeds one fixed step.
        ctx = acc.advance(0.010, simulate=True)
        assert ctx.simulation_steps == 1
        # Two full fixed steps on the next frame.
        ctx = acc.advance(2 * fixed + 0.001, simulate=True)
        assert ctx.simulation_steps == 2

    def test_clamps_large_deltas(self):
        acc = FixedStepAccumulator()
        ctx = acc.advance(10.0, simulate=True)
        assert ctx.delta_seconds == pytest.approx(acc.MAX_DELTA_SECONDS)
        # MAX_DELTA / (1/60) = 15 steps exactly.
        assert ctx.simulation_steps == 15

    def test_reset_clears_accumulated_time(self):
        acc = FixedStepAccumulator()
        acc.advance(0.010, simulate=True)
        acc.reset()
        ctx = acc.advance(0.010, simulate=True)
        assert ctx.simulation_steps == 0
        assert ctx.elapsed_seconds == 0.0


class TestFrameClock:
    def test_default_scheduler_advances(self):
        clock = FrameClock()
        ctx = clock.advance(0.016, simulate=True)
        assert isinstance(ctx, FrameContext)

    def test_custom_scheduler_is_used(self):
        class DummyScheduler:
            def reset(self):
                pass

            def advance(self, delta_seconds, *, simulate):
                return FrameContext(delta_seconds=delta_seconds, elapsed_seconds=0.0, simulation_steps=0)

        clock = FrameClock(scheduler=DummyScheduler())
        ctx = clock.advance(0.123, simulate=True)
        assert ctx.delta_seconds == pytest.approx(0.123)
