"""P5 settings-persistence round-trip tests (headless).

Covers the chain that previously only had in-memory coverage:
UserDB settings API → SettingsScene write-through → re-login restore
(SceneDirector._load_user_settings), including the P2 resolution tier.
"""

from airwar.game.scaled_viewport import ScaledViewport
from airwar.game.scene_director import SceneDirector
from airwar.scenes.scene import SceneManager
from airwar.scenes.settings_scene import SettingsScene
from airwar.utils.database import UserDB
from airwar.window.window import RESOLUTION_TIERS, Window


def _make_db(tmp_path) -> UserDB:
    db = UserDB(str(tmp_path / "users.json"))
    db.create_user("alice", "pw123")
    return db


class TestUserDbSettingsApi:
    def test_settings_round_trip_across_instances(self, tmp_path):
        db = _make_db(tmp_path)
        assert db.update_user_settings("alice", {"ctrl_mode": "toggle", "resolution_tier": "S"}) is True

        # Simulate "exit the game and relaunch": a fresh UserDB on the same file.
        reopened = UserDB(str(tmp_path / "users.json"))
        settings = reopened.get_user_settings("alice")

        assert settings["ctrl_mode"] == "toggle"
        assert settings["resolution_tier"] == "S"
        # Untouched keys still fall back to the defaults.
        assert settings["shift_boost_mode"] == UserDB.DEFAULT_SETTINGS["shift_boost_mode"]

    def test_unknown_user_gets_independent_defaults_copy(self, tmp_path):
        db = _make_db(tmp_path)
        settings = db.get_user_settings("nobody")

        assert settings == UserDB.DEFAULT_SETTINGS
        settings["ctrl_mode"] = "toggle"
        # Mutating the returned dict must not leak into the class defaults.
        assert db.get_user_settings("nobody")["ctrl_mode"] == UserDB.DEFAULT_SETTINGS["ctrl_mode"]


def _bare_settings_scene(db, username, applied: list) -> SettingsScene:
    """SettingsScene without __init__: only the attrs _cycle_resolution touches."""
    scene = object.__new__(SettingsScene)
    scene._db = db
    scene._username = username
    scene._settings_ref = {}
    scene._message = ""
    scene._message_timer = 0
    scene._on_resolution_tier = applied.append
    return scene


class TestSettingsScenePersistence:
    def test_cycle_resolution_writes_through_to_db(self, tmp_path):
        db = _make_db(tmp_path)
        applied = []
        scene = _bare_settings_scene(db, "alice", applied)

        scene._cycle_resolution()  # default M -> L

        assert db.get_user_settings("alice")["resolution_tier"] == "L"
        assert applied == ["L"]

    def test_save_to_db_without_login_is_noop(self, tmp_path):
        scene = _bare_settings_scene(None, None, [])
        scene._settings_ref["resolution_tier"] = "L"
        scene._save_to_db()  # guest session: must not raise


class TestLoginSettingsRestore:
    def test_load_user_settings_restores_and_applies_tier(self, tmp_path):
        db = _make_db(tmp_path)
        db.update_user_settings("alice", {"ctrl_mode": "toggle", "resolution_tier": "S"})
        window = Window()  # bare window: resize is pure bookkeeping headless
        director = SceneDirector(window, SceneManager(), db, ScaledViewport())
        director._current_user = "alice"

        director._load_user_settings()

        assert director._settings_ref["ctrl_mode"] == "toggle"
        assert director._settings_ref["resolution_tier"] == "S"
        # The persisted tier is applied to the OS window immediately.
        assert (window._width, window._height) == RESOLUTION_TIERS["S"]

    def test_guest_login_skips_restore(self, tmp_path):
        window = Window()
        director = SceneDirector(window, SceneManager(), _make_db(tmp_path), ScaledViewport())
        director._current_user = "Guest"
        size_before = (window._width, window._height)

        director._load_user_settings()

        assert "resolution_tier" not in director._settings_ref
        assert (window._width, window._height) == size_before
