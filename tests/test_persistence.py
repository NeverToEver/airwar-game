"""Tests for the single-path persistence boundary."""

import os

import pytest

from airwar.game.mother_ship import GameSaveData, PersistenceManager
from airwar.game.mother_ship.mother_ship_state import (
    CURRENT_SAVE_VERSION,
    SaveDataCorruptedError,
    normalize_save_data,
)
from airwar.game.systems.game_save_service import GameSaveService
from airwar.game.scene_director_components.scene_state_persistence import SceneStatePersistence


@pytest.fixture
def save_dir(tmp_path):
    return str(tmp_path / "saves")


@pytest.fixture
def sample_data():
    return GameSaveData(
        score=1000,
        cycle_count=2,
        player_health=80,
        player_max_health=100,
        difficulty="hard",
        username="test_user",
    )


class TestGameSaveData:
    def test_roundtrip_via_dict(self, sample_data):
        data = GameSaveData.from_dict(sample_data.to_dict())
        assert data.score == sample_data.score
        assert data.username == sample_data.username
        assert data.difficulty == sample_data.difficulty

    def test_legacy_migration_adds_version(self):
        legacy = {"score": 500, "username": "legacy"}
        data = GameSaveData.from_dict(legacy)
        assert data.version == CURRENT_SAVE_VERSION

    def test_v2_migration_adds_mothership_fields(self):
        v2 = {
            "version": 2,
            "score": 100,
            "username": "v2_user",
        }
        data = GameSaveData.from_dict(v2)
        assert data.mothership_state == "idle"
        assert data.mothership_cooldown_progress == 0.0

    def test_missing_required_field_raises(self):
        with pytest.raises(SaveDataCorruptedError):
            GameSaveData.from_dict({"version": CURRENT_SAVE_VERSION})

    def test_newer_version_raises(self):
        with pytest.raises(SaveDataCorruptedError):
            GameSaveData.from_dict({
                "version": CURRENT_SAVE_VERSION + 1,
                "score": 0,
                "username": "x",
            })

    def test_normalize_rejects_bool_for_int(self):
        with pytest.raises(SaveDataCorruptedError):
            normalize_save_data({"score": True})

    def test_normalize_rejects_float_non_integer(self):
        with pytest.raises(SaveDataCorruptedError):
            normalize_save_data({"score": 1.5})


class TestPersistenceManager:
    def test_save_file_for_user_is_stable(self):
        name = PersistenceManager._save_file_for_user("Player One!")
        assert name.startswith("user_docking_save_")
        assert name.endswith(".json")

    def test_save_and_load_roundtrip(self, save_dir, sample_data):
        pm = PersistenceManager(save_dir=save_dir, username=sample_data.username)
        assert pm.save_game(sample_data) is True
        loaded = pm.load_game()
        assert loaded is not None
        assert loaded.score == sample_data.score
        assert loaded.username == sample_data.username

    def test_load_missing_returns_none(self, save_dir):
        pm = PersistenceManager(save_dir=save_dir, username="nobody")
        assert pm.load_game() is None

    def test_delete_save(self, save_dir, sample_data):
        pm = PersistenceManager(save_dir=save_dir, username=sample_data.username)
        pm.save_game(sample_data)
        assert pm.has_saved_game() is True
        assert pm.delete_save() is True
        assert pm.has_saved_game() is False

    def test_load_corrupted_json_deletes_save(self, save_dir):
        pm = PersistenceManager(save_dir=save_dir, username="corrupt")
        os.makedirs(save_dir, exist_ok=True)
        with open(pm.save_path, "w") as f:
            f.write("not json")
        assert pm.load_game() is None
        assert pm.has_saved_game() is False


class TestGameSaveService:
    def test_save_forces_outside_mothership(self, save_dir, sample_data):
        sample_data.is_in_mothership = True
        service = GameSaveService(save_dir=save_dir)
        assert service.save(sample_data, force_outside_mothership=True) is True
        loaded = service.load(sample_data.username)
        assert loaded is not None
        assert loaded.is_in_mothership is False

    def test_load_filters_by_username(self, save_dir):
        service = GameSaveService(save_dir=save_dir)
        data_a = GameSaveData(username="alice", score=100)
        data_b = GameSaveData(username="bob", score=200)
        service.save(data_a)
        service.save(data_b)

        loaded_alice = service.load("alice")
        loaded_bob = service.load("bob")
        assert loaded_alice is not None
        assert loaded_bob is not None
        assert loaded_alice.score == 100
        assert loaded_bob.score == 200
        assert service.load("charlie") is None

    def test_clear_deletes_matching_save(self, save_dir, sample_data):
        service = GameSaveService(save_dir=save_dir)
        service.save(sample_data)
        service.clear(sample_data.username)
        assert service.load(sample_data.username) is None


class TestSceneStatePersistence:
    def test_perform_save_delegates_to_service(self, save_dir):
        class FakeScene:
            def create_save_data(self):
                return GameSaveData(username="scene_user", score=42)

            def is_mothership_docked(self):
                return True

        director = type("Director", (), {"_save_dir": save_dir, "_current_user": "scene_user"})()
        persistence = SceneStatePersistence(director)
        assert persistence.perform_save(FakeScene()) is True  # type: ignore[arg-type]
        loaded = persistence.check_and_get_saved_game("scene_user")
        assert loaded is not None
        assert loaded.score == 42
