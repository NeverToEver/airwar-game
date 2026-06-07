"""Tests for AchievementRegistry — registration, evaluation, persistence."""

from pathlib import Path

import pytest

from airwar.game.achievements import (
    USER_DATA_FIELD,
    Achievement,
    AchievementRegistry,
    build_default_registry,
)
from airwar.utils.database import UserDB


@pytest.fixture
def user_db(tmp_path: Path) -> UserDB:
    db = UserDB(str(tmp_path / "users.json"))
    db.create_user("pilot", "secret")
    return db


def _ach(ach_id: str, threshold: int = 1, field_name: str = "kill_count") -> Achievement:
    return Achievement(
        id=ach_id,
        name_key=f"ach.{ach_id}.name",
        description_key=f"ach.{ach_id}.desc",
        condition_fn=lambda state, t=threshold, f=field_name: state.get(f, 0) >= t,
    )


def test_register_adds_achievement_and_rejects_duplicate_id() -> None:
    registry = AchievementRegistry()
    ach = _ach("first_kill")

    registry.register(ach)

    assert registry.get("first_kill") is ach
    assert registry.all() == [ach]

    with pytest.raises(ValueError, match="already registered"):
        registry.register(_ach("first_kill"))


def test_condition_fn_drives_unlock_state() -> None:
    registry = AchievementRegistry()
    registry.register(_ach("kills_5", threshold=5, field_name="kill_count"))

    # Below threshold: nothing unlocks.
    assert registry.check_all({"kill_count": 4}) == []
    assert registry.get("kills_5").unlocked_at is None

    # At threshold: unlocks and records timestamp.
    newly = registry.check_all({"kill_count": 5})
    assert [a.id for a in newly] == ["kills_5"]
    assert registry.get("kills_5").is_unlocked
    assert isinstance(registry.get("kills_5").unlocked_at, str)


def test_persist_and_load_roundtrip_via_user_db(user_db: UserDB) -> None:
    registry = build_default_registry(user_db=user_db, user_id="pilot")

    newly = registry.check_all(
        {"kill_count": 10, "score": 5_000, "boss_kill_count": 0, "mothership_dock_count": 0}
    )
    unlocked_ids = sorted(a.id for a in newly)
    assert unlocked_ids == ["first_kill", "score_1k"]

    saved = user_db.get_user_data("pilot").get(USER_DATA_FIELD)
    assert saved is not None
    assert set(saved.keys()) == {"first_kill", "score_1k"}

    # Fresh registry → load restores prior unlocks.
    fresh = build_default_registry(user_db=user_db, user_id="pilot")
    assert fresh.load() == 2
    assert sorted(fresh.unlocked_ids()) == ["first_kill", "score_1k"]
    assert fresh.get("first_kill").unlocked_at == saved["first_kill"]


def test_check_all_returns_only_newly_unlocked() -> None:
    registry = AchievementRegistry()
    registry.register(_ach("first_kill", threshold=1, field_name="kill_count"))

    first_call = registry.check_all({"kill_count": 1})
    assert [a.id for a in first_call] == ["first_kill"]

    # Same state again → already unlocked, must not re-appear.
    second_call = registry.check_all({"kill_count": 1})
    assert second_call == []

    # Even higher state should not re-trigger an already-unlocked achievement.
    third_call = registry.check_all({"kill_count": 100})
    assert third_call == []


def test_check_all_handles_multiple_unlocks_in_one_call() -> None:
    registry = build_default_registry()

    newly = registry.check_all(
        {
            "kill_count": 50,
            "score": 12_000,
            "boss_kill_count": 1,
            "mothership_dock_count": 1,
        }
    )

    assert sorted(a.id for a in newly) == [
        "boss_kill",
        "first_kill",
        "mothership_dock",
        "score_10k",
        "score_1k",
    ]
    assert all(a.is_unlocked for a in newly)
