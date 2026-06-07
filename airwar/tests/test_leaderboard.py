"""Tests for the local high-score leaderboard in UserDB."""

import json
from pathlib import Path

from airwar.utils.database import LEADERBOARD_CAP, UserDB


def test_submit_score_returns_one_indexed_rank(tmp_path: Path) -> None:
    db = UserDB(str(tmp_path / "users.json"))

    rank = db.submit_score("alice", 100)

    assert rank == 1
    entries = db.get_leaderboard()
    assert len(entries) == 1
    assert entries[0]["player_name"] == "alice"
    assert entries[0]["score"] == 100
    timestamp = entries[0]["timestamp"]
    assert isinstance(timestamp, str)
    assert timestamp


def test_leaderboard_is_sorted_by_score_descending(tmp_path: Path) -> None:
    db = UserDB(str(tmp_path / "users.json"))

    db.submit_score("low", 100)
    db.submit_score("high", 500)
    db.submit_score("mid", 250)

    entries = db.get_leaderboard()
    assert [e["player_name"] for e in entries] == ["high", "mid", "low"]
    assert [e["score"] for e in entries] == [500, 250, 100]


def test_leaderboard_is_capped_at_ten_entries(tmp_path: Path) -> None:
    db = UserDB(str(tmp_path / "users.json"))

    total = LEADERBOARD_CAP + 5  # 15 entries submitted
    for i in range(total):
        db.submit_score(f"player_{i:02d}", (i + 1) * 10)

    entries = db.get_leaderboard()
    assert len(entries) == LEADERBOARD_CAP
    # Top 10 by score: player_14 (150) .. player_05 (60); the bottom 5 are dropped.
    expected_top = [f"player_{i:02d}" for i in range(total - 1, total - LEADERBOARD_CAP - 1, -1)]
    assert [e["player_name"] for e in entries] == expected_top
    assert [e["score"] for e in entries] == [150, 140, 130, 120, 110, 100, 90, 80, 70, 60]

    # A clearly lower score cannot crack the top 10.
    assert db.submit_score("stranger", 1) == 0
    assert db.submit_score("stranger", 1) == 0


def test_empty_leaderboard_returns_empty_list(tmp_path: Path) -> None:
    db = UserDB(str(tmp_path / "users.json"))

    assert db.get_leaderboard() == []


def test_leaderboard_persists_across_instances(tmp_path: Path) -> None:
    db_path = tmp_path / "users.json"
    first = UserDB(str(db_path))
    first.submit_score("alpha", 750)
    first.submit_score("bravo", 250)

    second = UserDB(str(db_path))
    entries = second.get_leaderboard()
    assert [e["player_name"] for e in entries] == ["alpha", "bravo"]
    assert [e["score"] for e in entries] == [750, 250]

    # The raw JSON should also expose the leaderboard under its dedicated key.
    raw = json.loads(db_path.read_text(encoding="utf-8"))
    assert "_leaderboard" in raw
    assert len(raw["_leaderboard"]) == 2
