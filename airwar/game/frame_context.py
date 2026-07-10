"""Shared frame timing for deterministic gameplay simulation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class FrameContext:
    """The timing data sampled once for a rendered frame.

    ``simulation_steps`` converts the clamped wall-clock delta into 60 Hz
    gameplay steps. Callers that own simulation iterate ``steps()``; menus may
    use the outer context for presentation-only animation.
    """

    FIXED_DELTA_SECONDS = 1.0 / 60.0

    delta_seconds: float
    elapsed_seconds: float
    simulation_steps: int

    def steps(self) -> tuple["SimulationStep", ...]:
        if self.simulation_steps == 0:
            return ()
        first_elapsed = self.elapsed_seconds - self.FIXED_DELTA_SECONDS * (self.simulation_steps - 1)
        return tuple(
            SimulationStep(self.FIXED_DELTA_SECONDS, first_elapsed + index * self.FIXED_DELTA_SECONDS)
            for index in range(self.simulation_steps)
        )


@dataclass(frozen=True, slots=True)
class SimulationStep:
    """One fixed-rate gameplay update step derived from a frame context."""

    delta_seconds: float
    elapsed_seconds: float


class SimulationStepScheduler(Protocol):
    """Convert sampled wall time into fixed simulation work."""

    def reset(self) -> None: ...

    def advance(self, delta_seconds: float, *, simulate: bool) -> FrameContext: ...


class FixedStepAccumulator:
    """Accumulate wall time and emit lossless, capped fixed-rate steps."""

    MAX_DELTA_SECONDS = 0.25

    def __init__(self, fixed_delta_seconds: float = FrameContext.FIXED_DELTA_SECONDS) -> None:
        if fixed_delta_seconds <= 0:
            raise ValueError("fixed_delta_seconds must be positive")
        self._fixed_delta_seconds = fixed_delta_seconds
        self._elapsed_seconds = 0.0
        self._remainder_seconds = 0.0

    def reset(self) -> None:
        self._elapsed_seconds = 0.0
        self._remainder_seconds = 0.0

    def advance(self, delta_seconds: float, *, simulate: bool) -> FrameContext:
        delta = max(0.0, min(float(delta_seconds), self.MAX_DELTA_SECONDS))
        if not simulate:
            return FrameContext(delta, self._elapsed_seconds, 0)

        self._remainder_seconds += delta
        steps = int((self._remainder_seconds + 1e-12) / self._fixed_delta_seconds)
        self._remainder_seconds -= steps * self._fixed_delta_seconds
        self._elapsed_seconds += steps * self._fixed_delta_seconds
        return FrameContext(delta, self._elapsed_seconds, steps)


class FrameClock:
    """Coordinate a pluggable simulation-step scheduling policy."""

    def __init__(self, scheduler: SimulationStepScheduler | None = None) -> None:
        self._scheduler = scheduler or FixedStepAccumulator()

    def reset(self) -> None:
        self._scheduler.reset()

    def advance(self, delta_seconds: float, *, simulate: bool = True) -> FrameContext:
        return self._scheduler.advance(delta_seconds, simulate=simulate)


__all__ = [
    "FixedStepAccumulator",
    "FrameClock",
    "FrameContext",
    "SimulationStep",
    "SimulationStepScheduler",
]
