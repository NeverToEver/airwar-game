import pytest
import pygame
from airwar.utils.mouse_interaction import MouseSelectableMixin, MouseInteractiveMixin


class TestMouseSelectableMixin:
    def test_initialization(self):
        mixin = MouseSelectableMixin()
        assert mixin._hovered_index == -1
        assert mixin._option_rects == []

    def test_register_single_rect(self):
        mixin = MouseSelectableMixin()
        rect = pygame.Rect(0, 0, 100, 50)
        mixin.append_option_rect(rect)
        assert len(mixin._option_rects) == 1
        assert mixin._option_rects[0] == rect

    def test_clear_rects(self):
        mixin = MouseSelectableMixin()
        mixin.append_option_rect(pygame.Rect(0, 0, 100, 50))
        mixin.append_option_rect(pygame.Rect(0, 100, 100, 50))
        mixin.clear_option_rects()
        assert len(mixin._option_rects) == 0

    def test_hover_tracking(self):
        mixin = MouseSelectableMixin()
        rect = pygame.Rect(0, 0, 100, 50)
        mixin.append_option_rect(rect)
        
        mixin.handle_mouse_motion((50, 25))
        assert mixin._hovered_index == 0
        assert mixin.is_hovered(0) == True
        
        mixin.handle_mouse_motion((200, 200))
        assert mixin._hovered_index == -1
        assert mixin.is_hovered(0) == False

    def test_hover_with_multiple_rects(self):
        mixin = MouseSelectableMixin()
        rects = [
            pygame.Rect(0, 0, 100, 50),
            pygame.Rect(0, 100, 100, 50),
            pygame.Rect(0, 200, 100, 50),
        ]
        for rect in rects:
            mixin.append_option_rect(rect)
        
        mixin.handle_mouse_motion((50, 25))
        assert mixin._hovered_index == 0
        
        mixin.handle_mouse_motion((50, 125))
        assert mixin._hovered_index == 1
        
        mixin.handle_mouse_motion((50, 225))
        assert mixin._hovered_index == 2

    def test_click_handling(self):
        mixin = MouseSelectableMixin()
        rect = pygame.Rect(0, 0, 100, 50)
        mixin.append_option_rect(rect)
        
        clicked = mixin.handle_mouse_click((50, 25))
        assert clicked == True
        
        not_clicked = mixin.handle_mouse_click((200, 200))
        assert not_clicked == False

    def test_click_with_callback(self):
        mixin = MouseSelectableMixin()
        rect = pygame.Rect(0, 0, 100, 50)
        mixin.append_option_rect(rect)
        
        callback_result = []
        def test_callback(index):
            callback_result.append(index)
        
        mixin.set_mouse_callbacks(on_click=test_callback)
        
        mixin.handle_mouse_click((50, 25))
        assert callback_result == [0]

    def test_hover_callback(self):
        mixin = MouseSelectableMixin()
        rects = [
            pygame.Rect(0, 0, 100, 50),
            pygame.Rect(0, 100, 100, 50),
        ]
        for rect in rects:
            mixin.append_option_rect(rect)
        
        callback_result = []
        def hover_callback(index):
            callback_result.append(index)
        
        mixin.set_mouse_callbacks(on_hover=hover_callback)
        
        mixin.handle_mouse_motion((50, 25))
        assert callback_result == [0]
        
        mixin.handle_mouse_motion((50, 125))
        assert callback_result == [0, 1]
        
        mixin.handle_mouse_motion((50, 225))
        assert callback_result == [0, 1]

    def test_get_effective_selected_index(self):
        mixin = MouseSelectableMixin()
        
        result = mixin.get_effective_selected_index(keyboard_selected=2)
        assert result == 2
        
        rect = pygame.Rect(0, 0, 100, 50)
        mixin.append_option_rect(rect)
        mixin.handle_mouse_motion((50, 25))
        
        result = mixin.get_effective_selected_index(keyboard_selected=2)
        assert result == 0

    def test_clear_hover(self):
        mixin = MouseSelectableMixin()
        rect = pygame.Rect(0, 0, 100, 50)
        mixin.append_option_rect(rect)
        
        mixin.handle_mouse_motion((50, 25))
        assert mixin._hovered_index == 0
        
        mixin.clear_hover()
        assert mixin._hovered_index == -1

    def test_update_option_rects(self):
        mixin = MouseSelectableMixin()
        rects = [
            pygame.Rect(0, 0, 100, 50),
            pygame.Rect(0, 100, 100, 50),
        ]
        mixin.update_option_rects(rects)
        assert mixin._option_rects == rects


