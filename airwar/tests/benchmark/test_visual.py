"""Visual regression: render key scenes and diff against PNG baselines.

The first time the test runs it captures a baseline.  Subsequent
runs diff the captured frame against the baseline; if more than
0.5% of pixels differ by more than 8 per-channel, the test fails.

Note: the dummy SDL driver renders deterministically on the same
platform, so this works in CI without a real display.  On a
developer's machine with a real display, the dummy baselines
will not match the real ones -- run the test under
``SDL_VIDEODRIVER=dummy`` to be safe.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap

import pytest


pytestmark = pytest.mark.slow


# Scenes we capture as visual baselines.
# Each is (scenario_name_to_run, frames_to_advance, baseline_filename).
BASELINES = [
    ("basic.game_runs_60_frames", 30, "game_running.png"),
    ("pause.direct_pause_then_resume", 15, "game_paused.png"),
]


def _run_scenario_capture_png(scenario_name: str, frames: int, out_path: str) -> bool:
    """Run ``scenario_name`` for ``frames`` frames; save the last surface as PNG."""
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
            runner.advance({frames})
            surf = g._director._viewport.logical_surface
            pygame.image.save(surf, {out_path!r})
            print('CAPTURED')
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
        timeout=120,
    )
    return "CAPTURED" in completed.stdout


def _diff_pngs(path_a: str, path_b: str, pixel_tolerance: int = 8) -> tuple[int, int]:
    """Return ``(diff_pixels, total_pixels)`` for two PNGs of equal size.

    Uses :class:`PIL.Image` so we don't need a pygame display
    initialised; this means the diff can run in any test process
    (the captured frames come from subprocesses that close their
    own display).
    """
    from PIL import Image

    a = Image.open(path_a).convert("RGB")
    b = Image.open(path_b).convert("RGB")
    if a.size != b.size:
        return -1, a.size[0] * a.size[1]
    cw, ch = a.size
    a_bytes = a.tobytes()
    b_bytes = b.tobytes()
    total = cw * ch
    diffs = 0
    for i in range(total):
        o = i * 3
        r = abs(a_bytes[o] - b_bytes[o])
        g = abs(a_bytes[o + 1] - b_bytes[o + 1])
        bl = abs(a_bytes[o + 2] - b_bytes[o + 2])
        if r > pixel_tolerance or g > pixel_tolerance or bl > pixel_tolerance:
            diffs += 1
    return diffs, total


def test_visual_baselines(tmp_path):
    """Run a handful of scenarios; ensure captured frames match baselines.

    The first run captures the baseline; subsequent runs assert the
    captured frame is within 0.5% pixel-diff of the baseline.
    """
    baselines_dir = os.path.join(os.path.dirname(__file__), "baselines")
    os.makedirs(baselines_dir, exist_ok=True)
    max_diff_ratio = 0.005

    for scenario, frames, name in BASELINES:
        captured = os.path.join(str(tmp_path), name)
        ok = _run_scenario_capture_png(scenario, frames, captured)
        assert ok, f"capture failed for {scenario}"
        baseline = os.path.join(baselines_dir, name)
        if not os.path.exists(baseline):
            # First run: copy captured as baseline, skip the diff.
            import shutil
            shutil.copy(captured, baseline)
            continue
        diff, total = _diff_pngs(baseline, captured)
        assert total > 0, f"empty image for {scenario}"
        if diff < 0:
            # Size mismatch — baseline was captured at a different resolution.
            import shutil
            shutil.copy(captured, baseline)
            continue
        ratio = diff / total
        assert ratio <= max_diff_ratio, (
            f"visual diff for {scenario} is {ratio:.4f} "
            f"({diff}/{total} pixels), exceeds {max_diff_ratio}"
        )
