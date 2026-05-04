import pygame

from airwar.scenes.welcome_scene import WelcomeScene
from airwar.utils.database import UserDB


def _make_scene() -> WelcomeScene:
    pygame.font.init()
    scene = WelcomeScene()
    scene.enter()
    return scene


def test_welcome_login_layout_keeps_chinese_labels_outside_inputs() -> None:
    scene = _make_scene()
    layout = scene._get_login_layout(120, 140)

    panel_rect = pygame.Rect(120, 140, scene.PANEL_W, scene.PANEL_H)
    for rect in layout.values():
        if isinstance(rect, pygame.Rect):
            assert panel_rect.contains(rect)

    assert layout["username_label"].right < layout["username_field"].left
    assert layout["password_label"].right < layout["password_field"].left
    assert not layout["username_label"].colliderect(layout["username_field"])
    assert not layout["password_label"].colliderect(layout["password_field"])
    assert layout["username_field"].bottom + scene.LOGIN_ROW_GAP <= layout["password_field"].top
    assert not layout["login"].colliderect(layout["register"])
    assert not layout["guest"].colliderect(layout["delete"])


def test_welcome_login_render_registers_new_button_regions() -> None:
    scene = _make_scene()
    surface = pygame.Surface((1280, 720), pygame.SRCALPHA)

    scene.render(surface)

    for name in [
        "username_field",
        "username_dropdown",
        "password_field",
        "login",
        "register",
        "skip_login",
        "delete_user",
    ]:
        rect = scene.get_button_rect(name)
        assert rect is not None
        assert rect.width >= 44
        assert rect.height >= 38


def test_welcome_defaults_to_last_login_user_and_password_focus(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "users.json"
    db = UserDB(str(db_path))
    assert db.create_user("alpha", "secret") is True
    assert db.create_user("bravo", "secret") is True
    assert db.record_login("alpha") is True
    assert db.record_login("bravo") is True

    monkeypatch.setattr("airwar.scenes.welcome_scene.UserDB", lambda: UserDB(str(db_path)))
    scene = _make_scene()

    assert scene.username == "bravo"
    assert scene.password == ""
    assert scene.focus == "password"
    assert scene.known_usernames == ["bravo", "alpha"]


def test_welcome_dropdown_selects_known_user_and_moves_focus_to_password() -> None:
    scene = _make_scene()
    scene.known_usernames = ["bravo", "alpha"]
    scene.username = ""
    scene.focus = "username"
    scene.show_user_dropdown = True

    scene._select_known_user(1)

    assert scene.username == "alpha"
    assert scene.password == ""
    assert scene.focus == "password"
    assert scene.show_user_dropdown is False


def test_welcome_successful_login_records_last_user(tmp_path) -> None:
    scene = _make_scene()
    scene.db = UserDB(str(tmp_path / "users.json"))
    assert scene.db.create_user("alpha", "secret") is True

    scene.username = "alpha"
    scene.password = "secret"
    scene._do_login()

    assert scene.running is False
    assert scene.db.get_last_login_user() == "alpha"


def test_delete_user_requires_current_password(tmp_path) -> None:
    scene = _make_scene()
    scene.db = UserDB(str(tmp_path / "users.json"))

    assert scene.db.create_user("pilot", "secret") is True
    scene.username = "pilot"
    scene.password = ""
    scene._handle_button_click("delete_user")
    scene._do_delete_user()

    assert scene.db.user_exists("pilot") is True
    assert scene.message == "请输入当前密码后再删除"
    assert scene._is_error is True

    scene.password = "secret"
    scene._handle_button_click("delete_user")
    scene._do_delete_user()

    assert scene.db.user_exists("pilot") is False
    assert scene.message == "用户 pilot 已删除"
