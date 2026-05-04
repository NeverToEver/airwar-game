import json
from pathlib import Path

import pytest

from airwar.utils.database import DatabaseError, UserDB


def test_user_db_rejects_corrupt_json_instead_of_treating_it_as_empty(tmp_path: Path) -> None:
    db_path = tmp_path / "users.json"
    db_path.write_text("{not valid json", encoding="utf-8")
    db = UserDB(str(db_path))

    with pytest.raises(DatabaseError):
        db.create_user("pilot", "secret")

    assert db_path.read_text(encoding="utf-8") == "{not valid json"


def test_user_db_create_user_reports_save_failure(monkeypatch, tmp_path: Path) -> None:
    db = UserDB(str(tmp_path / "users.json"))

    def fail_replace(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr("airwar.utils.database.os.replace", fail_replace)

    with pytest.raises(DatabaseError):
        db.create_user("pilot", "secret")


def test_user_db_requires_password_to_delete_user(tmp_path: Path) -> None:
    db = UserDB(str(tmp_path / "users.json"))

    assert db.create_user("pilot", "secret") is True
    assert db.delete_user("pilot") is False
    assert db.delete_user("pilot", "wrong") is False
    assert db.user_exists("pilot") is True

    assert db.delete_user("pilot", "secret") is True
    assert db.user_exists("pilot") is False

    raw = json.loads((tmp_path / "users.json").read_text(encoding="utf-8"))
    assert raw == {}


def test_user_db_remembers_last_successful_login_user(tmp_path: Path) -> None:
    db = UserDB(str(tmp_path / "users.json"))

    assert db.create_user("alpha", "secret") is True
    assert db.create_user("bravo", "secret") is True
    assert db.list_usernames() == ["alpha", "bravo"]

    assert db.record_login("alpha") is True
    assert db.record_login("bravo") is True

    assert db.get_last_login_user() == "bravo"
    assert db.list_usernames() == ["bravo", "alpha"]
