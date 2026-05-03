import pygame

from airwar.scenes.welcome_scene import WelcomeScene


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

    for name in ["username_field", "password_field", "login", "register", "skip_login", "delete_user"]:
        rect = scene.get_button_rect(name)
        assert rect is not None
        assert rect.width >= 44
        assert rect.height >= 38
