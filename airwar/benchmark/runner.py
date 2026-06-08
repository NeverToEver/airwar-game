"""Top-level orchestrator that the in-game launcher / pytest entry point share.

Provides :func:`run_all` which executes every registered scenario,
then runs the invariant suite over the union of all snapshots,
then runs a short fuzz pass, then (optionally) checks visual
baselines.  Returns a :class:`BenchmarkReport` summarising the
outcome.  The same function is used by the BenchmarkScene in-game
button and by ``airwar/tests/benchmark/test_smoke.py`` so the two
entry points can't drift.
"""

from __future__ import annotations

import logging
import time
import traceback
from dataclasses import dataclass, field
from typing import Sequence

from .harness import ScenarioResult
from .scenarios import ALL_SCENARIOS, run_scenario
from .snapshot import GameSnapshot
from .invariants import InvariantSuite
from .visual import VisualDiff

logger = logging.getLogger(__name__)


@dataclass
class LayerResult:
    """Outcome of one benchmark layer (scenarios, invariants, ...).

    Attributes:
        name: Layer identifier.
        passed: ``True`` iff no entry in this layer failed.
        details: Human-readable list of pass/fail lines.
        duration_s: Wall-clock seconds the layer took.
    """

    name: str
    passed: bool
    details: list[str] = field(default_factory=list)
    duration_s: float = 0.0


@dataclass
class BenchmarkReport:
    """Aggregate report from a full benchmark run.

    Attributes:
        passed: ``True`` iff every layer passed.
        layers: Per-layer results in the order they ran.
        snapshots: Concatenated snapshot list from all scenarios,
            in execution order.  Useful for post-hoc inspection or
            for the in-game renderer to scroll through.
    """

    passed: bool
    layers: list[LayerResult] = field(default_factory=list)
    snapshots: list[GameSnapshot] = field(default_factory=list)
    duration_s: float = 0.0

    def summary_line(self) -> str:
        """Return a one-line human summary."""
        counts = {"pass": 0, "fail": 0}
        for layer in self.layers:
            for d in layer.details:
                if d.startswith("PASS"):
                    counts["pass"] += 1
                elif d.startswith("FAIL"):
                    counts["fail"] += 1
        verdict = "PASS" if self.passed else "FAIL"
        return f"[{verdict}] {counts['pass']} passed, {counts['fail']} failed in {self.duration_s:.1f}s"


def run_all(
    game_factory,
    *,
    max_frames_per_scenario: int = 600,
    layers: Sequence[str] = ("scenarios", "invariants", "fuzz", "visual"),
    visual_baselines_dir: str | None = None,
    fuzz_frames: int = 60,
) -> BenchmarkReport:
    """Run the full benchmark suite against a freshly-built game.

    Args:
        game_factory: Zero-arg callable that returns a fresh
            :class:`airwar.game.Game` instance.  Each scenario
            gets its own instance so scenarios don't leak state
            into each other.
        max_frames_per_scenario: Frame cap for each scenario.
        layers: Which layers to run (subset of
            ``"scenarios"``, ``"invariants"``, ``"fuzz"``, ``"visual"``).
        visual_baselines_dir: Directory holding PNG baselines.  If
            ``None`` or the directory is empty, the visual layer is
            skipped (this is the default for the in-game button).
        fuzz_frames: Number of frames to advance under random input
            for the fuzz layer.

    Returns:
        A :class:`BenchmarkReport`.
    """
    started = time.monotonic()
    report_layers: list[LayerResult] = []
    all_snapshots: list[GameSnapshot] = []

    if "scenarios" in layers:
        layer = _run_scenarios_layer(game_factory, max_frames_per_scenario, all_snapshots)
        report_layers.append(layer)

    if "invariants" in layers:
        layer = _run_invariants_layer(all_snapshots)
        report_layers.append(layer)

    if "fuzz" in layers:
        layer = _run_fuzz_layer(game_factory, fuzz_frames, all_snapshots)
        report_layers.append(layer)

    if "visual" in layers and visual_baselines_dir:
        layer = _run_visual_layer(game_factory, visual_baselines_dir, all_snapshots)
        report_layers.append(layer)

    overall_passed = all(layer.passed for layer in report_layers)
    return BenchmarkReport(
        passed=overall_passed,
        layers=report_layers,
        snapshots=all_snapshots,
        duration_s=time.monotonic() - started,
    )


# -- Layer runners --------------------------------------------------------


def _run_scenarios_layer(
    game_factory,
    max_frames: int,
    snapshots_out: list[GameSnapshot],
) -> LayerResult:
    started = time.monotonic()
    details: list[str] = []
    failed = 0
    for scenario in ALL_SCENARIOS:
        game = game_factory()
        try:
            result = run_scenario(scenario, game, max_frames=max_frames)
        except Exception as exc:  # noqa: BLE001
            result = ScenarioResult(
                name=scenario.name,
                passed=False,
                error=exc,
                message=f"setup error: {exc!r}",
            )
        snapshots_out.extend(result.snapshots)
        if result.passed:
            details.append(f"PASS  {scenario.name}  ({len(result.snapshots)} frames)")
        else:
            failed += 1
            err_repr = repr(result.error) if result.error else result.message
            details.append(f"FAIL  {scenario.name}  {err_repr}")
    return LayerResult(
        name="scenarios",
        passed=failed == 0,
        details=details,
        duration_s=time.monotonic() - started,
    )


def _run_invariants_layer(snapshots: list[GameSnapshot]) -> LayerResult:
    started = time.monotonic()
    suite = InvariantSuite()
    violations = suite.check_all(snapshots)
    details = [
        f"PASS  invariant:{name}  ({count} checks)"
        for name, count in suite.check_counts.items()
    ]
    if violations:
        for v in violations:
            details.append(f"FAIL  invariant:{v.rule}  frame={v.frame}  {v.message}")
    return LayerResult(
        name="invariants",
        passed=not violations,
        details=details,
        duration_s=time.monotonic() - started,
    )


def _run_fuzz_layer(
    game_factory,
    frames: int,
    snapshots_out: list[GameSnapshot],
) -> LayerResult:
    """Random input fuzz -- just check no exception is raised."""
    started = time.monotonic()
    from .harness import ScenarioRunner

    game = game_factory()
    runner = ScenarioRunner(game, max_frames=frames + 10, target_scene="game")
    runner.setup()
    try:
        snaps = runner.advance(frames)
        snapshots_out.extend(snaps)
        details = [f"PASS  fuzz  {frames} frames, no crash"]
        passed = True
    except Exception:  # noqa: BLE001
        details = [f"FAIL  fuzz  {traceback.format_exc(limit=2)}"]
        passed = False
    return LayerResult(
        name="fuzz",
        passed=passed,
        details=details,
        duration_s=time.monotonic() - started,
    )


def _run_visual_layer(
    game_factory,
    baselines_dir: str,
    snapshots_out: list[GameSnapshot],
) -> LayerResult:
    started = time.monotonic()
    diff = VisualDiff(baselines_dir=baselines_dir)
    results = diff.run(game_factory)
    details = [
        f"{'PASS' if r.passed else 'FAIL'}  visual:{r.name}  diff={r.diff_ratio:.4f}"
        for r in results
    ]
    return LayerResult(
        name="visual",
        passed=all(r.passed for r in results),
        details=details,
        duration_s=time.monotonic() - started,
    )
