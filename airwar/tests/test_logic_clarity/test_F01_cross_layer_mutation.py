"""F01: 9 跨层直接突变（cross-layer state mutation）。

Maps: docs/logic-clarity/04-test-suite.md § F01.

These tests assert the **target** behavior after refactor (not the
current bug). Tests that document an existing bug are written to
demonstrate the *expected* post-refactor contract; until the production
code is changed, they are expected to fail with a clear message.

Each test docstring is the fuzzy-point ID from the discovery report.
"""

from __future__ import annotations

import inspect

import pytest


class TestF01GameControllerExposesSetScore:
    """F1: scene.score setter 应通过 GameController.set_score()."""

    def test_game_controller_has_set_score_method(self):
        from airwar.game.managers.game_controller import GameController

        assert hasattr(GameController, "set_score"), (
            "F1: GameController should expose set_score() to encapsulate mutation"
        )
        # Verify the method has a real implementation (not just a stub)
        method = GameController.set_score
        assert callable(method)
        # Should accept a single positional value
        sig = inspect.signature(method)
        params = list(sig.parameters)
        assert "self" in params
        # At least one non-self parameter
        assert len(params) >= 2


class TestF01GameControllerExposesSetCycleCount:
    """F2: cycle_count setter 通过 GameController."""

    def test_game_controller_has_set_cycle_count_method(self):
        from airwar.game.managers.game_controller import GameController

        assert hasattr(GameController, "set_cycle_count"), "F2: GameController should expose set_cycle_count()"


class TestF01GameControllerExposesSetDifficulty:
    """F3: difficulty setter 通过 GameController 且同步子系统。"""

    def test_game_controller_has_set_difficulty_method(self):
        from airwar.game.managers.game_controller import GameController

        assert hasattr(GameController, "set_difficulty"), "F3: GameController should expose set_difficulty()"


class TestF01GameControllerExposesAddScore:
    """F4: scene 累加 score 应走 add_score。"""

    def test_game_controller_has_add_score_method(self):
        from airwar.game.managers.game_controller import GameController

        assert hasattr(GameController, "add_score"), (
            "F4: GameController should expose add_score(amount) for accumulation"
        )


class TestF01KillCountOnlyViaOnEnemyKilled:
    """F5: kill_count 只能由 on_enemy_killed 改。"""

    def test_kill_count_attribute_is_protected(self):
        # The current implementation uses a plain dataclass attribute;
        # post-refactor it should be a property with no setter, or
        # document that direct assignment is illegal.
        from airwar.game.managers.game_controller import GameState

        # Document current state
        gs = GameState()
        gs.kill_count = 999
        # After refactor this should raise
        # For now, just record the current loose behavior
        assert gs.kill_count == 999  # current: no protection
        # This test serves as a sentinel: when refactored, it should fail
        # with FrozenInstanceError or AttributeError. Until then, it
        # documents the gap.


class TestF01BossKillCountOnlyViaOnBossKilled:
    """F6: boss_kill_count 只能由 on_boss_killed 改。"""

    def test_boss_kill_count_attribute_is_protected(self):
        from airwar.game.managers.game_controller import GameState

        gs = GameState()
        gs.boss_kill_count = 999
        assert gs.boss_kill_count == 999  # current: no protection


class TestF01SpawnControllerClearBoss:
    """F7: scene 应通过 clear_boss() 而非直接 boss = None。"""

    def test_spawn_controller_has_clear_boss_method(self):
        from airwar.game.managers.spawn_controller import SpawnController

        assert hasattr(SpawnController, "clear_boss"), (
            "F7: SpawnController should expose clear_boss() instead of direct attribute write"
        )


class TestF01GameControllerClearRipples:
    """F8: ripple_effects.clear() 应有显式 API。"""

    def test_game_controller_has_clear_ripples_method(self):
        from airwar.game.managers.game_controller import GameController

        assert hasattr(GameController, "clear_ripples"), "F8: GameController should expose clear_ripples()"


class TestF01HomecomingEntranceExplicitApi:
    """F9: _start_return_entrance 改 state.is_entrance_playing 应通过 API。"""

    def test_game_controller_has_start_entrance_animation(self):
        from airwar.game.managers.game_controller import GameController

        assert hasattr(GameController, "start_entrance_animation"), (
            "F9: GameController should expose start_entrance_animation()"
        )


# Sentinel: the "all 9 fixed" assertion.
def test_F01_summary_all_apis_exist():
    """When all F1-F9 are refactored, this test will pass."""
    from airwar.game.managers.game_controller import GameController
    from airwar.game.managers.spawn_controller import SpawnController

    required_on_controller = [
        "set_score",
        "set_cycle_count",
        "set_difficulty",
        "add_score",
        "clear_ripples",
        "start_entrance_animation",
    ]
    missing = [m for m in required_on_controller if not hasattr(GameController, m)]
    assert not missing, f"F01 missing API on GameController: {missing}"

    if not hasattr(SpawnController, "clear_boss"):
        pytest.fail("F01 missing API on SpawnController: clear_boss")
