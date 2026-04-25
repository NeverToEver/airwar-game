import pygame
from typing import List, Optional, Callable, Dict


class MouseSelectableMixin:
    """Mixin for list-selection menu scenes with mouse interaction support.

    Provides unified mouse interaction for scenes using list-based selection.
    Supports hover detection, click handling, and prioritizes mouse hover
    over keyboard selection.

    Usage:
        class MyMenuScene(Scene, MouseSelectableMixin):
            def __init__(self):
                Scene.__init__(self)
                MouseSelectableMixin.__init__(self)

    Attributes:
        _hovered_index: Currently hovered option index (-1 if none).
        _option_rects: List of pygame.Rect for each option.
        _on_hover_callback: Optional callback for hover state changes.
        _on_click_callback: Optional callback for option clicks.
    """

    def __init__(self):
        self._hovered_index: int = -1
        self._option_rects: List[pygame.Rect] = []
        self._on_hover_callback: Optional[Callable[[int], None]] = None
        self._on_click_callback: Optional[Callable[[int], None]] = None

    def set_mouse_callbacks(
        self,
        on_hover: Optional[Callable[[int], None]] = None,
        on_click: Optional[Callable[[int], None]] = None
    ) -> None:
        self._on_hover_callback = on_hover
        self._on_click_callback = on_click

    def handle_mouse_motion(self, mouse_pos: tuple) -> None:
        new_hovered = self._get_option_index_at_pos(mouse_pos)
        if new_hovered != self._hovered_index:
            self._hovered_index = new_hovered
            if self._on_hover_callback and new_hovered >= 0:
                self._on_hover_callback(new_hovered)

    def handle_mouse_click(self, mouse_pos: tuple) -> bool:
        clicked_index = self._get_option_index_at_pos(mouse_pos)
        if clicked_index >= 0:
            if self._on_click_callback:
                self._on_click_callback(clicked_index)
            return True
        return False

    def _get_option_index_at_pos(self, pos: tuple) -> int:
        for i, rect in enumerate(self._option_rects):
            if rect.collidepoint(pos):
                return i
        return -1

    def get_effective_selected_index(self, keyboard_selected: int) -> int:
        if self._hovered_index >= 0:
            return self._hovered_index
        return keyboard_selected

    def is_hovered(self, index: int) -> bool:
        return self._hovered_index == index

    def clear_hover(self) -> None:
        self._hovered_index = -1

    def update_option_rects(self, rects: List[pygame.Rect]) -> None:
        self._option_rects = rects

    def append_option_rect(self, rect: pygame.Rect) -> None:
        self._option_rects.append(rect)

    def clear_option_rects(self) -> None:
        self._option_rects.clear()


class MouseInteractiveMixin:
    """Mixin for button-based scenes with mouse interaction support.

    Provides unified mouse interaction for scenes using named buttons.
    Supports button registration, hover detection, click handling,
    and hover/click callbacks.

    Usage:
        class MyScene(Scene, MouseInteractiveMixin):
            def __init__(self):
                Scene.__init__(self)
                MouseInteractiveMixin.__init__(self)

    Attributes:
        _button_rects: Dictionary mapping button names to their pygame.Rect.
        _hovered_button: Currently hovered button name (None if none).
        _on_button_hover_callback: Optional callback for hover state changes.
        _on_button_click_callback: Optional callback for button clicks.
    """

    def __init__(self):
        self._button_rects: Dict[str, pygame.Rect] = {}
        self._hovered_button: Optional[str] = None
        self._on_button_hover_callback: Optional[Callable[[str], None]] = None
        self._on_button_click_callback: Optional[Callable[[str], None]] = None

    def set_button_callbacks(
        self,
        on_hover: Optional[Callable[[str], None]] = None,
        on_click: Optional[Callable[[str], None]] = None
    ) -> None:
        self._on_button_hover_callback = on_hover
        self._on_button_click_callback = on_click

    def register_button(self, name: str, rect: pygame.Rect) -> None:
        self._button_rects[name] = rect

    def unregister_button(self, name: str) -> None:
        if name in self._button_rects:
            del self._button_rects[name]

    def clear_buttons(self) -> None:
        self._button_rects.clear()

    def get_button_rect(self, name: str) -> Optional[pygame.Rect]:
        return self._button_rects.get(name)

    def handle_mouse_motion(self, mouse_pos: tuple) -> None:
        new_hovered = self._get_button_at_pos(mouse_pos)
        if new_hovered != self._hovered_button:
            self._hovered_button = new_hovered
            if self._on_button_hover_callback and new_hovered:
                self._on_button_hover_callback(new_hovered)

    def handle_mouse_click(self, mouse_pos: tuple) -> bool:
        clicked_button = self._get_button_at_pos(mouse_pos)
        if clicked_button:
            self._hovered_button = clicked_button
            if self._on_button_click_callback:
                self._on_button_click_callback(clicked_button)
            return True
        return False

    def _get_button_at_pos(self, pos: tuple) -> Optional[str]:
        for name, rect in self._button_rects.items():
            if rect.collidepoint(pos):
                return name
        return None

    def is_button_hovered(self, name: str) -> bool:
        return self._hovered_button == name

    def get_hovered_button(self) -> Optional[str]:
        return self._hovered_button

    def clear_hover(self) -> None:
        self._hovered_button = None
