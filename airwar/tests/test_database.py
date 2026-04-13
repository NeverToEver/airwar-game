import pytest
import os
import sys
import tempfile
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestUserDB:
    @pytest.fixture(autouse=True)
    def setup_temp_db(self):
        fd, self.db_path = tempfile.mkstemp(suffix='.json')
        os.close(fd)
        os.remove(self.db_path)

        from airwar.utils.database import UserDB
        original_path = UserDB.__init__.__code__.co_freevars
        self.db = UserDB()
        self.db.db_path = self.db_path
        self.db._ensure_dir()
        yield self.db

        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_create_user(self):
        result = self.db.create_user('testuser', 'password123')
        assert result is True

    def test_create_duplicate_user(self):
        self.db.create_user('testuser', 'password123')
        result = self.db.create_user('testuser', 'different')
        assert result is False

    def test_verify_user(self):
        self.db.create_user('testuser', 'password123')
        assert self.db.verify_user('testuser', 'password123') is True
        assert self.db.verify_user('testuser', 'wrongpass') is False

    def test_verify_nonexistent_user(self):
        assert self.db.verify_user('nobody', 'password') is False

    def test_user_exists(self):
        self.db.create_user('testuser', 'password123')
        assert self.db.user_exists('testuser') is True
        assert self.db.user_exists('nobody') is False

    def test_get_user_data(self):
        self.db.create_user('testuser', 'password123')
        data = self.db.get_user_data('testuser')
        assert 'password' in data
        assert data['high_score'] == 0
        assert data['total_kills'] == 0
        assert data['games_played'] == 0

    def test_update_user_data(self):
        self.db.create_user('testuser', 'password123')
        result = self.db.update_user_data('testuser', {'high_score': 500})
        assert result is True
        data = self.db.get_user_data('testuser')
        assert data['high_score'] == 500

    def test_update_high_score(self):
        self.db.create_user('testuser', 'password123')
        self.db.update_high_score('testuser', 100)
        self.db.update_high_score('testuser', 200)
        self.db.update_high_score('testuser', 50)
        data = self.db.get_user_data('testuser')
        assert data['high_score'] == 200

    def test_password_not_stored_plain(self):
        self.db.create_user('testuser', 'password123')
        with open(self.db_path, 'r') as f:
            raw = json.load(f)
        assert 'password123' not in str(raw)
        assert 'password' in raw['testuser']
