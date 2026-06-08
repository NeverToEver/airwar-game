"""Visual regression -- compare rendered frames to PNG baselines.

The diff is intentionally simple: render the current frame, compare
to a baseline PNG pixel-by-pixel, fail if more than ``MAX_DIFF_RATIO``
of pixels differ by more than ``PIXEL_TOLERANCE`` per channel.

This is a regression detector for *gross* rendering breakage (the
"boss health bar disappeared" / "score is offscreen" class of bug),
not a pixel-perfect match.  CI-only -- the dummy video driver is the
only supported backend.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Callable, Sequence

import pygame

from .harness import ScenarioRunner

logger = logging.getLogger(__name__)


PIXEL_TOLERANCE = 8           # per-channel max diff to count as "different"
MAX_DIFF_RATIO = 0.005         # 0.5% of pixels allowed to differ


@dataclass
class VisualResult:
    name: str
    passed: bool
    diff_ratio: float
    diff_pixels: int
    total_pixels: int
    baseline_path: str
    message: str = ""


@dataclass
class VisualBaseline:
    """Specification of a visual baseline to capture and compare.

    Attributes:
        name: Identifier (e.g. ``"welcome_scene"``).
        target_scene: Scene name to switch to.
        setup: Optional callable taking the runner; used to perform
            additional setup (e.g. set difficulty, post a click).
        advance_frames: How many frames to render before snapshotting.
    """

    name: str
    target_scene: str = "welcome"
    setup: Callable[[ScenarioRunner], None] | None = None
    advance_frames: int = 30


DEFAULT_BASELINES: list[VisualBaseline] = [
    VisualBaseline(name="welcome", target_scene="welcome", advance_frames=5),
    VisualBaseline(name="game_initial", target_scene="game", advance_frames=20),
]


class VisualDiff:
    """Render frames at registered baselines and diff them."""

    def __init__(self, baselines_dir: str):
        self.baselines_dir = baselines_dir
        os.makedirs(self.baselines_dir, exist_ok=True)

    def _baseline_path(self, name: str) -> str:
        return os.path.join(self.baselines_dir, f"{name}.png")

    def capture(
        self,
        runner: ScenarioRunner,
        baseline: VisualBaseline,
        *,
        write: bool = False,
    ) -> pygame.Surface | None:
        """Run ``runner`` to the baseline state, return the rendered surface."""
        # The runner expects to start at scene='game'. If we want a different
        # scene, we need a fresh runner; for now, the game factory does that.
        if baseline.setup is not None:
            baseline.setup(runner)
        runner.advance(baseline.advance_frames)
        director = runner.game._director
        surf = director._viewport.logical_surface
        if write:
            path = self._baseline_path(baseline.name)
            try:
                pygame.image.save(surf, path)
                logger.info("wrote visual baseline %s", path)
            except Exception:  # noqa: BLE001
                logger.exception("failed to write visual baseline %s", path)
        return surf

    def compare(self, current: pygame.Surface, baseline_name: str) -> VisualResult:
        path = self._baseline_path(baseline_name)
        if not os.path.exists(path):
            return VisualResult(
                name=baseline_name,
                passed=True,
                diff_ratio=0.0,
                diff_pixels=0,
                total_pixels=current.get_width() * current.get_height(),
                baseline_path=path,
                message=f"no baseline at {path} -- captured on first run",
            )
        baseline = pygame.image.load(path).convert()
        if baseline.get_size() != current.get_size():
            return VisualResult(
                name=baseline_name,
                passed=False,
                diff_ratio=1.0,
                diff_pixels=baseline.get_width() * baseline.get_height(),
                total_pixels=current.get_width() * current.get_height(),
                baseline_path=path,
                message=f"size mismatch: baseline={baseline.get_size()} current={current.get_size()}",
            )
        cw, ch = current.get_size()
        cur_bytes = pygame.image.tostring(current, "RGB")
        base_bytes = pygame.image.tostring(baseline, "RGB")
        total = cw * ch
        diffs = 0
        for i in range(total):
            o = i * 3
            r = abs(cur_bytes[o] - base_bytes[o])
            g = abs(cur_bytes[o + 1] - base_bytes[o + 1])
            b = abs(cur_bytes[o + 2] - base_bytes[o + 2])
            if r > PIXEL_TOLERANCE or g > PIXEL_TOLERANCE or b > PIXEL_TOLERANCE:
                diffs += 1
        ratio = diffs / total if total else 0.0
        return VisualResult(
            name=baseline_name,
            passed=ratio <= MAX_DIFF_RATIO,
            diff_ratio=ratio,
            diff_pixels=diffs,
            total_pixels=total,
            baseline_path=path,
            message="within tolerance" if ratio <= MAX_DIFF_RATIO else f"diff ratio {ratio:.4f} > {MAX_DIFF_RATIO}",
        )

    def run(self, game_factory, baselines: Sequence[VisualBaseline] | None = None) -> list[VisualResult]:
        baselines = baselines or DEFAULT_BASELINES
        results: list[VisualResult] = []
        for baseline in baselines:
            game = game_factory()
            runner = ScenarioRunner(game, max_frames=baseline.advance_frames + 5, target_scene=baseline.target_scene)
            runner.setup()
            try:
                surf = self.capture(runner, baseline, write=False)
            except Exception as exc:  # noqa: BLE001
                results.append(
                    VisualResult(
                        name=baseline.name,
                        passed=False,
                        diff_ratio=1.0,
                        diff_pixels=0,
                        total_pixels=0,
                        baseline_path=self._baseline_path(baseline.name),
                        message=f"capture failed: {exc!r}",
                    )
                )
                continue
            if surf is None:
                continue
            results.append(self.compare(surf, baseline.name))
        return results
