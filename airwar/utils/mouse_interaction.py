import pygame
from typing import List, Optional, Callable, Dict


class MouseSelectableMixin:
    """
    鼠标可选中混入类，为列表选择模式的菜单场景提供统一的鼠标交互支持。
    
    使用方式:
        class MyMenuScene(Scene, MouseSelectableMixin):
            def __init__(self):
                Scene.__init__(self)
                MouseSelectableMixin.__init__(self)
    
    特性:
        - 鼠标悬停检测：自动跟踪鼠标位置，更新悬停状态
        - 鼠标点击处理：通过索引处理点击事件
        - 键盘/鼠标状态优先级：鼠标悬停优先于键盘选中状态
    
    典型用法:
        1. 在渲染选项时调用 append_option_rect() 注册每个选项的矩形区域
        2. 在 handle_events() 中处理 pygame.MOUSEMOTION 和 pygame.MOUSEBUTTONDOWN 事件
        3. 使用 get_effective_selected_index() 获取有效的选中索引（鼠标优先）
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
    """
    鼠标交互混入类，为按钮模式的场景提供统一的鼠标交互支持。
    
    使用方式:
        class MyScene(Scene, MouseInteractiveMixin):
            def __init__(self):
                Scene.__init__(self)
                MouseInteractiveMixin.__init__(self)
    
    特性:
        - 命名按钮管理：通过字符串名称标识不同按钮
        - 鼠标悬停检测：自动跟踪鼠标位置，更新悬停状态
        - 鼠标点击处理：通过按钮名称处理点击事件
        - 悬停回调支持：支持自定义悬停状态变化时的回调
    
    典型用法:
        1. 在渲染按钮时调用 register_button() 注册每个按钮的矩形区域和名称
        2. 在 handle_events() 中处理 pygame.MOUSEMOTION 和 pygame.MOUSEBUTTONDOWN 事件
        3. 使用 is_button_hovered() 检查特定按钮是否处于悬停状态
        4. 使用 get_hovered_button() 获取当前悬停的按钮名称
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
