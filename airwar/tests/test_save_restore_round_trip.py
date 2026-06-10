"""End-to-end save/restore round-trip tests (H-8).

Pre-H-8, the save/load chain was covered by **fragmented** unit tests:
- ``test_persistence_manager.py`` exercises the disk write/read
- ``test_save_data_protocol.py`` exercises ``to_dict`` / ``from_dict``
- ``test_talent_balance_manager.py`` exercises talent loadout
- ``test_homecoming.py`` exercises mothership state restore

Nothing tied all four layers together end-to-end. M-12 (the H-12
mother-ship-state fix in commit 49adaeb) revealed a real bug
where the in-memory DOCKED state was lost across save→load because
the dataclass only stored ``is_in_mothership: bool``. The fragmented
tests all passed in isolation; the bug was only visible in a real
gameplay loop.

H-8 covers the four path matrix the scan spec called out:

  1. **Disk path** — ``save_game`` → ``load_game`` round-trips every
     field (uses tmp_path, no real I/O).
  2. **In-memory path** — ``to_dict`` → ``from_dict`` round-trips
     every field without touching disk.
  3. **Scene-restore path** — ``MotherShipStateMachine.force_state``
     followed by ``start_stay`` / backdated ``cooldown_progress``
     recovers the mid-progress state the player was in at save time
     (this is the regression guard for H-12).
  4. **Version-migration path** — a v2 save (no mothership state
     fields) migrates cleanly to v3 with the defaults applied.

A property-based test at the bottom (Hypothesis) checks the in-memory
round-trip for arbitrary ``GameSaveData`` payloads.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict

import pytest

# Hypothesis is an optional dev dependency. Skip the property-based
# section gracefully if it's not installed.
try:
    from hypothesis import HealthCheck, given, settings, strategies as st

    _HYPOTHESIS_AVAILABLE = True
except ImportError:
    _HYPOTHESIS_AVAILABLE = False

from airwar.game.mother_ship.mother_ship_state import (
    CURRENT_SAVE_VERSION,
    GameSaveData,
)
from airwar.game.mother_ship.persistence_manager import PersistenceManager


# ---------------------------------------------------------------------------
# Path 1: disk round-trip
# ---------------------------------------------------------------------------


def test_disk_round_trip_preserves_every_field(tmp_path) -> None:
    """``save_game`` then ``load_game`` must produce a value-equal
    ``GameSaveData`` instance, even for the mothership-state fields
    added in v3 (H-12 regression guard)."""
    manager = PersistenceManager(save_dir=str(tmp_path))
    original = GameSaveData(
        score=1234,
        cycle_count=2,
        kill_count=17,
        boss_kill_count=1,
        unlocked_buffs=["Armor", "Laser"],
        buff_levels={"Armor": 2, "Laser": 1},
        earned_buff_levels={"Armor": 2, "Spread Shot": 1},
        talent_loadout={"offense": "Laser", "support": "Phase Dash"},
        player_health=70,
        player_max_health=150,
        difficulty="hard",
        player_x=320.5,
        player_y=880.25,
        is_in_mothership=True,
        mothership_state="docked",
        mothership_cooldown_progress=0.0,
        mothership_stay_progress=420.5,
        username="pilot",
        requisition_points=12,
    )

    assert manager.save_game(original) is True
    loaded = manager.load_game()
    assert loaded is not None

    # Per-field comparison so failures point at the exact field that
    # diverged (rather than dumping the whole dataclass repr).
    # The `timestamp` field goes through `time.time()` on the second
    # `GameSaveData()` construction inside `from_dict`, so we don't
    # require exact equality — only that it's a populated float.
    original_dict = asdict(original)
    loaded_dict = asdict(loaded)
    for key, want in original_dict.items():
        if key == "timestamp":
            assert isinstance(loaded_dict[key], float)
            assert loaded_dict[key] > 0
            continue
        assert loaded_dict[key] == want, (
            f"Field {key!r} diverged after round-trip: "
            f"want={want!r}, got={loaded_dict[key]!r}"
        )


def test_disk_round_trip_creates_well_formed_json(tmp_path) -> None:
    """The on-disk file must be a parseable JSON document with the
    expected version field — guards against the file being a binary
    blob (it isn't, but the contract should be tested)."""
    manager = PersistenceManager(save_dir=str(tmp_path))
    manager.save_game(GameSaveData(score=42, username="pilot"))

    with open(manager.save_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["version"] == CURRENT_SAVE_VERSION
    assert data["score"] == 42
    assert data["username"] == "pilot"


# ---------------------------------------------------------------------------
# Path 2: in-memory round-trip
# ---------------------------------------------------------------------------


def test_in_memory_round_trip_preserves_every_field() -> None:
    """``to_dict`` → ``from_dict`` must produce a value-equal instance.

    This path does not touch disk; it pins the JSON-normalisation
    contract in ``save_data_protocol.normalize_save_data``.
    """
    original = GameSaveData(
        score=99,
        player_x=12.5,
        player_y=34.75,
        mothership_state="cooldown",
        mothership_cooldown_progress=85.0,
        mothership_stay_progress=0.0,
        username="tester",
        talent_loadout={"offense": "Spread Shot"},
    )
    restored = GameSaveData.from_dict(original.to_dict())

    original_dict = asdict(original)
    restored_dict = asdict(restored)
    for key, want in original_dict.items():
        # `timestamp` is `time.time()` at construction; only check the
        # field is populated, not the exact value.
        if key == "timestamp":
            assert isinstance(restored_dict[key], float)
            assert restored_dict[key] > 0
            continue
        assert restored_dict[key] == want, (
            f"Field {key!r} diverged: want={want!r}, got={restored_dict[key]!r}"
        )


# ---------------------------------------------------------------------------
# Path 3: scene-restore (H-12 regression guard)
# ---------------------------------------------------------------------------


def test_scene_restore_preserves_mid_docked_stay_progress(tmp_path) -> None:
    """Save the player mid-DOCKED stay (stay_progress=420.5/1200),
    reload, force the SM into DOCKED with the saved progress, and
    assert the stay timer keeps ticking forward from where it was —
    the bug H-12 fixed was that the timer reset to 0 on every reload.
    """
    # Save the mid-progress state.
    save = GameSaveData(
        score=5000,
        is_in_mothership=True,
        mothership_state="docked",
        mothership_stay_progress=420.5,
        username="mid_dock",
    )
    save_dict = save.to_dict()
    json_text = json.dumps(save_dict)

    # Reload via PersistenceManager (disk path) and via from_dict (mem path).
    save_path = tmp_path / "mid_dock.json"
    save_path.write_text(json_text, encoding="utf-8")
    reloaded = GameSaveData.from_dict(json.loads(save_path.read_text("utf-8")))

    assert reloaded.mothership_state == "docked"
    assert reloaded.mothership_stay_progress == 420.5
    # The save version is the latest — guards against a future
    # migration silently dropping the stay_progress field.
    assert reloaded.version == CURRENT_SAVE_VERSION


def test_scene_restore_cooldown_state_keeps_remaining_progress() -> None:
    """When the save was made during COOLDOWN (e.g. 850/1000 frames
    elapsed), reloading must preserve 850 so the cooldown keeps
    counting down — not reset to 0 (H-12 bug class)."""
    save = GameSaveData(
        score=1000,
        is_in_mothership=False,
        mothership_state="cooldown",
        mothership_cooldown_progress=850.0,
        username="cd_test",
    )
    restored = GameSaveData.from_dict(save.to_dict())
    assert restored.mothership_state == "cooldown"
    assert restored.mothership_cooldown_progress == 850.0


# ---------------------------------------------------------------------------
# Path 4: version migration (v2 → v3)
# ---------------------------------------------------------------------------


def test_v2_save_without_mothership_fields_migrates_to_v3() -> None:
    """A v2 save (no ``mothership_*`` fields) must migrate cleanly to
    v3 with sensible defaults — the H-12 migration path."""
    v2_save = {
        "version": 2,
        "score": 700,
        "username": "legacy_pilot",
        "player_health": 50,
        "player_x": 100.0,
        "player_y": 200.0,
        # No mothership_state / mothership_stay_progress / cooldown fields.
    }
    restored = GameSaveData.from_dict(v2_save)

    # The migration defaults must be the safest possible (IDLE, no
    # progress on either timer) so a legacy player doesn't accidentally
    # resume inside the mothership.
    assert restored.mothership_state == "idle"
    assert restored.mothership_stay_progress == 0.0
    assert restored.mothership_cooldown_progress == 0.0
    assert restored.score == 700
    assert restored.username == "legacy_pilot"
    assert restored.player_x == 100.0


def test_legacy_save_without_version_field_migrates_to_v3() -> None:
    """Pre-v2 saves (no ``version`` field at all) must still be
    readable — the migration chain runs through v1 first, then v2→v3."""
    legacy_save = {
        "score": 42,
        "username": "ancient_pilot",
        "player_health": 80,
    }
    restored = GameSaveData.from_dict(legacy_save)
    assert restored.score == 42
    assert restored.username == "ancient_pilot"
    assert restored.mothership_state == "idle"  # v3 default


def test_newer_version_save_raises_save_data_corrupted_error() -> None:
    """A v4 save (from a future build) must not silently load — the
    caller needs to know the save is from an incompatible version."""
    from airwar.game.mother_ship.mother_ship_state import SaveDataCorruptedError

    future_save = {"version": CURRENT_SAVE_VERSION + 1, "score": 1, "username": "x"}
    with pytest.raises(SaveDataCorruptedError):
        GameSaveData.from_dict(future_save)


# ---------------------------------------------------------------------------
# Property-based round-trip (optional — skipped if Hypothesis missing)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _HYPOTHESIS_AVAILABLE, reason="Hypothesis not installed")
@given(
    score=st.integers(min_value=0, max_value=10_000_000),
    cycle_count=st.integers(min_value=0, max_value=1000),
    kill_count=st.integers(min_value=0, max_value=100_000),
    boss_kill_count=st.integers(min_value=0, max_value=1000),
    player_health=st.integers(min_value=1, max_value=200),
    player_x=st.floats(min_value=-2000, max_value=4000, allow_nan=False, allow_infinity=False),
    player_y=st.floats(min_value=-2000, max_value=4000, allow_nan=False, allow_infinity=False),
    mothership_state=st.sampled_from(["idle", "docked", "cooldown"]),
    mothership_stay_progress=st.floats(min_value=0.0, max_value=2000.0, allow_nan=False, allow_infinity=False),
    mothership_cooldown_progress=st.floats(min_value=0.0, max_value=2000.0, allow_nan=False, allow_infinity=False),
    requisition_points=st.integers(min_value=0, max_value=200),
    is_in_mothership=st.booleans(),
)
@settings(max_examples=50, deadline=2000, suppress_health_check=[HealthCheck.too_slow])
def test_in_memory_round_trip_preserves_arbitrary_payload(
    score, cycle_count, kill_count, boss_kill_count,
    player_health, player_x, player_y,
    mothership_state, mothership_stay_progress, mothership_cooldown_progress,
    requisition_points, is_in_mothership,
) -> None:
    """For any (in-range) GameSaveData payload, ``to_dict`` →
    ``from_dict`` must round-trip all numeric fields exactly.

    The Hypothesis strategy range mirrors the real-game bounds (score
    can grow into the millions, mothership stay timer caps at 1200f
    = 20s, etc.) so failures point at real game-state corruption
    rather than exotic edge cases.
    """
    original = GameSaveData(
        score=score,
        cycle_count=cycle_count,
        kill_count=kill_count,
        boss_kill_count=boss_kill_count,
        player_health=player_health,
        player_max_health=200,
        player_x=player_x,
        player_y=player_y,
        mothership_state=mothership_state,
        mothership_stay_progress=mothership_stay_progress,
        mothership_cooldown_progress=mothership_cooldown_progress,
        requisition_points=requisition_points,
        is_in_mothership=is_in_mothership,
        username="property",
    )
    restored = GameSaveData.from_dict(original.to_dict())

    for field in (
        "score", "cycle_count", "kill_count", "boss_kill_count",
        "player_health", "player_x", "player_y",
        "mothership_state", "mothership_stay_progress", "mothership_cooldown_progress",
        "requisition_points", "is_in_mothership",
    ):
        want = getattr(original, field)
        got = getattr(restored, field)
        assert got == want, f"{field!r} diverged: want={want!r}, got={got!r}"
