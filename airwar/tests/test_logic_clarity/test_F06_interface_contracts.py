"""F06: 4 接口契约缺失（interface contract gaps）。

Maps: docs/logic-clarity/11-phase5b-handoff.md §6.2 § F06.
(The previous docs/logic-clarity/04-test-suite.md was retired in the
2026-06-08 docs cleanup; the F06 interface-contract contract is
preserved in the new handoff doc — I2 (property setter bypasses
IGameScene API) flagged with docstring warning, I4 (SaveData Protocol)
formalized as ``airwar/game/mother_ship/save_data_protocol.py``.)

These tests verify that the protocol contracts exist with the right shape.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest


class TestF06CrossLayerProtocols:
    """I1, I2: 跨层 Protocol 存在。"""

    def test_input_source_protocol_exists(self):
        from airwar.protocols import InputSourceProtocol

        assert hasattr(InputSourceProtocol, "get_movement_direction")
        assert hasattr(InputSourceProtocol, "is_pause_pressed")
        assert hasattr(InputSourceProtocol, "is_boost_pressed")

    def test_difficulty_manager_protocol_exists(self):
        from airwar.protocols import DifficultyManagerProtocol

        assert hasattr(DifficultyManagerProtocol, "get_current_difficulty")


class TestF06GameInternalProtocols:
    """I3, I4: game-internal Protocol 存在。"""

    def test_game_internal_protocols_module_exists(self):
        from airwar.game import protocols

        assert protocols is not None
        # Should expose PlayerProtocol, GameControllerProtocol, etc.
        assert hasattr(protocols, "PlayerProtocol") or hasattr(protocols, "__all__")

    def test_protocols_have_method_signatures(self):
        from airwar.game import protocols as gi_protocols

        # Whatever protocols are exported, they should have methods (not empty)
        for name in getattr(gi_protocols, "__all__", []):
            cls = getattr(gi_protocols, name, None)
            if cls is not None and hasattr(cls, "__dict__"):
                # At least one non-dunder attribute
                members = [k for k in cls.__dict__ if not k.startswith("_")]
                assert members, f"Protocol {name} has no members"


class TestF06PreconditionEnforcement:
    """I3: 前置条件校验。"""

    def test_player_state_machine_rejects_invalid_substate(self):
        from airwar.entities.player_state import (
            IllegalPlayerTransition,
            PlayerAliveState,
            PlayerStateMachine,
        )

        class _Stub:
            pass

        sm = PlayerStateMachine(_Stub())
        sm.transition_substate(PlayerAliveState.DOCKED)
        # DASHING from DOCKED is illegal
        with pytest.raises(IllegalPlayerTransition):
            sm.transition_substate(PlayerAliveState.DASHING)
