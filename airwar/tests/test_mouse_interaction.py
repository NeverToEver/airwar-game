"""Coverage push for airwar.utils.mouse_interaction — MouseSelectableMixin and MouseInteractiveMixin.

Targets the high-leverage hover / click / drag / callback paths on both
mixins, with focus on lifecycle transitions (hover-enter, hover-exit, click)
and callback wiring.  The two mixins are exercised in isolation against
lightweight stand-in hosts (no scene plumbing required).
"""

import pygame

from airwar.utils.mouse_interaction import MouseInteractiveMixin, MouseSelectableMixin

# ─── MouseSelectableMixin ────────────────────────────────────────────────────


class TestMouseSelectableMixin:
    def test_init_starts_with_no_hover_and_no_rects(self) -> None:
        host = _SelectableHost()
        assert host._hovered_index == -1
        assert host._option_rects == []
        assert host._on_hover_callback is None
        assert host._on_click_callback is None

    def test_set_mouse_callbacks(self) -> None:
        host = _SelectableHost()
        host.set_mouse_callbacks(on_hover=lambda i: None, on_click=lambda i: None)
        assert host._on_hover_callback is not None
        assert host._on_click_callback is not None

    def test_update_option_rects_replaces_full_list(self) -> None:
        host = _SelectableHost()
        rects = [pygame.Rect(0, 0, 10, 10), pygame.Rect(20, 20, 10, 10)]
        host.update_option_rects(rects)
        assert host._option_rects == rects

    def test_append_option_rect_extends_list(self) -> None:
        host = _SelectableHost()
        host.append_option_rect(pygame.Rect(0, 0, 10, 10))
        host.append_option_rect(pygame.Rect(20, 20, 10, 10))
        assert len(host._option_rects) == 2
        assert host._option_rects[0] == pygame.Rect(0, 0, 10, 10)

    def test_clear_option_rects_resets(self) -> None:
        host = _SelectableHost()
        host.append_option_rect(pygame.Rect(0, 0, 10, 10))
        host.clear_option_rects()
        assert host._option_rects == []

    def test_motion_updates_hover_and_fires_callback(self) -> None:
        host = _SelectableHost()
        host.update_option_rects([pygame.Rect(0, 0, 100, 100), pygame.Rect(200, 0, 100, 100)])
        events: list[int] = []
        host.set_mouse_callbacks(on_hover=events.append)

        host.handle_mouse_motion((10, 10))
        assert host._hovered_index == 0
        assert events == [0]

    def test_motion_same_index_does_not_refire_callback(self) -> None:
        host = _SelectableHost()
        host.update_option_rects([pygame.Rect(0, 0, 100, 100)])
        events: list[int] = []
        host.set_mouse_callbacks(on_hover=events.append)

        host.handle_mouse_motion((10, 10))
        host.handle_mouse_motion((20, 20))  # same index, no callback
        assert events == [0]

    def test_motion_outside_clears_hover_but_no_callback_for_negative(self) -> None:
        host = _SelectableHost()
        host.update_option_rects([pygame.Rect(0, 0, 100, 100)])
        events: list[int] = []
        host.set_mouse_callbacks(on_hover=events.append)

        host.handle_mouse_motion((10, 10))
        host.handle_mouse_motion((9999, 9999))  # outside
        assert host._hovered_index == -1
        # Negative transitions are not surfaced to the callback (avoids
        # spurious "deselect" notifications on every mouse move).
        assert events == [0]

    def test_click_inside_rect_fires_callback(self) -> None:
        host = _SelectableHost()
        host.update_option_rects([pygame.Rect(0, 0, 100, 100), pygame.Rect(200, 0, 100, 100)])
        clicks: list[int] = []
        host.set_mouse_callbacks(on_click=clicks.append)

        handled = host.handle_mouse_click((50, 50))
        assert handled is True
        assert clicks == [0]

    def test_click_outside_returns_false(self) -> None:
        host = _SelectableHost()
        host.update_option_rects([pygame.Rect(0, 0, 100, 100)])
        clicks: list[int] = []
        host.set_mouse_callbacks(on_click=clicks.append)

        handled = host.handle_mouse_click((9999, 9999))
        assert handled is False
        assert clicks == []

    def test_is_hovered_and_clear_hover(self) -> None:
        host = _SelectableHost()
        host.update_option_rects([pygame.Rect(0, 0, 100, 100), pygame.Rect(200, 0, 100, 100)])
        host.handle_mouse_motion((50, 50))
        assert host.is_hovered(0) is True
        assert host.is_hovered(1) is False
        host.clear_hover()
        assert host.is_hovered(0) is False

    def test_get_effective_selected_prefers_hover(self) -> None:
        host = _SelectableHost()
        host.update_option_rects([pygame.Rect(0, 0, 100, 100), pygame.Rect(200, 0, 100, 100)])
        host.handle_mouse_motion((250, 50))
        assert host.get_effective_selected_index(keyboard_selected=0) == 1
        host.clear_hover()
        assert host.get_effective_selected_index(keyboard_selected=0) == 0


# ─── MouseInteractiveMixin ───────────────────────────────────────────────────


