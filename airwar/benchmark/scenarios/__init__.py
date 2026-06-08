"""Scenario registry and per-scenario driver.

A :class:`Scenario` is a declarative spec: a name, a frame budget,
an optional input schedule, and an assertion function.  The driver
function :func:`run_scenario` builds a :class:`ScenarioRunner` and
executes the spec, returning a :class:`ScenarioResult`.

Adding a new scenario means appending an entry to :data:`ALL_SCENARIOS`
(or a new module under :mod:`airwar.benchmark.scenarios` that exports
its list); both the pytest entry point and the in-game launcher pick
it up automatically.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Sequence

import pygame

from ..harness import InputEvent, ScenarioResult, ScenarioRunner

logger = logging.getLogger(__name__)


@dataclass
class Scenario:
    """A single end-to-end test scenario.

    Attributes:
        name: Identifier; used in test names and report lines.
        inputs: Pre-scheduled :class:`InputEvent` to feed into the run.
        frames: Maximum number of frames to advance.
        assert_fn: Callable taking the :class:`ScenarioResult` and
            returning either ``None`` (pass) or a string (fail with
            that message).  May also raise ``AssertionError``.
        on_setup: Optional callable taking the :class:`ScenarioRunner`
            after ``setup()`` has run; use to register
            ``on_frame`` callbacks.
    """

    name: str
    frames: int = 200
    inputs: list[InputEvent] = field(default_factory=list)
    assert_fn: Callable[[ScenarioResult], str | None] = lambda r: None
    on_setup: Callable[["ScenarioRunner"], None] | None = None


def run_scenario(
    scenario: Scenario,
    game,
    *,
    max_frames: int = 600,
) -> ScenarioResult:
    """Execute ``scenario`` against a freshly-constructed ``game``.

    Args:
        scenario: The spec to run.
        game: A live :class:`airwar.game.Game` instance.  Usually a
            fresh one from the factory; do not reuse across scenarios.
        max_frames: Hard cap; supersedes ``scenario.frames`` if smaller.

    Returns:
        A :class:`ScenarioResult`.  ``passed`` is ``True`` iff the
        assertion function returned ``None`` (or didn't raise).
    """
    runner = ScenarioRunner(game, max_frames=min(scenario.frames, max_frames), target_scene="game")
    runner.setup()
    if scenario.on_setup is not None:
        try:
            scenario.on_setup(runner)
        except Exception as exc:  # noqa: BLE001
            return ScenarioResult(
                name=scenario.name,
                passed=False,
                snapshots=[],
                error=exc,
                frames_run=0,
                message=f"on_setup raised: {exc!r}",
            )
    runner.feed_all(scenario.inputs)
    try:
        runner.advance(runner.max_frames)
        result = ScenarioResult(
            name=scenario.name,
            passed=True,
            snapshots=runner.snapshots,
            frames_run=runner.frame,
        )
    except Exception as exc:  # noqa: BLE001
        result = ScenarioResult(
            name=scenario.name,
            passed=False,
            snapshots=runner.snapshots,
            error=exc,
            frames_run=runner.frame,
        )
        return result

    try:
        msg = scenario.assert_fn(result)
    except AssertionError as exc:
        msg = str(exc) or "assertion failed"
    except Exception as exc:  # noqa: BLE001
        msg = f"assert_fn raised: {exc!r}"
    if msg is not None:
        result.passed = False
        result.message = msg
    return result


# -- Default scenario list (built up by sibling modules) -----------------


ALL_SCENARIOS: list[Scenario] = []


def register(*scenarios: Scenario) -> None:
    """Append ``scenarios`` to :data:`ALL_SCENARIOS` (idempotent by name)."""
    existing = {s.name for s in ALL_SCENARIOS}
    for s in scenarios:
        if s.name not in existing:
            ALL_SCENARIOS.append(s)
            existing.add(s.name)


# Import side-effect modules so their ``register(...)`` calls fire.
from . import (  # noqa: E402, F401
    basic as _basic,
    pause as _pause,
    death as _death,
    mothership as _mothership,
    boss as _boss,
    save_load as _save_load,
)
