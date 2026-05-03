import json

from airwar.game.mother_ship.mother_ship_state import GameSaveData
from airwar.game.mother_ship.persistence_manager import PersistenceManager


def test_save_and_load_round_trip(tmp_path):
    manager = PersistenceManager(save_dir=str(tmp_path))
    save_data = GameSaveData(
        score=1234,
        cycle_count=2,
        kill_count=17,
        boss_kill_count=1,
        unlocked_buffs=["Armor", "Laser"],
        buff_levels={"Armor": 2, "Laser": 1},
        player_health=70,
        player_max_health=150,
        difficulty="hard",
        player_x=320.5,
        player_y=880.25,
        is_in_mothership=True,
        username="pilot",
    )

    assert manager.save_game(save_data) is True

    loaded = manager.load_game()
    assert loaded is not None
    assert loaded.score == 1234
    assert loaded.username == "pilot"
    assert loaded.unlocked_buffs == ["Armor", "Laser"]
    assert loaded.buff_levels == {"Armor": 2, "Laser": 1}
    assert loaded.player_x == 320.5
    assert loaded.is_in_mothership is True


def test_save_normalizes_integer_float_score(tmp_path):
    manager = PersistenceManager(save_dir=str(tmp_path))
    save_data = GameSaveData(score=1234.0, username="pilot")

    assert manager.save_game(save_data) is True

    raw = json.loads((tmp_path / PersistenceManager.DEFAULT_SAVE_FILE_NAME).read_text(encoding="utf-8"))
    assert raw["score"] == 1234
    assert isinstance(raw["score"], int)


def test_load_normalizes_integer_float_score(tmp_path):
    save_path = tmp_path / PersistenceManager.DEFAULT_SAVE_FILE_NAME
    save_path.write_text(
        json.dumps({
            "version": 1,
            "score": 1234.0,
            "username": "pilot",
            "player_health": 80.0,
            "player_max_health": 100.0,
        }),
        encoding="utf-8",
    )

    manager = PersistenceManager(save_dir=str(tmp_path))

    loaded = manager.load_game()
    assert loaded is not None
    assert loaded.score == 1234
    assert isinstance(loaded.score, int)
    assert loaded.player_health == 80


def test_load_corrupt_json_returns_none(tmp_path):
    save_path = tmp_path / PersistenceManager.DEFAULT_SAVE_FILE_NAME
    save_path.write_text("{not valid json", encoding="utf-8")

    manager = PersistenceManager(save_dir=str(tmp_path))

    assert manager.has_saved_game() is True
    assert manager.load_game() is None


def test_load_missing_required_field_returns_none(tmp_path):
    save_path = tmp_path / PersistenceManager.DEFAULT_SAVE_FILE_NAME
    save_path.write_text(json.dumps({"version": 1, "score": 100}), encoding="utf-8")

    manager = PersistenceManager(save_dir=str(tmp_path))

    assert manager.load_game() is None
