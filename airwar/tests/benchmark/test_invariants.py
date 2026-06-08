"""Invariant suite: property checks applied to a stream of snapshots.

We run each scenario in its own subprocess (because the SDL dummy
driver only allows one window per process), collect snapshots to a
file, then run the invariant suite over the concatenated stream.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap

import pytest


pytestmark = pytest.mark.slow


def _run_scenario_dump_snapshots(scenario_name: str, output_path: str, timeout: int = 120) -> bool:
    """Run a single scenario and dump snapshots to ``output_path`` as JSON."""
    env = os.environ.copy()
    env.setdefault("SDL_VIDEODRIVER", "dummy")
    env.setdefault("SDL_AUDIODRIVER", "dummy")
    code = textwrap.dedent(
        f"""
        import sys, json
        sys.path.insert(0, '.')
        import logging
        logging.disable(logging.CRITICAL)
        import pygame
        pygame.init()
        from airwar.benchmark.scenarios import ALL_SCENARIOS, run_scenario
        for mod in ('basic','pause','death','mothership','boss','save_load'):
            __import__('airwar.benchmark.scenarios.' + mod, fromlist=['*'])
        from airwar.game import Game
        target = next((s for s in ALL_SCENARIOS if s.name == {scenario_name!r}), None)
        if target is None:
            sys.exit(0)
        g = Game()
        try:
            res = run_scenario(target, g, max_frames=target.frames)
            snaps_dicts = [s.to_dict() for s in res.snapshots]
            with open({output_path!r}, 'w') as f:
                json.dump({{
                    'scenario': {scenario_name!r},
                    'passed': res.passed,
                    'message': res.message,
                    'frames_run': res.frames_run,
                    'snapshots': snaps_dicts,
                }}, f)
        finally:
            try: g._window.close()
            except Exception: pass
        """
    )
    completed = subprocess.run(
        [sys.executable, "-W", "ignore", "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return completed.returncode == 0


def _collect_all_snapshots() -> list[dict]:
    """Run every scenario in a fresh subprocess; return concatenated snapshot dicts."""
    from airwar.benchmark.scenarios import ALL_SCENARIOS

    all_snaps: list[dict] = []
    failed_scenarios: list[str] = []
    for s in ALL_SCENARIOS:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            ok = _run_scenario_dump_snapshots(s.name, path)
            if not ok or not os.path.exists(path):
                failed_scenarios.append(s.name)
                continue
            with open(path) as f:
                data = json.load(f)
            if not data.get("passed", False):
                failed_scenarios.append(f"{data.get('scenario')}: {data.get('message')}")
            all_snaps.extend(data.get("snapshots", []))
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
    return all_snaps, failed_scenarios


def test_invariants_across_all_scenarios():
    """Run all scenarios in subprocesses; assert invariant suite passes."""
    from airwar.benchmark.snapshot import GameSnapshot
    from airwar.benchmark.invariants import InvariantSuite

    all_snaps_dicts, failed = _collect_all_snapshots()
    assert not failed, f"scenarios failed: {failed}"

    snapshots = [GameSnapshot(**d) for d in all_snaps_dicts]
    suite = InvariantSuite()
    violations = suite.check_all(snapshots)
    assert not violations, (
        "invariant violations: "
        + "; ".join(f"{v.rule}@frame{v.frame}: {v.message[:120]}" for v in violations[:10])
    )
