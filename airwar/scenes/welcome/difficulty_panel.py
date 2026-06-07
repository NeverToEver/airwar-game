"""Difficulty panel: radio-style selection, focus cycling, labels, CTA button.

Owns the right-panel render path: tutorial CTA, difficulty radio list, and
quick-controls reference. State mutations read/write ``scene.selected_difficulty``
and ``scene.focus`` directly through the host.
"""

from __future__ import annotations

import math
from typing import Any

import pygame

from airwar.config.design_tokens import SceneColors
from airwar.i18n import t
from airwar.ui.chamfered_panel import draw_chamfered_panel
from airwar.ui.scene_rendering_utils import fit_text_to_width

from .layout import (
    CHAMFER,
    DIFF_GAP,
    DIFF_OPTION_H,
    PANEL_H,
    PANEL_W,
)


class DifficultyPanel:
    """Right-side panel: tutorial CTA, difficulty selection, controls reference."""

    def __init__(self, scene: Any) -> None:
        self._scene = scene

    # -- State operations ----------------------------------------------

    def cycle_focus(self) -> None:
        """Advance focus through username -> password -> difficulty and wrap."""
        scene = self._scene
        order = ["username", "password", "difficulty"]
        idx = order.index(scene.focus) if scene.focus in order else 0
        scene.focus = order[(idx + 1) % len(order)]

    def select_difficulty(self, difficulty: str) -> None:
        scene = self._scene
        scene.difficulty_index = scene.difficulty_options.index(difficulty)
        scene.selected_difficulty = difficulty
        scene.focus = "difficulty"
        scene.show_user_dropdown = False

    def handle_difficulty_key(self, event: pygame.event.Event) -> None:
        """Move the difficulty index in response to up/down arrow keys."""
        scene = self._scene
        if event.key in (pygame.K_UP, pygame.K_w):
            scene.difficulty_index = (scene.difficulty_index - 1) % len(scene.difficulty_options)
            scene.selected_difficulty = scene.difficulty_options[scene.difficulty_index]
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            scene.difficulty_index = (scene.difficulty_index + 1) % len(scene.difficulty_options)
            scene.selected_difficulty = scene.difficulty_options[scene.difficulty_index]

    # -- Rendering ------------------------------------------------------

    def render(self, surface: pygame.Surface, px: int, py: int) -> None:
        """Render the right panel at the given top-left pixel coordinates."""
        SC = SceneColors
        scene = self._scene

        # Panel background
        draw_chamfered_panel(
            surface, px, py, PANEL_W, PANEL_H, SC.BG_PANEL_LIGHT, SC.BORDER_DIM, SC.GOLD_GLOW, CHAMFER
        )

        # Section title
        title = scene.section_font.render(t("welcome.briefing_title"), True, SC.GOLD_PRIMARY)
        surface.blit(title, title.get_rect(center=(px + PANEL_W // 2, py + 32)))

        sep_y = py + 58
        pygame.draw.line(surface, SC.BORDER_DIM, (px + 30, sep_y), (px + PANEL_W - 30, sep_y), 1)

        # -- Tutorial call-to-action --
        tutorial_y = py + 80
        tutorial_rect = pygame.Rect(px + 22, tutorial_y, PANEL_W - 44, 56)
        self._draw_tutorial_cta_button(surface, tutorial_rect)

        # -- Difficulty selection --
        diff_title_y = tutorial_rect.bottom + 14
        diff_label = scene.hint_font.render(t("welcome.difficulty_label"), True, SC.TEXT_DIM)
        surface.blit(diff_label, (px + 35, diff_title_y))

        diff_start_y = diff_title_y + 26
        for i, opt in enumerate(scene.difficulty_options):
            dy = diff_start_y + i * (DIFF_OPTION_H + DIFF_GAP)
            is_sel = i == scene.difficulty_index
            self._draw_diff_option(surface, px + 20, dy, PANEL_W - 40, scene.difficulty_labels[opt], i, is_sel)

        # -- Quick Controls reference --
        tips_title_y = (
            diff_start_y
            + len(scene.difficulty_options) * DIFF_OPTION_H
            + (len(scene.difficulty_options) - 1) * DIFF_GAP
            + 12
        )
        tips_label = scene.hint_font.render(t("welcome.controls_label"), True, SC.TEXT_DIM)
        surface.blit(tips_label, (px + 35, tips_title_y))

        # -- Leaderboard button (compact, near bottom) --
        lb_btn_w = 120
        lb_btn_h = 36
        lb_rect = pygame.Rect(
            px + PANEL_W - lb_btn_w - 20,
            py + PANEL_H - lb_btn_h - 16,
            lb_btn_w,
            lb_btn_h,
        )
        scene._login_panel._draw_ghost_button(surface, lb_rect, t("welcome.leaderboard_button"), "leaderboard")

        controls = [
            (t("welcome.controls.move_key"), t("welcome.controls.move")),
            (t("welcome.controls.boost_key"), t("welcome.controls.boost")),
            (t("welcome.controls.home_key"), t("welcome.controls.home")),
            (t("welcome.controls.dock_key"), t("welcome.controls.dock")),
            (t("welcome.controls.surrender_key"), t("welcome.controls.surrender")),
            (t("welcome.controls.pause_key"), t("welcome.controls.pause")),
            (t("welcome.controls.hud_key"), t("welcome.controls.hud")),
        ]
        tip_y = tips_title_y + 26
        key_x = px + 35
        desc_right = px + PANEL_W - 35
        max_key_w = desc_right - key_x - 92
        for key, desc in controls:
            key_surf = fit_text_to_width(scene.tip_font, key, SC.ACCENT_PRIMARY, max_key_w)
            desc_surf = scene.tip_font.render(desc, True, SC.TEXT_DIM)
            surface.blit(key_surf, (key_x, tip_y))
            surface.blit(desc_surf, (desc_right - desc_surf.get_width(), tip_y))
            tip_y += 17

    def _draw_diff_option(self, surface, x, y, w, label, index, selected):
        SC = SceneColors
        scene = self._scene
        btn_name = f"diff_{scene.difficulty_options[index]}"
        rect = pygame.Rect(x, y, w, DIFF_OPTION_H)
        scene.register_button(btn_name, rect)

        hover = scene.is_button_hovered(btn_name)
        is_active = selected or (scene.focus == "difficulty" and hover)

        if is_active:
            draw_chamfered_panel(
                surface, x - 2, y - 2, w + 4, DIFF_OPTION_H + 4, SC.BG_PANEL, SC.GOLD_GLOW, SC.GOLD_GLOW, 6
            )

        draw_chamfered_panel(
            surface,
            x,
            y,
            w,
            DIFF_OPTION_H,
            SC.BG_PANEL if is_active else SC.BG_PANEL_LIGHT,
            SC.GOLD_PRIMARY if is_active else SC.BORDER_DIM,
            None,
            6,
        )

        prefix = ">  " if is_active else "   "
        color = SC.GOLD_PRIMARY if is_active else SC.TEXT_DIM
        text = scene.input_font.render(f"{prefix}{label}", True, color)
        surface.blit(text, text.get_rect(midleft=(x + 20, y + DIFF_OPTION_H // 2)))

    def _draw_tutorial_cta_button(self, surface, rect: pygame.Rect) -> None:
        """Primary tutorial CTA with the same chamfer language as difficulty options."""
        SC = SceneColors
        scene = self._scene
        scene.register_button("tutorial", rect)
        hover = scene.is_button_hovered("tutorial")
        pulse = 0.5 + 0.5 * math.sin(scene.animation_time * 0.075)
        glow_alpha = int(58 + 48 * pulse)

        fill = (22, 54, 64) if hover else (16, 42, 52)
        border = (112, 224, 218) if hover else (82, 190, 190)
        gold = (220, 190, 96)

        draw_chamfered_panel(
            surface,
            rect.x - 5,
            rect.y - 5,
            rect.width + 10,
            rect.height + 10,
            SC.BG_PANEL,
            (*border, 150),
            (*border, glow_alpha),
            9,
        )
        draw_chamfered_panel(surface, rect.x, rect.y, rect.width, rect.height, fill, border, None, 7)

        accent_w = 7
        accent_points = [
            (rect.x + 7, rect.y + 9),
            (rect.x + accent_w + 8, rect.y + 9),
            (rect.x + accent_w + 2, rect.bottom - 9),
            (rect.x + 1, rect.bottom - 9),
        ]
        pygame.draw.polygon(surface, gold, accent_points)

        text_color = SC.TEXT_BRIGHT if hover else (224, 248, 248)
        text = fit_text_to_width(scene.input_font, t("welcome.tutorial_cta"), text_color, rect.width - 112)
        surface.blit(text, text.get_rect(midleft=(rect.x + 32, rect.centery)))

        chevron_x = rect.right - 42 + int(3 * pulse)
        chevron = [
            (chevron_x, rect.centery - 12),
            (chevron_x + 14, rect.centery),
            (chevron_x, rect.centery + 12),
        ]
        pygame.draw.lines(surface, gold if hover else border, False, chevron, 3)
