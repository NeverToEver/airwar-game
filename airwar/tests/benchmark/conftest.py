"""Pytest fixtures for the benchmark suite.

Each scenario gets a fresh ``Game`` instance via the ``fresh_game``
fixture so scenarios don't leak state into each other.  Tests are
run in a separate process (one per scenario) to avoid the SDL dummy
driver's one-window-per-process limit.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap

import pytest


SCENARIOS_PACKAGE = "airwar.benchmark.scenarios"


def _import_scenarios():
    """Import the scenarios package and all side-effect modules."""
    import importlib

    import airwar.benchmark.scenarios as pkg

    for mod in (
        "basic",
        "pause",
        "death",
        "mothership",
        "boss",
        "save_load",
    ):
        importlib.import_module(f"{SCENARIOS_PACKAGE}.{mod}")
    return pkg


def _run_in_subprocess(scenario_name: str, timeout: int = 120) -> tuple[bool, str, int]:
    """Run ``scenario_name`` in a fresh Python subprocess.

    Returns (passed, message, frames_run).
    """
    env = os.environ.copy()
    env.setdefault("SDL_VIDEODRIVER", "dummy")
    env.setdefault("SDL_AUDIODRIVER", "dummy")
    code = textwrap.dedent(
        f"""
        import sys
        sys.path.insert(0, '.')
        import logging
        logging.disable(logging.CRITICAL)
        import pygame
        pygame.init()
        from airwar.game import Game
        from airwar.benchmark.scenarios import ALL_SCENARIOS, run_scenario
        for mod in ('basic','pause','death','mothership','boss','save_load'):
            __import__('airwar.benchmark.scenarios.' + mod, fromlist=['*'])
        target = next((s for s in ALL_SCENARIOS if s.name == {scenario_name!r}), None)
        if target is None:
            print('NOT_FOUND'); sys.exit(0)
        g = Game()
        try:
            res = run_scenario(target, g, max_frames=target.frames)
            flag = 'PASS' if res.passed else 'FAIL'
            print(f'{{flag}} {{res.frames_run}} {{res.message or ""}}')
        finally:
            try:
                g._window.close()
            except Exception:
                pass
        """
    )
    completed = subprocess.run(
        [sys.executable, "-W", "ignore", "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    out = completed.stdout.strip().splitlines()
    last = out[-1] if out else "FAIL 0 crashed"
    parts = last.split(maxsplit=2)
    if len(parts) >= 2 and parts[0] in ("PASS", "FAIL"):
        passed = parts[0] == "PASS"
        try:
            frames = int(parts[1])
        except ValueError:
            frames = 0
        msg = parts[2] if len(parts) > 2 else ""
        return passed, msg, frames
    return False, last, 0


def pytest_generate_tests(metafunc):
    """Parametrize ``test_*`` over the registered scenario names."""
    if "scenario_name" in metafunc.fixturenames:
        pkg = _import_scenarios()
        names = sorted(s.name for s in pkg.ALL_SCENARIOS)
        metafunc.parametrize("scenario_name", names)


@pytest.fixture
def run_scenario_in_subprocess():
    """Return a function that runs a single scenario in a subprocess."""
    return _run_in_subprocess


@pytest.fixture(scope="session")
def all_scenarios():
    """Return the list of registered scenarios."""
    pkg = _import_scenarios()
    return list(pkg.ALL_SCENARIOS)
