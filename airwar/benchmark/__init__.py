"""End-to-end game-flow benchmark suite.

Drives a real :class:`airwar.game.Game` instance frame-by-frame, takes
state snapshots, runs scenarios, asserts invariants, and (optionally)
compares rendered frames against visual baselines.  Exposes two entry
points:

* **pytest** -- ``airwar/tests/benchmark/test_*.py`` runs each layer
  (``scenarios``, ``invariants``, ``fuzz``, ``visual``) as a regular
  test module.
* **In-game launcher** -- :class:`airwar.benchmark.scene.BenchmarkScene`
  registers a scene with a "进入自动化测试" button that, when clicked,
  runs the same suite and shows the result panel.

Public surface (re-exported here for convenience):
* :class:`GameSnapshot` -- frozen state reading.
* :class:`ScenarioRunner` -- frame-accurate driver.
* :func:`run_all` -- top-level entry that the in-game launcher calls.
* :class:`BenchmarkScene` -- the in-game launcher scene.
"""

from .snapshot import GameSnapshot, take_snapshot
from .harness import ScenarioRunner, ScenarioResult
from .runner import run_all, BenchmarkReport, LayerResult
from .scene import BenchmarkScene

__all__ = [
    "GameSnapshot",
    "take_snapshot",
    "ScenarioRunner",
    "ScenarioResult",
    "run_all",
    "BenchmarkReport",
    "LayerResult",
    "BenchmarkScene",
]