class TestMouseInteractiveMixin:
    def test_init_starts_with_no_hover_and_no_buttons(self) -> None:
        host = _InteractiveHost()
        assert host._hovered_button is None
        assert host._button_rects == {}
        assert host._on_button_hover_callback is None
        assert host._on_button_click_callback is None

    def test_set_button_callbacks(self) -> None:
        host = _InteractiveHost()
        host.set_button_callbacks(on_hover=lambda n: None, on_click=lambda n: None)
        assert host._on_button_hover_callback is not None
        assert host._on_button_click_callback is not None

    def test_register_and_get_button_rect(self) -> None:
        host = _InteractiveHost()
        rect = pygame.Rect(0, 0, 50, 50)
        host.register_button("play", rect)
        assert host.get_button_rect("play") == rect
        assert host.get_button_rect("missing") is None

    def test_register_overwrites_existing_button(self) -> None:
        host = _InteractiveHost()
        host.register_button("play", pygame.Rect(0, 0, 50, 50))
        host.register_button("play", pygame.Rect(100, 100, 50, 50))
        assert host.get_button_rect("play") == pygame.Rect(100, 100, 50, 50)

    def test_unregister_button_removes_it(self) -> None:
        host = _InteractiveHost()
        host.register_button("play", pygame.Rect(0, 0, 50, 50))
        host.unregister_button("play")
        assert host.get_button_rect("play") is None

    def test_unregister_unknown_button_is_noop(self) -> None:
        host = _InteractiveHost()
        # Should not raise
        host.unregister_button("never_existed")
        assert host._button_rects == {}

    def test_clear_buttons(self) -> None:
        host = _InteractiveHost()
        host.register_button("a", pygame.Rect(0, 0, 10, 10))
        host.register_button("b", pygame.Rect(20, 0, 10, 10))
        host.clear_buttons()
        assert host._button_rects == {}

    def test_motion_updates_hover_and_fires_callback(self) -> None:
        host = _InteractiveHost()
        host.register_button("a", pygame.Rect(0, 0, 100, 100))
        host.register_button("b", pygame.Rect(200, 0, 100, 100))
        events: list[str] = []
        host.set_button_callbacks(on_hover=events.append)

        host.handle_mouse_motion((50, 50))
        assert host._hovered_button == "a"
        assert events == ["a"]

    def test_motion_same_button_does_not_refire(self) -> None:
        host = _InteractiveHost()
        host.register_button("a", pygame.Rect(0, 0, 100, 100))
        events: list[str] = []
        host.set_button_callbacks(on_hover=events.append)

        host.handle_mouse_motion((10, 10))
        host.handle_mouse_motion((20, 20))  # same button
        assert events == ["a"]

    def test_motion_outside_buttons_clears_hover_without_callback(self) -> None:
        host = _InteractiveHost()
        host.register_button("a", pygame.Rect(0, 0, 100, 100))
        events: list[str] = []
        host.set_button_callbacks(on_hover=events.append)

        host.handle_mouse_motion((10, 10))
        host.handle_mouse_motion((9999, 9999))
        assert host._hovered_button is None
        # None transitions are NOT surfaced (matches MouseSelectableMixin).
        assert events == ["a"]

    def test_click_button_fires_callback_and_marks_hovered(self) -> None:
        host = _InteractiveHost()
        host.register_button("play", pygame.Rect(0, 0, 100, 100))
        clicks: list[str] = []
        host.set_button_callbacks(on_click=clicks.append)

        handled = host.handle_mouse_click((50, 50))
        assert handled is True
        assert clicks == ["play"]
        assert host._hovered_button == "play"

    def test_click_outside_returns_false(self) -> None:
        host = _InteractiveHost()
        host.register_button("play", pygame.Rect(0, 0, 100, 100))
        clicks: list[str] = []
        host.set_button_callbacks(on_click=clicks.append)

        handled = host.handle_mouse_click((9999, 9999))
        assert handled is False
        assert clicks == []
        # Click outside does not change hover state.
        assert host._hovered_button is None

    def test_is_button_hovered_and_get_hovered_button(self) -> None:
        host = _InteractiveHost()
        host.register_button("play", pygame.Rect(0, 0, 100, 100))
        host.handle_mouse_motion((10, 10))
        assert host.is_button_hovered("play") is True
        assert host.is_button_hovered("missing") is False
        assert host.get_hovered_button() == "play"

    def test_clear_hover(self) -> None:
        host = _InteractiveHost()
        host.register_button("play", pygame.Rect(0, 0, 100, 100))
        host.handle_mouse_motion((10, 10))
        host.clear_hover()
        assert host.get_hovered_button() is None
        assert host.is_button_hovered("play") is False


# ─── host stand-ins ──────────────────────────────────────────────────────────


class _SelectableHost(MouseSelectableMixin):
    """Minimal host that exposes the mixin attributes without scene plumbing."""

    def __init__(self) -> None:
        MouseSelectableMixin.__init__(self)


class _InteractiveHost(MouseInteractiveMixin):
    """Minimal host that exposes the mixin attributes without scene plumbing."""

    def __init__(self) -> None:
        MouseInteractiveMixin.__init__(self)
