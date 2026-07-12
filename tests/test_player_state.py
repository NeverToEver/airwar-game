"""Tests for PlayerStateMachine boundary fixes (batch F8, F9)."""

import logging
from types import SimpleNamespace

import pytest

from airwar.entities.base import Vector2
from airwar.entities.player import Player
from airwar.entities.player_state import (
    IllegalPlayerTransition,
    PlayerAliveState,
    PlayerStateMachine,
)


class _DummyInputHandler(SimpleNamespace):
    def __init__(self):
        super().__init__(
            tick=lambda: None,
            is_boost_pressed=lambda: False,
            is_fire_pressed=lambda: False,
            is_precision_pressed=lambda: False,
            get_movement_direction=lambda: Vector2(0.0, 0.0),
            get_aim_direction=lambda: (0.0, -1.0),
        )


def _machine_in_docked():
    player = SimpleNamespace(is_controls_locked=False)
    machine = PlayerStateMachine(player)
    machine.force_substate(PlayerAliveState.DOCKED)  # legal from NORMAL
    return machine


def test_force_substate_validates_by_default():
    """F8: default validate=True enforces legal edges."""
    machine = _machine_in_docked()
    # DOCKED -> SHIELDED is not a legal edge.
    with pytest.raises(IllegalPlayerTransition):
        machine.force_substate(PlayerAliveState.SHIELDED)


def test_force_substate_no_validate_logs_warning_and_applies(caplog):
    """F8: validate=False applies the state but warns on illegal edges."""
    machine = _machine_in_docked()
    with caplog.at_level(logging.WARNING, logger="airwar.entities.player_state"):
        machine.force_substate(PlayerAliveState.SHIELDED, validate=False)
    assert machine.alive_substate is PlayerAliveState.SHIELDED
    assert "bypasses the legal-edge table" in caplog.text


def test_force_substate_no_validate_no_warning_for_legal_move(caplog):
    """F8: a legal forced transition should not produce a warning."""
    machine = _machine_in_docked()
    with caplog.at_level(logging.WARNING, logger="airwar.entities.player_state"):
        machine.force_substate(PlayerAliveState.NORMAL, validate=False)
    assert machine.alive_substate is PlayerAliveState.NORMAL
    assert "bypasses the legal-edge table" not in caplog.text


def test_enter_boost_illegal_transition_logs_warning(caplog):
    """F9: Player.update logs a warning for illegal boost transitions."""
    handler = _DummyInputHandler()
    handler.is_boost_pressed = lambda: True
    player = Player(100, 100, handler)
    # Force the player into a state incompatible with boost.
    player._state.force_substate(PlayerAliveState.SHIELDED, validate=False)
    # Ensure there is boost energy so the update attempts enter_boost().
    player.boost.boost_current = 100.0

    with caplog.at_level(logging.WARNING, logger="airwar.entities.player"):
        player.update()

    assert "Ignored illegal boost transition" in caplog.text
