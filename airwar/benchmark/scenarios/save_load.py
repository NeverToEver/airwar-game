"""Save / load round-trip scenarios.

These exercise the persistence stack end-to-end against a real Game
instance: mutate the game state, call the public
``perform_save`` / ``check_and_get_saved_game`` APIs, then assert
the data round-trips.
"""

from __future__ import annotations

from ..harness import ScenarioResult
from . import Scenario, register


SCENARIOS: list[Scenario] = []


def _assert_game_stable(result: ScenarioResult) -> str | None:
    if not result.snapshots:
        return "no snapshots"
    first = result.snapshots[0]
    if first.scene_name != "game":
        return f"expected to start in 'game' scene, got '{first.scene_name}'"
    return None


SCENARIOS.append(
    Scenario(
        name="save_load.game_stable_for_save_window",
        frames=40,
        inputs=[],
        assert_fn=_assert_game_stable,
    )
)


def _build_score_roundtrip() -> Scenario:
    """Save the game with a custom score, reload, verify it round-tripped."""

    def _on_setup(runner) -> None:
        director = runner.game._director
        scene = runner.current_scene()
        if scene is None or scene.player is None:
            return

        def _do_round_trip(runner, frame: int) -> None:
            if frame != 5:
                return
            try:
                scene.game_controller.set_score(12345)
                scene.player.health = 77
            except Exception:
                return
            try:
                director._perform_save(scene)
                saved = director._check_and_get_saved_game(director._current_user or "benchmark")
                if saved is None:
                    runner._scenario_error = "save returned None"
                    return
                if saved.score != 12345:
                    runner._scenario_error = f"score did not round-trip: got {saved.score}"
                    return
            except Exception as exc:  # noqa: BLE001
                runner._scenario_error = f"save/load raised: {exc!r}"

        runner.on_frame(_do_round_trip)

    def _assert(result: ScenarioResult) -> str | None:
        err = getattr(result, "_scenario_error", None)
        if err:
            return err
        return _assert_game_stable(result)

    return Scenario(
        name="save_load.score_round_trips_via_persistence_manager",
        frames=20,
        inputs=[],
        on_setup=_on_setup,
        assert_fn=_assert,
    )


SCENARIOS.append(_build_score_roundtrip())


for s in SCENARIOS:
    register(s)
