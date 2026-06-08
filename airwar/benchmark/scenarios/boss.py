"""Boss lifecycle scenarios.

Boss doesn't spawn until the spawn timer expires (default 1800
frames = 30s).  Driving that long is wasteful, so we trigger boss
spawn by directly calling ``SpawnController.spawn_boss`` after a
few frames and assert the game handles it without crashing.
"""

from __future__ import annotations

from ..harness import ScenarioResult
from . import Scenario, register


SCENARIOS: list[Scenario] = []


def _assert_no_boss_yet(result: ScenarioResult) -> str | None:
    if not result.snapshots:
        return "no snapshots"
    snaps_with_boss = [s for s in result.snapshots if s.boss_state is not None]
    if snaps_with_boss:
        return f"unexpected boss appeared: {snaps_with_boss[0].to_dict()}"
    return None


SCENARIOS.append(
    Scenario(
        name="boss.no_spawn_in_first_120_frames",
        frames=120,
        inputs=[],
        assert_fn=_assert_no_boss_yet,
    )
)


def _build_boss_appears() -> Scenario:
    """Force-spawn a boss at frame 30; assert game survives 60 more frames."""

    def _assert(result: ScenarioResult) -> str | None:
        boss_snaps = [s for s in result.snapshots if s.boss_state is not None]
        if not boss_snaps:
            return "boss never appeared after force-spawn"
        # After spawn, the game should remain stable.
        later = [s for s in result.snapshots if s.frame > boss_snaps[0].frame + 30]
        if not later:
            return "not enough frames after boss spawn to check stability"
        last = later[-1]
        if last.scene_name not in ("game", "death"):
            return f"unexpected scene after boss spawn: {last.scene_name}"
        return None

    def _on_setup(runner) -> None:
        def _spawn_boss(runner, frame: int) -> None:
            if frame != 30:
                return
            scene = runner.current_scene()
            if scene is None:
                return
            spawn = getattr(scene, "spawn_controller", None)
            if spawn is None:
                return
            try:
                # boss_kill_count=0 -> first boss; bullet_damage/player_dps
                # match the player's normal bullet / DPS.
                spawn.spawn_boss(boss_kill_count=0, bullet_damage=10, player_dps=20.0)
            except Exception:
                pass

        runner.on_frame(_spawn_boss)

    return Scenario(
        name="boss.force_spawn_does_not_crash",
        frames=90,
        inputs=[],
        on_setup=_on_setup,
        assert_fn=_assert,
    )


SCENARIOS.append(_build_boss_appears())


for s in SCENARIOS:
    register(s)
