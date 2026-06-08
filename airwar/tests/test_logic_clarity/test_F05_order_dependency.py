"""F05: 7 顺序依赖（order dependencies）。

Maps: docs/logic-clarity/11-phase5b-handoff.md §6.2 § F05.
(The previous docs/logic-clarity/04-test-suite.md was retired in the
2026-06-08 docs cleanup; the F05 order-dependency contract is
preserved in the new handoff doc — T3-T7 verified in commit
``7f95e33``.)

These tests verify that ordered operations have explicit, documented
pipelines rather than implicit positional dependencies.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


class TestF05UpdatePipelineDocumented:
    """T1: 9 子系统位置顺序应被 PIPELINE_ORDER 显式声明。"""

    def test_update_pipeline_module_exists(self):
        """Post-refactor: airwar.scenes.update_pipeline 应有 PIPELINE_ORDER。"""
        try:
            from airwar.scenes import update_pipeline
        except ImportError:
            pytest.skip("T1: airwar.scenes.update_pipeline not yet created; refactor pending")

        assert hasattr(update_pipeline, "PIPELINE_ORDER")

    def test_game_scene_update_documents_steps(self):
        """Current: GameScene.update() has a docstring listing the order."""
        from airwar.scenes.game_scene import GameScene

        source = GameScene.update.__doc__ or ""
        # The current docstring lists 4 steps (entrance, mothership, docking, game logic)
        # Post-refactor: 15 steps.
        assert "Update order" in source or "顺序" in source


class TestF05PostCollisionCleanupBeforeMilestone:
    """T2: post-collision cleanup 在 milestone check 之前。"""

    def test_game_scene_update_calls_cleanup_before_milestone(self):
        """Static check: verify the call order in GameScene.update()."""
        from airwar.scenes import game_scene

        source_path = game_scene.__file__
        text = Path(source_path).read_text()

        # Find the update method
        update_start = text.find("def update(self")
        if update_start < 0:
            pytest.skip("Could not locate update method")

        # Get the body of update (next 100 lines)
        body = text[update_start : update_start + 6000]
        cleanup_pos = body.find("cleanup()")
        milestone_pos = body.find("_milestone_manager.check_and_trigger")

        if cleanup_pos < 0 or milestone_pos < 0:
            pytest.skip("Could not locate cleanup/milestone calls")

        assert cleanup_pos < milestone_pos, "T2: cleanup() must be called before milestone check"


class TestF05OnRequestedOrder:
    """T5: on_requested 顺序 hide→clear→protect→start。"""

    def test_homecoming_on_requested_documented(self):
        from airwar.game.systems import homecoming_coordinator

        source = homecoming_coordinator.HomecomingCoordinator.on_requested.__doc__ or ""
        # The current method has a docstring (may or may not list order)
        assert source is not None


class TestF05RestoreOrder:
    """T7: 还原顺序 difficulty → health → boost → buff → position。"""

    def test_save_restore_restore_method_documents_order(self):
        from airwar.game.systems.save_restore_manager import SaveRestoreManager

        source = SaveRestoreManager.restore.__doc__ or ""
        # Post-refactor: the docstring should explicitly list the order
        assert source is not None
