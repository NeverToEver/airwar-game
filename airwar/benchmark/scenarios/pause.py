"""Pause / resume scenario.

Exercises GameScene.pause() and GameScene.resume() via the harness
``on_frame`` hook.  ESC pause is wired through SceneDirector which
the benchmark harness bypasses; calling pause/resume directly still
exercises the same GameController state flip.
"""

from __future__ import annotations


from ..harness import ScenarioResult
from . import Scenario, register


SCENARIOS: list[Scenario] = []


def _build_pause_resume() -> Scenario:
    """Pause at frame 10, resume at frame 30, assert both states are seen."""

    def _assert(result: ScenarioResult) -> str | None:
        paused = [s for s in result.snapshots if s.is_paused is True]
        unpaused = [s for s in result.snapshots if s.is_paused is False]
        if not paused:
            return "no paused snapshot observed"
        if not unpaused:
            return "no unpaused snapshot observed (resume never took effect)"
        first_pause = paused[0].frame
        if first_pause <= 8:
            return f"pause happened too early: frame {first_pause}"
        resume_after = next(
            (s.frame for s in result.snapshots if s.frame > first_pause and s.is_paused is False),
            None,
        )
        if resume_after is None or resume_after <= 28:
            return f"resume didn't happen after frame 30: first={resume_after}"
        return None

    return Scenario(
        name="pause.direct_pause_then_resume",
        frames=60,
        inputs=[],
        on_setup=lambda runner: (
            runner.on_frame(_pause_at_10_then_resume_at_30),
        ),
        assert_fn=_assert,
    )


def _pause_at_10_then_resume_at_30(runner, frame: int) -> None:
    scene = runner.current_scene()
    if scene is None:
        return
    if frame == 10:
        _safe_call(scene, "pause")
    elif frame == 30:
        _safe_call(scene, "resume")


def _safe_call(obj, attr: str) -> None:
    fn = getattr(obj, attr, None)
    if callable(fn):
        try:
            fn()
        except Exception:
            pass


SCENARIOS.append(_build_pause_resume())


for s in SCENARIOS:
    register(s)