class TestMouseInteractiveMixin:
    def test_initialization(self):
        mixin = MouseInteractiveMixin()
        assert mixin._button_rects == {}
        assert mixin._hovered_button is None

    def test_register_single_button(self):
        mixin = MouseInteractiveMixin()
        rect = pygame.Rect(0, 0, 100, 50)
        mixin.register_button('test', rect)
        assert mixin.get_button_rect('test') == rect

    def test_register_multiple_buttons(self):
        mixin = MouseInteractiveMixin()
        mixin.register_button('btn1', pygame.Rect(0, 0, 100, 50))
        mixin.register_button('btn2', pygame.Rect(0, 100, 100, 50))
        
        assert mixin.get_button_rect('btn1') == pygame.Rect(0, 0, 100, 50)
        assert mixin.get_button_rect('btn2') == pygame.Rect(0, 100, 100, 50)

    def test_unregister_button(self):
        mixin = MouseInteractiveMixin()
        mixin.register_button('test', pygame.Rect(0, 0, 100, 50))
        mixin.unregister_button('test')
        assert mixin.get_button_rect('test') is None

    def test_clear_buttons(self):
        mixin = MouseInteractiveMixin()
        mixin.register_button('btn1', pygame.Rect(0, 0, 100, 50))
        mixin.register_button('btn2', pygame.Rect(0, 100, 100, 50))
        mixin.clear_buttons()
        assert len(mixin._button_rects) == 0

    def test_hover_tracking(self):
        mixin = MouseInteractiveMixin()
        rect = pygame.Rect(0, 0, 100, 50)
        mixin.register_button('test', rect)
        
        mixin.handle_mouse_motion((50, 25))
        assert mixin._hovered_button == 'test'
        assert mixin.is_button_hovered('test') == True
        assert mixin.get_hovered_button() == 'test'
        
        mixin.handle_mouse_motion((200, 200))
        assert mixin._hovered_button is None
        assert mixin.is_button_hovered('test') == False
        assert mixin.get_hovered_button() is None

    def test_hover_with_multiple_buttons(self):
        mixin = MouseInteractiveMixin()
        mixin.register_button('btn1', pygame.Rect(0, 0, 100, 50))
        mixin.register_button('btn2', pygame.Rect(0, 100, 100, 50))
        
        mixin.handle_mouse_motion((50, 25))
        assert mixin._hovered_button == 'btn1'
        
        mixin.handle_mouse_motion((50, 125))
        assert mixin._hovered_button == 'btn2'

    def test_click_handling(self):
        mixin = MouseInteractiveMixin()
        rect = pygame.Rect(0, 0, 100, 50)
        mixin.register_button('test', rect)
        
        clicked = mixin.handle_mouse_click((50, 25))
        assert clicked == True
        
        not_clicked = mixin.handle_mouse_click((200, 200))
        assert not_clicked == False

    def test_click_with_callback(self):
        mixin = MouseInteractiveMixin()
        rect = pygame.Rect(0, 0, 100, 50)
        mixin.register_button('test', rect)
        
        callback_result = []
        def test_callback(name):
            callback_result.append(name)
        
        mixin.set_button_callbacks(on_click=test_callback)
        
        mixin.handle_mouse_click((50, 25))
        assert callback_result == ['test']

    def test_hover_callback(self):
        mixin = MouseInteractiveMixin()
        mixin.register_button('btn1', pygame.Rect(0, 0, 100, 50))
        mixin.register_button('btn2', pygame.Rect(0, 100, 100, 50))
        
        callback_result = []
        def hover_callback(name):
            callback_result.append(name)
        
        mixin.set_button_callbacks(on_hover=hover_callback)
        
        mixin.handle_mouse_motion((50, 25))
        assert callback_result == ['btn1']
        
        mixin.handle_mouse_motion((50, 125))
        assert callback_result == ['btn1', 'btn2']
        
        mixin.handle_mouse_motion((50, 225))
        assert callback_result == ['btn1', 'btn2']

    def test_clear_hover(self):
        mixin = MouseInteractiveMixin()
        rect = pygame.Rect(0, 0, 100, 50)
        mixin.register_button('test', rect)
        
        mixin.handle_mouse_motion((50, 25))
        assert mixin._hovered_button == 'test'
        
        mixin.clear_hover()
        assert mixin._hovered_button is None

    def test_nonexistent_button_returns_none(self):
        mixin = MouseInteractiveMixin()
        assert mixin.get_button_rect('nonexistent') is None
