"""Tests for the ISaveData structural Protocol (47 模糊点 F.I4).

Verifies that:
- ``GameSaveData`` (the production dataclass) conforms to ``ISaveData``.
- A duck-typed ``SimpleNamespace`` test double with the required
  attributes also conforms (``isinstance`` is True), so test doubles
  can satisfy the contract without importing the concrete dataclass.
- The Protocol catches missing fields: a double missing ``version``
  is NOT an ``ISaveData``.
- Round-trip ``to_dict`` / ``from_dict`` works through the Protocol.
"""

from __future__ import annotations

from types import SimpleNamespace

from airwar.game.mother_ship import GameSaveData, ISaveData
from airwar.game.mother_ship.mother_ship_state import CURRENT_SAVE_VERSION


def _make_double(**overrides):
    """Build a SimpleNamespace that satisfies ISaveData."""
    base = {
        "version": CURRENT_SAVE_VERSION,
        "timestamp": 0.0,
        "difficulty": "medium",
        "username": "Tester",
        "score": 42,
        "cycle_count": 3,
        "kill_count": 7,
        "boss_kill_count": 1,
        "requisition_points": 5,
        "player_health": 80,
        "player_max_health": 100,
        "player_x": 10.0,
        "player_y": 20.0,
        "is_in_mothership": False,
        "mothership_state": "idle",
        "mothership_cooldown_progress": 0.0,
        "mothership_stay_progress": 0.0,
        "unlocked_buffs": [],
        "buff_levels": {},
        "earned_buff_levels": {},
        "talent_loadout": {},
    }
    base.update(overrides)

    def to_dict():
        return dict(base)

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

    base["to_dict"] = to_dict
    base["from_dict"] = from_dict
    return SimpleNamespace(**base)


def test_gamesavedata_conforms_to_isave_data():
    """The production dataclass should satisfy the ISaveData Protocol."""
    assert isinstance(GameSaveData(), ISaveData)


def test_duck_typed_double_conforms_to_isave_data():
    """A SimpleNamespace with the required fields also satisfies the Protocol."""
    assert isinstance(_make_double(), ISaveData)


def test_double_missing_version_does_not_conform():
    """If version is missing, the double is NOT an ISaveData."""
    dbl = _make_double()
    del dbl.version
    assert not isinstance(dbl, ISaveData)


def test_double_missing_to_dict_does_not_conform():
    """If the round-trip API is missing, the double is NOT an ISaveData."""
    dbl = _make_double()
    del dbl.to_dict
    assert not isinstance(dbl, ISaveData)


def test_gamesavedata_round_trip_preserves_fields():
    """to_dict + from_dict must round-trip without losing data."""
    original = GameSaveData(
        score=100,
        kill_count=5,
        boss_kill_count=2,
        username="Alice",
        difficulty="hard",
        player_x=42.0,
        player_y=84.0,
    )
    round_tripped = GameSaveData.from_dict(original.to_dict())
    assert round_tripped.score == 100
    assert round_tripped.kill_count == 5
    assert round_tripped.boss_kill_count == 2
    assert round_tripped.username == "Alice"
    assert round_tripped.difficulty == "hard"
    assert round_tripped.player_x == 42.0
    assert round_tripped.player_y == 84.0
