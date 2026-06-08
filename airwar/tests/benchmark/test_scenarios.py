"""End-to-end scenario tests.

Each scenario runs in a fresh subprocess so the SDL dummy driver's
one-window-per-process limit doesn't bite.  Output is a single test
per scenario name; pass/fail is read from the subprocess's stdout.
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.slow


def test_scenario_runs(scenario_name: str, run_scenario_in_subprocess):
    """Run ``scenario_name``; assert it completed without failure."""
    passed, message, frames = run_scenario_in_subprocess(scenario_name)
    assert passed, f"scenario '{scenario_name}' failed: {message} (frames={frames})"
    assert frames > 0, f"scenario '{scenario_name}' produced no frames"


def test_all_scenarios_present(all_scenarios):
    """Sanity check: we expect at least the 5 main flow scenarios."""
    names = {s.name for s in all_scenarios}
    expected = {
        "basic.game_runs_60_frames",
        "pause.direct_pause_then_resume",
        "death.player_reaches_dead_state",
        "boss.force_spawn_does_not_crash",
        "save_load.score_round_trips_via_persistence_manager",
    }
    missing = expected - names
    assert not missing, f"missing scenarios: {missing}"
