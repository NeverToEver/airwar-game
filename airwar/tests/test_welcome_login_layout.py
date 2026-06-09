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


def test_delete_confirm_buttons_delete_or_cancel_user(tmp_path) -> None:
    scene = _make_scene()
    scene.db = UserDB(str(tmp_path / "users.json"))
    assert scene.db.create_user("pilot", "secret") is True

    scene.username = "pilot"
    scene.password = "secret"
    scene._handle_button_click("delete_user")
    scene._handle_button_click("delete_confirm_no")

    assert scene.show_delete_confirm is False
    assert scene.db.user_exists("pilot") is True

    scene._handle_button_click("delete_user")
    scene._handle_button_click("delete_confirm_yes")

    assert scene.show_delete_confirm is False
    assert scene.db.user_exists("pilot") is False
    assert scene.message == "用户 pilot 已删除"


# --- Regression tests for B1 (event.unicode crash) and B4 (responsive panel) ---

def test_welcome_login_keydown_without_unicode_does_not_crash() -> None:
    """Regression for B1: synthetic KEYDOWN with no `unicode` attribute
    must not crash the login panel even when username/password is focused.

    Repro: ``smoke_real_machine.py`` posts KEYDOWN events without
    ``unicode``; without the fix, ``login_panel.handle_input_key`` raised
    ``AttributeError("'pygame.event.Event' object has no attribute 'unicode'")``.
    """
    scene = _make_scene()
    # Reset state populated by UserDB's last-logged-in user (would otherwise
    # mask the assertion below).
    scene.username = ""
    scene.password = ""
    scene.focus = "username"
    # Synthetic event without the `unicode` field (as the smoke test does)
    ev = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_a, "mod": 0, "scancode": 0})
    scene.handle_events(ev)  # must not raise
    # No printable input was injected, so the username should remain empty
    assert scene.username == ""


def test_welcome_layout_keeps_benchmark_button_on_screen_at_small_window() -> None:
    """Regression for B4: at 984x553 (a typical small/laptop window) the
    benchmark and leaderboard buttons must remain within the screen
    bounds so the user can click them.

    Repro: pre-fix, the right panel was placed at y=734 (below the 553px
    screen bottom), dragging the benchmark button to y=1084 (off-screen).
    """
    scene = _make_scene()
    surface = pygame.Surface((984, 553), pygame.SRCALPHA)
    scene.render(surface)
    for name in ("benchmark", "leaderboard"):
        rect = scene.get_button_rect(name)
        assert rect is not None, f"{name} button not registered"
        assert 0 <= rect.bottom <= 553, f"{name} extends past screen: {rect}"
        assert 0 <= rect.top <= 553, f"{name} starts above screen: {rect}"


def test_welcome_layout_adaptive_panel_height() -> None:
    """At the design size, panel_h equals the natural PANEL_H; at a
    smaller viewport, panel_h shrinks to keep both panels on screen."""
    scene = _make_scene()
    big = scene._get_layout(1920, 1080)
    assert big["panel_h"] == scene.PANEL_H
    # Stacked mode: right panel + bottom clearance must fit in the screen
    small = scene._get_layout(984, 553)
    assert small["panel_h"] <= scene.PANEL_H
    assert small["right_y"] + small["panel_h"] + 96 <= 553, (
        f"stacked right panel overflows screen: right_y={small['right_y']} "
        f"panel_h={small['panel_h']} sh=553"
    )
