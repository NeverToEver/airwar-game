"""Welcome-scene modal overlays: guest confirm, delete confirm, shared dialog.

The host WelcomeScene delegates "show this confirmation overlay" state and
"render the overlay" logic here. Keyboard handlers stay in the scene so
focus and modal visibility transitions match the existing flow.
"""

from __future__ import annotations

from typing import Any

import pygame

from airwar.config.design_tokens import Modals, SceneColors
from airwar.i18n import t
from airwar.ui.chamfered_panel import draw_chamfered_panel
from airwar.ui.scene_rendering_utils import wrap_text


class WelcomeModals:
    """Guest and delete confirmation overlays, plus shared dialog helpers."""

    def __init__(self, scene: Any) -> None:
        self._scene = scene

    # -- State transitions --------------------------------------------

    def start_guest_session(self) -> None:
        scene = self._scene
        scene.username = "Guest"
        scene.running = False

    def dismiss_guest_confirm(self) -> None:
        self._scene.show_guest_confirm = False

    def handle_modal_mouse_click(self, pos: tuple[int, int], allowed_buttons: set[str]) -> None:
        """Dispatch a mouse click to one of the allowed modal buttons.

        Iterates the named buttons, picking the first whose rect contains
        the click position, then defers to the scene's button dispatcher.
        """
        scene = self._scene
        for name in allowed_buttons:
            rect = scene.get_button_rect(name)
            if rect and rect.collidepoint(pos):
                scene._handle_button_click(name)
                return

    def open_delete_confirm(self) -> None:
        """Public entry to the delete-confirm flow when a delete request is queued."""
        self._scene._login_panel.request_delete_user()

    # -- Rendering ----------------------------------------------------

    def render_guest_confirm(self, surface: pygame.Surface) -> None:
        """Overlay confirmation dialog: guest mode does not save progress."""
        SC = SceneColors
        scene = self._scene
        sw, sh = surface.get_width(), surface.get_height()

        # Dim overlay
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, Modals.DIM_ALPHA))
        surface.blit(overlay, (0, 0))

        # Dialog box
        dlg_w, dlg_h = Modals.GUEST_CONFIRM_W, Modals.GUEST_CONFIRM_H
        dlg_x = (sw - dlg_w) // 2
        dlg_y = (sh - dlg_h) // 2
        draw_chamfered_panel(surface, dlg_x, dlg_y, dlg_w, dlg_h, SC.BG_PANEL_LIGHT, SC.GOLD_PRIMARY, SC.GOLD_GLOW, 12)

        # Title
        title = scene.section_font.render(t("welcome.guest_confirm_title"), True, SC.GOLD_PRIMARY)
        surface.blit(title, title.get_rect(center=(sw // 2, dlg_y + Modals.TITLE_TOP_PAD)))

        self._render_dialog_lines(
            surface,
            [
                t("welcome.guest_confirm_line1"),
                t("welcome.guest_confirm_line2"),
            ],
            sw // 2,
            dlg_y + Modals.BODY_TOP_PAD,
            dlg_w - Modals.BODY_INSET_X,
        )

        # Buttons
        btn_w, btn_h = Modals.BUTTON_W, Modals.BUTTON_H
        gap = Modals.BUTTON_GAP
        total_btn_w = btn_w * 2 + gap
        btn_start_x = sw // 2 - total_btn_w // 2
        btn_y = dlg_y + dlg_h - Modals.BUTTON_BOTTOM_PAD

        # Confirm button (primary)
        confirm_rect = pygame.Rect(btn_start_x, btn_y, btn_w, btn_h)
        scene._login_panel._draw_button(
            surface,
            confirm_rect,
            t("welcome.guest_confirm_yes"),
            "guest_confirm_yes",
            SC.FOREST_GREEN,
            is_primary=True,
            is_focused=(scene.guest_confirm_focus == "yes"),
        )

        # Cancel button (secondary)
        cancel_rect = pygame.Rect(btn_start_x + btn_w + gap, btn_y, btn_w, btn_h)
        scene._login_panel._draw_button(
            surface,
            cancel_rect,
            t("welcome.guest_confirm_no"),
            "guest_confirm_no",
            SC.GOLD_DIM,
            is_focused=(scene.guest_confirm_focus == "no"),
        )

    def render_delete_confirm(self, surface: pygame.Surface) -> None:
        """Overlay confirmation dialog: delete user account."""
        SC = SceneColors
        scene = self._scene
        sw, sh = surface.get_width(), surface.get_height()

        # Dim overlay
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, Modals.DIM_ALPHA))
        surface.blit(overlay, (0, 0))

        # Dialog box
        dlg_w, dlg_h = Modals.DELETE_CONFIRM_W, Modals.DELETE_CONFIRM_H
        dlg_x = (sw - dlg_w) // 2
        dlg_y = (sh - dlg_h) // 2
        draw_chamfered_panel(surface, dlg_x, dlg_y, dlg_w, dlg_h, SC.BG_PANEL_LIGHT, SC.GOLD_PRIMARY, SC.GOLD_GLOW, 12)

        # Title
        title = scene.section_font.render(t("welcome.delete_confirm_title"), True, SC.DANGER_RED)
        surface.blit(title, title.get_rect(center=(sw // 2, dlg_y + Modals.TITLE_TOP_PAD)))

        self._render_dialog_lines(
            surface,
            [
                t("welcome.delete_confirm_line1", username=scene.delete_username),
                t("welcome.delete_confirm_line2"),
            ],
            sw // 2,
            dlg_y + 104,
            dlg_w - Modals.BODY_INSET_X,
        )

        # Buttons
        btn_w, btn_h = Modals.BUTTON_W, Modals.BUTTON_H
        gap = Modals.BUTTON_GAP
        total_btn_w = btn_w * 2 + gap
        btn_start_x = sw // 2 - total_btn_w // 2
        btn_y = dlg_y + dlg_h - Modals.BUTTON_BOTTOM_PAD

        # Confirm button (danger — red)
        confirm_rect = pygame.Rect(btn_start_x, btn_y, btn_w, btn_h)
        scene._login_panel._draw_button(
            surface,
            confirm_rect,
            t("welcome.delete_confirm_yes"),
            "delete_confirm_yes",
            SC.DANGER_RED,
            is_primary=True,
            is_focused=(scene.delete_confirm_focus == "yes"),
        )

        # Cancel button
        cancel_rect = pygame.Rect(btn_start_x + btn_w + gap, btn_y, btn_w, btn_h)
        scene._login_panel._draw_button(
            surface,
            cancel_rect,
            t("welcome.delete_confirm_no"),
            "delete_confirm_no",
            SC.GOLD_DIM,
            is_focused=(scene.delete_confirm_focus == "no"),
        )

    def _render_dialog_lines(self, surface, lines, center_x, start_y, max_width):
        scene = self._scene
        y = start_y
        for line in lines:
            for wrapped in wrap_text(line, scene.hint_font, max_width, max_lines=2):
                text = scene.hint_font.render(wrapped, True, SceneColors.TEXT_DIM)
                surface.blit(text, text.get_rect(center=(center_x, y)))
                y += 30
