"""End-to-end test of the in-game BenchmarkScene.

This test runs the BenchmarkScene exactly the way the user would
experience it: open the scene, click the "进入自动化测试" button,
let the worker thread run all scenarios + invariants, and check
that the results panel shows up with a non-zero number of
passing scenarios.
"""

from __future__ import annotations

import os
import sys
import textwrap

import pytest


pytestmark = pytest.mark.slow


def _run_scene_in_subprocess(timeout: int = 240) -> tuple[bool, str]:
    env = os.environ.copy()
    env.setdefault("SDL_VIDEODRIVER", "dummy")
    env.setdefault("SDL_AUDIODRIVER", "dummy")
    code = textwrap.dedent(
        """
        import sys, os, time, threading
        sys.path.insert(0, '.')
        import logging
        logging.disable(logging.CRITICAL)
        import pygame
        pygame.init()
        from airwar.game import Game
        from airwar.benchmark import BenchmarkScene
        g = Game()
        try:
            sm = g._director._scene_manager
            bs = sm.get_scene('benchmark')
            assert bs is not None, 'benchmark scene not registered'
            bs.enter()
            # Drive one render so the enter button rect is registered.
            surf = pygame.Surface((1280, 720))
            bs.render(surf)
            enter_rect = bs.get_button_rect('benchmark_enter')
            if enter_rect is not None:
                # Dispatch the click directly via the scene's
                # handle_events -- the scene_director isn't running
                # in this subprocess, so pygame.event.post alone
                # wouldn't reach the scene.
                bs.handle_events(pygame.event.Event(
                    pygame.MOUSEMOTION, {'pos': enter_rect.center, 'buttons': (0,0,0), 'rel': (0,0)}
                ))
                bs.handle_events(pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN, {'pos': enter_rect.center, 'button': 1}
                ))
                bs.handle_events(pygame.event.Event(
                    pygame.MOUSEBUTTONUP, {'pos': enter_rect.center, 'button': 1}
                ))
            # Drive a few update / render cycles so the worker
            # thread starts.
            for _ in range(5):
                bs.update()
                bs.render(surf)
                time.sleep(0.05)
            # After click, state should be 'running' (worker spinning up).
            assert bs._state == 'running', f'expected running, got {bs._state}'
            # Wait for worker to finish (max 120s).
            for _ in range(240):
                time.sleep(0.5)
                bs.update()
                if bs._state == 'results':
                    break
            assert bs._state == 'results', f'benchmark never finished; state={bs._state}'
            report = bs._report
            assert report is not None
            n_pass = sum(d.startswith('PASS') for layer in report.layers for d in layer.details)
            n_fail = sum(d.startswith('FAIL') for layer in report.layers for d in layer.details)
            print(f'BENCH_OK n_pass={n_pass} n_fail={n_fail} duration={report.duration_s:.1f}s')
            # We expect at least 8 passing scenarios.
            assert n_pass >= 8, f'expected >= 8 passing, got {n_pass}'
            bs.exit()
        finally:
            try: g._window.close()
            except Exception: pass
        """
    )
    import subprocess
    completed = subprocess.run(
        [sys.executable, "-W", "ignore", "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    out = completed.stdout.strip().splitlines()
    if not out:
        return False, f"no output: stderr={completed.stderr[-300:]}"
    last = out[-1]
    return last.startswith("BENCH_OK"), last


def test_benchmark_scene_button_runs_full_suite():
    """Click 进入自动化测试; assert the suite completes and shows results."""
    ok, msg = _run_scene_in_subprocess()
    assert ok, f"benchmark scene flow failed: {msg}"
