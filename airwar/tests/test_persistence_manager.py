import pytest
import os
import sys
import tempfile
import json
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from airwar.game.mother_ship import (
    PersistenceManager,
    GameSaveData,
    SaveDataCorruptedError,
)


class TestGameSaveData:
    def test_default_values(self):
        save_data = GameSaveData()
        assert save_data.version == 1
        assert save_data.score == 0
        assert save_data.cycle_count == 0
        assert save_data.kill_count == 0
        assert save_data.boss_kill_count == 0
        assert save_data.player_health == 100
        assert save_data.player_max_health == 100
        assert save_data.difficulty == "medium"
        assert save_data.is_in_mothership is False
        assert save_data.username == ""

    def test_custom_values(self):
        save_data = GameSaveData(
            score=1000,
            cycle_count=3,
            kill_count=50,
            username="testuser",
            unlocked_buffs=["piercing", "spread"],
            buff_levels={"piercing": 2, "spread": 1}
        )
        assert save_data.score == 1000
        assert save_data.cycle_count == 3
        assert save_data.username == "testuser"
        assert len(save_data.unlocked_buffs) == 2

    def test_to_dict(self):
        save_data = GameSaveData(score=500, username="player1")
        data = save_data.to_dict()
        assert 'version' in data
        assert data['version'] == 1
        assert data['score'] == 500
        assert data['username'] == "player1"
        assert 'timestamp' in data

    def test_from_dict(self):
        data = {
            'score': 1000,
            'username': 'testuser',
            'version': 1,
            'cycle_count': 2,
            'kill_count': 30,
            'player_health': 80,
            'player_max_health': 100,
            'difficulty': 'hard',
            'timestamp': 1234567890.0,
            'is_in_mothership': True,
            'unlocked_buffs': ['piercing'],
            'buff_levels': {'piercing': 1}
        }
        save_data = GameSaveData.from_dict(data)
        assert save_data.score == 1000
        assert save_data.username == 'testuser'
        assert save_data.difficulty == 'hard'

    def test_from_dict_legacy_save(self):
        data = {
            'score': 500,
            'username': 'olduser',
            'cycle_count': 1,
            'kill_count': 10,
        }
        save_data = GameSaveData.from_dict(data)
        assert save_data.score == 500
        assert save_data.username == 'olduser'
        assert save_data.version == 1

    def test_from_dict_missing_required_field(self):
        data = {
            'score': 500,
        }
        with pytest.raises(SaveDataCorruptedError):
            GameSaveData.from_dict(data)

    def test_boss_kill_count_in_save_data(self):
        save_data = GameSaveData(
            score=5000,
            cycle_count=5,
            kill_count=100,
            boss_kill_count=3,
            username="bossplayer"
        )
        assert save_data.boss_kill_count == 3
        
        data = save_data.to_dict()
        assert data['boss_kill_count'] == 3
        
        loaded = GameSaveData.from_dict(data)
        assert loaded.boss_kill_count == 3

    def test_from_dict_future_version(self):
        data = {
            'score': 500,
            'username': 'testuser',
            'version': 999,
        }
        with pytest.raises(SaveDataCorruptedError):
            GameSaveData.from_dict(data)


class TestPersistenceManager:
    @pytest.fixture(autouse=True)
    def setup_temp_save(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = "test_save.json"

        yield

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_initialization_default(self):
        manager = PersistenceManager()
        assert os.path.isabs(manager.SAVE_DIRECTORY)
        assert manager.SAVE_DIRECTORY.endswith(os.path.join("airwar", "data"))
        assert manager.SAVE_FILE_NAME == "user_docking_save.json"

    def test_initialization_custom_path(self):
        manager = PersistenceManager(
            save_dir=self.temp_dir,
            save_file=self.temp_file
        )
        assert manager.SAVE_DIRECTORY == self.temp_dir
        assert manager.SAVE_FILE_NAME == self.temp_file
        assert manager.save_path == os.path.join(self.temp_dir, self.temp_file)

    def test_save_game_success(self):
        manager = PersistenceManager(
            save_dir=self.temp_dir,
            save_file=self.temp_file
        )
        save_data = GameSaveData(score=1000, username="testuser")

        result = manager.save_game(save_data)
        assert result is True
        assert os.path.exists(manager.save_path)

        with open(manager.save_path, 'r') as f:
            loaded = json.load(f)
        assert loaded['score'] == 1000
        assert loaded['username'] == "testuser"

    def test_save_game_creates_directory(self):
        nested_dir = os.path.join(self.temp_dir, "nested", "path")
        manager = PersistenceManager(
            save_dir=nested_dir,
            save_file=self.temp_file
        )
        save_data = GameSaveData(score=500, username="testuser")

        result = manager.save_game(save_data)
        assert result is True
        assert os.path.exists(nested_dir)

    def test_load_game_success(self):
        manager = PersistenceManager(
            save_dir=self.temp_dir,
            save_file=self.temp_file
        )
        save_data = GameSaveData(score=2000, username="loader", cycle_count=5)

        manager.save_game(save_data)
        loaded = manager.load_game()

        assert loaded is not None
        assert loaded.score == 2000
        assert loaded.username == "loader"
        assert loaded.cycle_count == 5

    def test_load_game_no_file(self):
        manager = PersistenceManager(
            save_dir=self.temp_dir,
            save_file="nonexistent.json"
        )
        result = manager.load_game()
        assert result is None

    def test_has_saved_game(self):
        manager = PersistenceManager(
            save_dir=self.temp_dir,
            save_file=self.temp_file
        )

        assert manager.has_saved_game() is False

        save_data = GameSaveData(score=100, username="test")
        manager.save_game(save_data)

        assert manager.has_saved_game() is True

    def test_delete_save_success(self):
        manager = PersistenceManager(
            save_dir=self.temp_dir,
            save_file=self.temp_file
        )
        save_data = GameSaveData(score=100, username="test")
        manager.save_game(save_data)

        assert manager.has_saved_game() is True

        result = manager.delete_save()
        assert result is True
        assert manager.has_saved_game() is False

    def test_delete_save_no_file(self):
        manager = PersistenceManager(
            save_dir=self.temp_dir,
            save_file="nonexistent.json"
        )

        result = manager.delete_save()
        assert result is True

    def test_load_corrupted_json(self):
        manager = PersistenceManager(
            save_dir=self.temp_dir,
            save_file=self.temp_file
        )

        with open(manager.save_path, 'w') as f:
            f.write("{ invalid json }")

        result = manager.load_game()
        assert result is None

    def test_overwrite_existing_save(self):
        manager = PersistenceManager(
            save_dir=self.temp_dir,
            save_file=self.temp_file
        )

        save1 = GameSaveData(score=100, username="user1")
        manager.save_game(save1)

        save2 = GameSaveData(score=500, username="user1")
        manager.save_game(save2)

        loaded = manager.load_game()
        assert loaded.score == 500

    def test_save_multiple_users(self):
        manager = PersistenceManager(
            save_dir=self.temp_dir,
            save_file=self.temp_file
        )

        save1 = GameSaveData(score=100, username="user1")
        save2 = GameSaveData(score=200, username="user2")

        manager.save_game(save1)
        loaded1 = manager.load_game()
        assert loaded1.username == "user1"

        manager.save_game(save2)
        loaded2 = manager.load_game()
        assert loaded2.username == "user2"
        assert loaded2.score == 200
