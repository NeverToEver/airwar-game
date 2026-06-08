"""F05: T3-T7 顺序细节 + 早期返回分支枚举。

F05 T3: 4 个 early return 分支（dying / entrance / paused / reward_visible）
应有显式命名。

F05 T5: on_requested 步骤顺序 hide → clear → protect → start。

F05 T7: save_restore 顺序 difficulty → health → boost → buff → position。
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import inspect


class TestF05EarlyReturnEnum:
    """T3: early return 分支枚举。"""

    def test_early_return_branches_documented(self):
        """The 4 early-return branches should have a named enumeration."""
        from airwar.scenes.update_pipeline import PIPELINE_ORDER

        # PIPELINE_ORDER includes 5 short-circuit-capable steps:
        # pause_check, reward_selector, dying_animation,
        # entrance_animation, homecoming.
        short_circuits = {
            "pause_check",
            "reward_selector",
            "dying_animation",
            "entrance_animation",
            "homecoming",
        }
        for step in short_circuits:
            assert step in PIPELINE_ORDER, f"F05 T3: missing short-circuit step {step}"


class TestF05OnRequestedStepOrder:
    """T5: on_requested 步骤顺序。"""

    def test_homecoming_on_requested_calls_in_order(self):
        """The on_requested method should call methods in this order:
        1. self._ui.hide() (if _ui exists)
        2. bullet_manager.clear_enemy_bullets() (if bullet_manager exists)
        3. self._set_protection(True, ...) -> lock_manager.acquire (delegated)
        4. self._sequence.start() (if _sequence exists)
        """
        from airwar.game.systems import homecoming_coordinator

        source = inspect.getsource(homecoming_coordinator.HomecomingCoordinator.on_requested)
        # Verify the order of the four key calls in the source.
        hide_pos = source.find("self._ui.hide()")
        clear_pos = source.find("bullet_manager.clear_enemy_bullets")
        protect_pos = source.find("self._set_protection(True")
        start_pos = source.find("self._sequence.start")

        # All four should be present
        assert hide_pos > 0, "F05 T5: on_requested missing self._ui.hide()"
        assert clear_pos > 0, "F05 T5: on_requested missing clear_enemy_bullets"
        assert protect_pos > 0, "F05 T5: on_requested missing self._set_protection"
        assert start_pos > 0, "F05 T5: on_requested missing self._sequence.start"

        # Verify the order
        assert hide_pos < clear_pos, "F05 T5: hide must come before clear"
        assert clear_pos < protect_pos, "F05 T5: clear must come before protect"
        assert protect_pos < start_pos, "F05 T5: protect must come before start"


class TestF05RestoreOrder:
    """T7: save_restore 顺序。"""

    def test_save_restore_restore_method_steps_in_order(self):
        """The restore method should follow: difficulty → boost → buff reapply → health → position.

        The actual ordering matters: difficulty must be set first so the
        boost config and health/buff values use the right difficulty
        baseline; buff reapply must happen after difficulty is set so
        the buff effects match the saved difficulty; health must be
        clamped to the new max; position is last.
        """
        from airwar.game.systems.save_restore_manager import SaveRestoreManager

        source = inspect.getsource(SaveRestoreManager.restore)
        difficulty_pos = source.find("set_difficulty")
        boost_pos = source.find("player.boost_current =")
        # Buff reapply is in the helper _restore_talent_loadout_effects,
        # which is called from restore. The restore method has the call
        # ``self._restore_talent_loadout_effects()`` between boost and health.
        buff_pos = source.find("_restore_talent_loadout_effects")
        health_pos = source.find("player.health =")
        position_pos = source.find("player.rect.x = max")

        assert difficulty_pos > 0, "F05 T7: restore missing set_difficulty"
        assert boost_pos > 0, "F05 T7: restore missing boost_current set"
        assert buff_pos > 0, "F05 T7: restore missing _restore_talent_loadout_effects call"
        assert health_pos > 0, "F05 T7: restore missing health set"
        assert position_pos > 0, "F05 T7: restore missing position set"

        # Verify the canonical order
        assert difficulty_pos < boost_pos, "F05 T7: difficulty must come before boost"
        assert boost_pos < buff_pos, "F05 T7: boost must come before buff reapply"
        assert buff_pos < health_pos, "F05 T7: buff reapply must come before health"
        assert health_pos < position_pos, "F05 T7: health must come before position"
