import json
import os
import hashlib


class SimpleDB:
    def __init__(self, db_path: str = "airwar/data/users.json"):
        self.db_path = db_path
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        if not os.path.exists(self.db_path):
            self._save({})

    def _load(self) -> dict:
        try:
            with open(self.db_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, data: dict) -> None:
        with open(self.db_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()


class UserDB(SimpleDB):
    def __init__(self):
        super().__init__()

    def create_user(self, user_id: str, password: str) -> bool:
        data = self._load()
        if user_id in data:
            return False
        data[user_id] = {
            'password': self._hash_password(password),
            'high_score': 0,
            'total_kills': 0,
            'games_played': 0
        }
        self._save(data)
        return True

    def verify_user(self, user_id: str, password: str) -> bool:
        data = self._load()
        if user_id not in data:
            return False
        return data[user_id]['password'] == self._hash_password(password)

    def user_exists(self, user_id: str) -> bool:
        data = self._load()
        return user_id in data

    def get_user_data(self, user_id: str) -> dict:
        data = self._load()
        return data.get(user_id, {})

    def update_user_data(self, user_id: str, updates: dict) -> bool:
        data = self._load()
        if user_id not in data:
            return False
        data[user_id].update(updates)
        self._save(data)
        return True

    def update_high_score(self, user_id: str, score: int) -> bool:
        data = self._load()
        if user_id not in data:
            return False
        if score > data[user_id].get('high_score', 0):
            data[user_id]['high_score'] = score
            self._save(data)
            return True
        return False
