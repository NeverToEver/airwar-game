"""Tests for UserDB and SimpleDB persistence safety."""

import json
from multiprocessing import Pool

import pytest

from airwar.utils.database import UserDB


@pytest.fixture
def db(tmp_path):
    return UserDB(db_path=str(tmp_path / "users.json"))


class TestUserDBAuthentication:
    def test_verify_user_success(self, db):
        assert db.create_user("alice", "secret") is True
        assert db.verify_user("alice", "secret") is True

    def test_verify_user_wrong_password(self, db):
        assert db.create_user("alice", "secret") is True
        assert db.verify_user("alice", "wrong") is False

    def test_verify_user_missing_user(self, db):
        assert db.verify_user("nobody", "secret") is False

    def test_verify_user_missing_salt_is_rejected(self, db):
        assert db.create_user("alice", "secret") is True
        data = db._load()
        del data["alice"]["salt"]
        db._save(data)
        assert db.verify_user("alice", "secret") is False

    def test_verify_user_empty_salt_is_rejected(self, db):
        assert db.create_user("alice", "secret") is True
        data = db._load()
        data["alice"]["salt"] = ""
        db._save(data)
        assert db.verify_user("alice", "secret") is False


class TestUserDBLeaderboard:
    def test_submit_score_accepts_int(self, db):
        assert db.submit_score("alice", 100) == 1
        assert db.get_leaderboard()[0]["score"] == 100

    def test_submit_score_rejects_bool(self, db):
        assert db.submit_score("alice", True) == 0
        assert db.get_leaderboard() == []

    def test_submit_score_converts_string_int(self, db):
        assert db.submit_score("alice", "42") == 1
        assert db.get_leaderboard()[0]["score"] == 42

    def test_submit_score_rejects_non_numeric(self, db):
        assert db.submit_score("alice", "not-a-number") == 0
        assert db.get_leaderboard() == []

    def test_submit_score_clamps_negative(self, db):
        assert db.submit_score("alice", -10) == 1
        assert db.get_leaderboard()[0]["score"] == 0


class TestSimpleDBCorruptionRecovery:
    def test_load_corrupted_database_resets_and_backup(self, tmp_path):
        db_path = tmp_path / "users.json"
        db_path.write_text("not valid json", encoding="utf-8")

        db = UserDB(db_path=str(db_path))
        data = db._load()

        assert data == {}
        backups = list(tmp_path.glob("users.json.corrupted.*.bak"))
        assert len(backups) == 1

    def test_save_uses_unique_temp_files(self, tmp_path):
        db_path = tmp_path / "users.json"
        db = UserDB(db_path=str(db_path))
        db.create_user("alice", "secret")

        # Saving should leave no stale fixed-name .tmp files.
        assert not any(tmp_path.glob("*.tmp"))
        assert db_path.exists()


def _concurrent_writer(args):
    db_path, user_id, password = args
    db = UserDB(db_path=db_path)
    db.create_user(user_id, password)
    return db_path


class TestSimpleDBConcurrency:
    def test_concurrent_writes_keep_valid_json(self, tmp_path):
        db_path = str(tmp_path / "users.json")
        args = [(db_path, f"user_{i}", f"pass_{i}") for i in range(8)]

        with Pool(processes=4) as pool:
            pool.map(_concurrent_writer, args)

        with open(db_path, encoding="utf-8") as f:
            data = json.load(f)

        assert len(data) == 8
        for i in range(8):
            assert f"user_{i}" in data
