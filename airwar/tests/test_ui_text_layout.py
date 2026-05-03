import pytest
import pygame

from airwar.utils.fonts import get_cjk_font
from airwar.ui.scene_rendering_utils import (
    adaptive_box_width,
    fit_string_to_width,
    wrap_text,
)


@pytest.fixture(scope="module", autouse=True)
def _init_font():
    pygame.font.init()
    yield


def test_fit_string_to_width_never_exceeds_limit():
    font = get_cjk_font(24)
    fitted = fit_string_to_width(font, "返回主菜单保存并退出", 80)

    assert font.size(fitted)[0] <= 80


def test_wrap_text_keeps_chinese_lines_inside_width():
    font = get_cjk_font(24)
    lines = wrap_text("此操作不可撤销所有数据将被永久删除", font, 120, max_lines=3)

    assert 1 < len(lines) <= 3
    assert all(font.size(line)[0] <= 120 for line in lines)


def test_adaptive_box_width_grows_for_localized_menu_text():
    font = get_cjk_font(44)
    width = adaptive_box_width(font, ">> 返回主菜单", 120, 1024)

    assert width > 120
    assert width <= 1024 - 80
    assert font.size(">> 返回主菜单")[0] < width
