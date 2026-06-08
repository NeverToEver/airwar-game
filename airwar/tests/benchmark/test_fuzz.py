"""Fuzz / stress test: random inputs over many frames.

The fuzz driver picks a random subset of inputs to post each frame
(KEYDOWN/KEYUP for movement, MOD keys, pause, mothership; MOUSEMOTION
with random positions).  After running for the requested frame budget,
the test asserts that no exception escaped the harness and the game
ended in a sane scene.

A second test exercises lock-layer concurrency: we acquire
``MOTHERSHIP`` + ``GAME_PAUSE`` simultaneously via the
:func:`airwar.game.systems.lock_manager.LockManager` and run the
game for 60 frames.  This catches the class of bug where two
high-priority lock sources produce an inconsistent game_state.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap

import pytest


pytestmark = pytest.mark.slow


# -- Fuzz driver ---------------------------------------------------------


def _run_fuzz_subprocess(frames: int, seed: int, timeout: int = 300) -> tuple[bool, str]:
    env = os.environ.copy()
    env.setdefault("SDL_VIDEODRIVER", "dummy")
    env.setdefault("SDL_AUDIODRIVER", "dummy")
    code = textwrap.dedent(
        f"""
        import sys, os, random
        sys.path.insert(0, '.')
        import logging
        logging.disable(logging.CRITICAL)
        import pygame
        pygame.init()
        random.seed({seed})
        from airwar.game import Game
        from airwar.benchmark.harness import ScenarioRunner
        g = Game()
        try:
            runner = ScenarioRunner(g, max_frames={frames}+5, target_scene='game', seed={seed})
            runner.setup()
            KEYS = [pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d,
                    pygame.K_h, pygame.K_k, pygame.K_b,
                    pygame.K_LSHIFT, pygame.K_LCTRL,
                    pygame.K_SPACE, pygame.K_ESCAPE]
            for f in range({frames}):
                if random.random() < 0.6:
                    k = random.choice(KEYS)
                    kind = pygame.KEYDOWN if random.random() < 0.3 else pygame.KEYUP
                    pygame.event.post(pygame.event.Event(
                        kind, {{'key': k, 'mod': 0, 'unicode': '', 'scancode': 0}}
                    ))
                if random.random() < 0.7:
                    x = random.randint(0, 1920)
                    y = random.randint(0, 1080)
                    pygame.event.post(pygame.event.Event(
                        pygame.MOUSEMOTION,
                        {{'pos': (x, y), 'buttons': (0,0,0), 'rel': (0,0)}},
                    ))
                runner.advance(1)
            last = runner.snapshots[-1] if runner.snapshots else None
            scene = last.scene_name if last else '?'
            locks = list(last.active_lock_layers) if last else []
            print(f'FUZZ_OK {{scene}} {{len(locks)}} {{len(runner.snapshots)}}')
        except Exception as e:
            print(f'FUZZ_FAIL {{e!r}}')
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
    out = completed.stdout.strip().splitlines()
    if not out:
        return False, f"no output: stderr={completed.stderr[-300:]}"
    last = out[-1]
    if last.startswith("FUZZ_OK"):
        return True, last
    return False, last


def test_fuzz_120_frames():
    """120 frames of random input must not crash the game."""
    ok, msg = _run_fuzz_subprocess(frames=120, seed=1)
    assert ok, f"fuzz failed: {msg}"


def test_fuzz_seed_variation():
    """Run fuzz with several different seeds; all must complete."""
    for seed in (1, 7, 42, 99, 1234):
        ok, msg = _run_fuzz_subprocess(frames=120, seed=seed)
        assert ok, f"fuzz seed={seed} failed: {msg}"


# -- Lock-layer concurrency matrix --------------------------------------


def _run_lock_concurrency(layers: list[str], frames: int = 60, timeout: int = 120) -> tuple[bool, str]:
    env = os.environ.copy()
    env.setdefault("SDL_VIDEODRIVER", "dummy")
    env.setdefault("SDL_AUDIODRIVER", "dummy")
    code = textwrap.dedent(
        f"""
        import sys, os
        sys.path.insert(0, '.')
        import logging
        logging.disable(logging.CRITICAL)
        import pygame
        pygame.init()
        from airwar.game import Game
        from airwar.benchmark.harness import ScenarioRunner
        g = Game()
        try:
            runner = ScenarioRunner(g, max_frames={frames}+5, target_scene='game')
            runner.setup()
            from airwar.game.systems.lock_manager import LockLayer, LockRequest
            scene = runner.current_scene()
            layer_objs = {{'MOTHERSHIP': LockLayer.MOTHERSHIP,
                          'GAME_PAUSE': LockLayer.GAME_PAUSE,
                          'PHASE_DASH': LockLayer.PHASE_DASH,
                          'BOSS_ENRAGE': LockLayer.BOSS_ENRAGE}}
            reqs = {{'MOTHERSHIP': LockRequest(invincible=True, lock_controls=True, is_silent_invincible=True),
                    'GAME_PAUSE': LockRequest(is_paused=True, invincible=False),
                    'PHASE_DASH': LockRequest(invincible=True, lock_controls=True),
                    'BOSS_ENRAGE': LockRequest(invincible=True, lock_controls=True)}}
            for name in {layers!r}:
                scene._lock_manager.acquire(layer_objs[name], reqs[name])
            for _ in range({frames}):
                runner.advance(1)
            active = list(runner.snapshots[-1].active_lock_layers) if runner.snapshots else []
            print(f'LOCKS_OK {{active}}')
        except Exception as e:
            import traceback
            print(f'LOCKS_FAIL {{e!r}}')
            traceback.print_exc()
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
    out = completed.stdout.strip().splitlines()
    if not out:
        return False, f"no output: stderr={completed.stderr[-200:]}"
    last = out[-1]
    return last.startswith("LOCKS_OK"), last


@pytest.mark.parametrize(
    "layers",
    [
        ["MOTHERSHIP", "GAME_PAUSE"],
        ["PHASE_DASH", "GAME_PAUSE"],
        ["BOSS_ENRAGE", "MOTHERSHIP"],
        ["MOTHERSHIP", "PHASE_DASH", "GAME_PAUSE"],
    ],
)
def test_lock_layer_concurrency(layers):
    """Multiple high-priority lock layers must coexist without raising."""
    ok, msg = _run_lock_concurrency(layers, frames=60)
    assert ok, f"lock concurrency {layers} failed: {msg}"
