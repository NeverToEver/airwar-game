import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestWindowFullscreen:
    @pytest.mark.smoke
    def test_window_initial_state_not_fullscreen(self):
        from airwar.window import Window
        window = Window()
        assert window._is_fullscreen is False

    @pytest.mark.smoke
    def test_window_is_fullscreen_returns_false_initially(self):
        from airwar.window import Window
        window = Window()
        assert window.is_fullscreen() is False

    def test_window_stores_windowed_size_on_init(self):
        from airwar.window import Window
        window = Window(1920, 1080)
        assert window._windowed_size == (1920, 1080)
        assert window._default_width == 1920
        assert window._default_height == 1080

    def test_window_fullscreen_state_toggle_without_init(self):
        from airwar.window import Window
        window = Window()
        window.toggle_fullscreen()
        assert window._is_fullscreen is False
