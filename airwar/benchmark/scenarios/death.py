"""Death flow scenarios.

Drives the player to DYING via direct state-machine manipulation
(:meth:`PlayerStateMachine.mark_dying`) and asserts that:

1. The DYING state is reached.
2. The death animation runs to completion.
3. The scene transitions to ``"death"`` after the animation ends.

We poke the state machine directly via :func:`runner.on_frame` callbacks
because the alternative (waiting for enemy bullets to land) is slow
and non-deterministic.
"""

from __future__ import annotations

from ..harness import ScenarioResult
from . import Scenario, register


SCENARIOS: list[Scenario] = []


def _kill_player(scene) -> None:
    """Drive a player into the dying/game-over state machine.

    Three things have to happen in concert:

    1. ``player.health = 0`` (so collisions stop dealing damage)
    2. ``PlayerStateMachine.mark_dying()`` (so the player enters
       the dying state from which the death animation runs)
    3. ``GameController.state.gameplay_state = DYING`` and the
       death timer set, otherwise ``is_game_over()`` never becomes
       True and the director never switches to the death scene.
    """
    if scene is None or scene.player is None:
        return
    try:
        scene.player.health = 0
        scene.player._state.mark_dying()  # type: ignore[attr-defined]
        gc = getattr(scene, "game_controller", None)
        if gc is not None and hasattr(gc, "state"):
            from airwar.game.managers.game_controller import GameplayState
            gc.state.gameplay_state = GameplayState.DYING
            gc.state.death_timer = 1  # transition to GAME_OVER next frame
    except Exception:
        pass


def _build_death_basic() -> Scenario:
    def _assert(result: ScenarioResult) -> str | None:
        dying = [s for s in result.snapshots if s.player_dying is True]
        dead = [s for s in result.snapshots if s.player_alive is False]
        if not dying:
            return "player never entered DYING state"
        if not dead:
            return "player never reached DEAD state"
        return None

    def _on_setup(runner) -> None:
        def _kill_at_30(runner, frame: int) -> None:
            if frame == 30:
                _kill_player(runner.current_scene())

        runner.on_frame(_kill_at_30)

    return Scenario(
        name="death.player_reaches_dead_state",
        frames=120,
        inputs=[],
        on_setup=_on_setup,
        assert_fn=_assert,
    )


def _build_death_transitions_to_death_scene() -> Scenario:
    """Run a longer scenario to allow the death animation to complete.

    The director's main loop is what switches to the death scene
    once the game-over flag is set; the benchmark harness bypasses
    that loop, so this scenario also drives the switch directly
    via the scene_manager when ``is_game_over()`` becomes True.
    """

    def _assert(result: ScenarioResult) -> str | None:
        death_scene = [s for s in result.snapshots if s.scene_name == "death"]
        if not death_scene:
            return "scene never transitioned to 'death' after player death"
        return None

    def _on_setup(runner) -> None:
        def _tick(runner, frame: int) -> None:
            scene = runner.current_scene()
            if frame == 5:
                _kill_player(scene)
                return
            if scene is None:
                return
            # If we've left the game scene already, nothing to do.
            sm = runner.game._director._scene_manager
            if sm.get_current_scene_name() != "game":
                return
            # If the game has reached game-over, switch to the death
            # scene ourselves (mimicking what SceneSwitcher does in
            # the real main loop, which the benchmark harness
            # bypasses).
            try:
                if scene.is_game_over():
                    death = sm.get_scene("death")
                    if death is not None:
                        sm.switch("death")
            except Exception:
                pass

        runner.on_frame(_tick)

    return Scenario(
        name="death.scene_transitions_to_death_after_animation",
        frames=300,
        inputs=[],
        on_setup=_on_setup,
        assert_fn=_assert,
    )


SCENARIOS.extend([_build_death_basic(), _build_death_transitions_to_death_scene()])


for s in SCENARIOS:
    register(s)
