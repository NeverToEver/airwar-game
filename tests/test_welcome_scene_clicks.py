"""Regression tests for WelcomeScene mouse-button dispatch.

Every MOUSEBUTTONDOWN used to be swallowed by the user-dropdown elif
branch whenever the login panel existed (always after enter()) and the
dropdown was closed (the normal state), leaving all main-page buttons
unclickable.
"""

import pygame

from airwar.scenes.welcome_scene import WelcomeScene
from airwar.utils.database import UserDB


def _make_scene(tmp_path, monkeypatch) -> WelcomeScene:
    monkeypatch.setattr(
        "airwar.scenes.welcome_scene.UserDB",
        lambda: UserDB(db_path=str(tmp_path / "users.json")),
    )
    scene = WelcomeScene()
    scene.enter()
    return scene


def _click(scene: WelcomeScene, pos: tuple[int, int]) -> None:
    scene.handle_events(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))


class TestWelcomeSceneClicks:
    def test_difficulty_button_responds_to_click(self, tmp_path, monkeypatch):
        scene = _make_scene(tmp_path, monkeypatch)
        scene.register_button("diff_hard", pygame.Rect(100, 100, 80, 40))

        _click(scene, (140, 120))

        assert scene.selected_difficulty == "hard"

    def test_password_field_focuses_on_click(self, tmp_path, monkeypatch):
        scene = _make_scene(tmp_path, monkeypatch)
        scene.register_button("password_field", pygame.Rect(100, 100, 80, 40))

        _click(scene, (140, 120))

        assert scene.focus == "password"

    def test_click_outside_buttons_closes_dropdown(self, tmp_path, monkeypatch):
        scene = _make_scene(tmp_path, monkeypatch)
        scene.known_usernames = ["alice"]
        scene.show_user_dropdown = True

        _click(scene, (5, 5))

        assert scene.show_user_dropdown is False

    def test_dropdown_entry_click_still_consumes_event(self, tmp_path, monkeypatch):
        scene = _make_scene(tmp_path, monkeypatch)
        scene.known_usernames = ["alice"]
        scene.show_user_dropdown = True
        scene.register_button("known_user_0", pygame.Rect(100, 100, 80, 40))

        _click(scene, (140, 120))

        assert scene.username == "alice"
        assert scene.focus == "password"
