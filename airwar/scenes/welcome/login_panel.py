"""Login panel: username/password inputs, dropdown, login/register/delete logic.

Holds the login form state mutations and rendering helpers shared with the
welcome scene's other panels. The host WelcomeScene passes itself in so
this panel can register hover rects, render buttons, and mutate
scene-level state (focus, username, password, etc.).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import pygame

from airwar.config.design_tokens import SceneColors
from airwar.i18n import t
from airwar.ui.chamfered_panel import draw_chamfered_panel
from airwar.ui.scene_rendering_utils import fit_text_to_width
from airwar.utils.database import DatabaseError

from .layout import (
    BTN_H,
    CHAMFER,
    INPUT_H,
    INPUT_W,
    LOGIN_LABEL_GAP,
    LOGIN_LABEL_W,
    LOGIN_PAD_X,
    LOGIN_PRIMARY_GAP,
    LOGIN_PRIMARY_W,
    LOGIN_ROW_GAP,
    LOGIN_SECONDARY_H,
    LOGIN_SECONDARY_W,
    PANEL_H,
    PANEL_W,
    USER_DROPDOWN_MAX_ITEMS,
    USER_DROPDOWN_OPTION_H,
    USER_DROPDOWN_W,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class LoginPanel:
    """Login form panel: inputs, user dropdown, and credential CRUD.

    Attributes are read from the host scene each frame so panel rendering
    reflects the latest username/password/focus changes immediately.
    """

    def __init__(self, scene: Any) -> None:
        self._scene = scene

    # -- Layout ---------------------------------------------------------

    def get_login_layout(self, px: int, py: int) -> dict:
        """Compute the login panel layout given a top-left origin.

        Returns a dict of named pygame.Rect values keyed by element name.
        Used by both the rendering code and unit tests asserting that
        labels stay outside their input fields.
        """
        content_x = px + LOGIN_PAD_X
        content_w = PANEL_W - LOGIN_PAD_X * 2
        field_x = content_x + LOGIN_LABEL_W + LOGIN_LABEL_GAP
        field_w = content_w - LOGIN_LABEL_W - LOGIN_LABEL_GAP
        username_dropdown_gap = 8
        username_field_w = field_w - USER_DROPDOWN_W - username_dropdown_gap

        user_y = py + 106
        pass_y = user_y + INPUT_H + LOGIN_ROW_GAP
        primary_y = pass_y + INPUT_H + 38

        settings_y = primary_y + BTN_H + 16
        secondary_y = settings_y + LOGIN_SECONDARY_H + 14

        primary_total_w = LOGIN_PRIMARY_W * 2 + LOGIN_PRIMARY_GAP
        primary_x = px + (PANEL_W - primary_total_w) // 2
        secondary_total_w = LOGIN_SECONDARY_W * 2 + LOGIN_PRIMARY_GAP
        secondary_x = px + (PANEL_W - secondary_total_w) // 2

        return {
            "title_center": (px + PANEL_W // 2, py + 38),
            "username_label": pygame.Rect(content_x, user_y, LOGIN_LABEL_W, INPUT_H),
            "username_field": pygame.Rect(field_x, user_y, username_field_w, INPUT_H),
            "username_dropdown": pygame.Rect(
                field_x + username_field_w + username_dropdown_gap,
                user_y,
                USER_DROPDOWN_W,
                INPUT_H,
            ),
            "password_label": pygame.Rect(content_x, pass_y, LOGIN_LABEL_W, INPUT_H),
            "password_field": pygame.Rect(field_x, pass_y, field_w, INPUT_H),
            "login": pygame.Rect(primary_x, primary_y, LOGIN_PRIMARY_W, BTN_H),
            "register": pygame.Rect(
                primary_x + LOGIN_PRIMARY_W + LOGIN_PRIMARY_GAP,
                primary_y,
                LOGIN_PRIMARY_W,
                BTN_H,
            ),
            "settings": pygame.Rect(
                px + (PANEL_W - LOGIN_SECONDARY_W) // 2,
                settings_y,
                LOGIN_SECONDARY_W,
                LOGIN_SECONDARY_H,
            ),
            "guest": pygame.Rect(secondary_x, secondary_y, LOGIN_SECONDARY_W, LOGIN_SECONDARY_H),
            "delete": pygame.Rect(
                secondary_x + LOGIN_SECONDARY_W + LOGIN_PRIMARY_GAP,
                secondary_y,
                LOGIN_SECONDARY_W,
                LOGIN_SECONDARY_H,
            ),
        }

    # -- Rendering ------------------------------------------------------

    def render(self, surface: pygame.Surface, px: int, py: int, panel_h: int | None = None) -> None:
        """Render the login panel at the given top-left pixel coordinates.

        ``panel_h`` overrides the natural :data:`PANEL_H` for the panel
        background only; internal element positions continue to use the
        constant for stability. Falls back to :data:`PANEL_H` when not
        provided (e.g. by tests that render the panel in isolation).
        """
        SC = SceneColors
        layout = self.get_login_layout(px, py)
        scene = self._scene
        actual_h = panel_h if panel_h is not None else PANEL_H

        # Panel background
        draw_chamfered_panel(
            surface, px, py, PANEL_W, actual_h,
            SC.BG_PANEL_LIGHT, SC.BORDER_DIM, SC.GOLD_GLOW, CHAMFER,
        )

        # Section title
        title = scene.section_font.render(t("welcome.login_title"), True, SC.GOLD_PRIMARY)
        surface.blit(title, title.get_rect(center=layout["title_center"]))

        # Decorative separator
        sep_y = py + 72
        pygame.draw.line(surface, SC.BORDER_DIM, (px + 30, sep_y), (px + PANEL_W - 30, sep_y), 1)

        self._draw_input_row(
            surface,
            layout["username_label"],
            layout["username_field"],
            t("welcome.username_label"),
            scene.username,
            scene.focus == "username",
            "username_field",
        )
        self._draw_username_dropdown_button(surface, layout["username_dropdown"])
        self._draw_input_row(
            surface,
            layout["password_label"],
            layout["password_field"],
            t("welcome.password_label"),
            scene.password,
            scene.focus == "password",
            "password_field",
            is_password=True,
        )

        self._draw_button(
            surface,
            layout["login"],
            t("welcome.login_button"),
            "login",
            SceneColors.FOREST_GREEN,
            is_primary=True,
        )
        self._draw_button(surface, layout["register"], t("welcome.register_button"), "register", SceneColors.GOLD_DIM)

        self._draw_ghost_button(surface, layout["guest"], t("welcome.guest_button"), "skip_login")

        # Settings button
        settings_rect = layout["settings"]
        scene.register_button("settings", settings_rect)
        settings_hover = scene.is_button_hovered("settings")
        settings_fill = (20, 32, 42) if settings_hover else SC.BG_PANEL_LIGHT
        settings_border = (82, 180, 200) if settings_hover else SC.BORDER_DIM
        draw_chamfered_panel(
            surface,
            settings_rect.x,
            settings_rect.y,
            settings_rect.width,
            settings_rect.height,
            settings_fill,
            settings_border,
            None,
            6,
        )
        settings_color = (160, 220, 240) if settings_hover else SC.TEXT_DIM
        settings_font = scene._tokens_typography_font("SMALL_SIZE")
        settings_text = settings_font.render(t("welcome.settings_button"), True, settings_color)
        surface.blit(settings_text, settings_text.get_rect(center=settings_rect.center))

        delete_rect = layout["delete"]
        scene.register_button("delete_user", delete_rect)
        delete_hover = scene.is_button_hovered("delete_user")
        delete_fill = (80, 20, 20) if delete_hover else SC.BG_PANEL_LIGHT
        delete_border = (200, 60, 60) if delete_hover else SC.BORDER_DIM
        draw_chamfered_panel(
            surface,
            delete_rect.x,
            delete_rect.y,
            delete_rect.width,
            delete_rect.height,
            delete_fill,
            delete_border,
            None,
            6,
        )
        delete_color = (255, 100, 100) if delete_hover else SC.TEXT_DIM
        delete_font = scene._tokens_typography_font("SMALL_SIZE")
        delete_text = delete_font.render(t("welcome.delete_button"), True, delete_color)
        surface.blit(delete_text, delete_text.get_rect(center=delete_rect.center))
        self._render_user_dropdown(surface, layout["username_dropdown"])

    # -- Drawing helpers (shared with modals and other panels) ---------

    def _draw_input_row(self, surface, label_rect, input_rect, label, text, is_active, button_name, is_password=False):
        SC = SceneColors
        scene = self._scene
        label_color = SC.GOLD_PRIMARY if is_active else SC.TEXT_DIM
        label_surf = fit_text_to_width(scene.hint_font, label, label_color, label_rect.width)
        surface.blit(label_surf, label_surf.get_rect(midleft=(label_rect.x, label_rect.centery)))

        scene.register_button(button_name, input_rect)
        self._draw_input(surface, input_rect, text, is_active, is_password=is_password)

    def _draw_username_dropdown_button(self, surface, rect: pygame.Rect) -> None:
        SC = SceneColors
        scene = self._scene
        scene.register_button("username_dropdown", rect)
        hover = scene.is_button_hovered("username_dropdown")
        active = scene.show_user_dropdown or hover
        border = SC.GOLD_PRIMARY if active else SC.BORDER_DIM
        fill = SC.BG_PANEL if active else SC.BG_PANEL_LIGHT
        if active:
            draw_chamfered_panel(
                surface,
                rect.x - 3,
                rect.y - 3,
                rect.width + 6,
                rect.height + 6,
                SC.BG_PANEL,
                SC.GOLD_GLOW,
                SC.GOLD_GLOW,
                8,
            )
        draw_chamfered_panel(surface, rect.x, rect.y, rect.width, rect.height, fill, border, None, 6)

        arrow = "▲" if scene.show_user_dropdown else "▼"
        color = SC.GOLD_PRIMARY if active else SC.TEXT_DIM
        arrow_surf = scene.hint_font.render(arrow, True, color)
        surface.blit(arrow_surf, arrow_surf.get_rect(center=rect.center))

    def _render_user_dropdown(self, surface, anchor_rect: pygame.Rect) -> None:
        scene = self._scene
        for index in range(USER_DROPDOWN_MAX_ITEMS):
            scene.unregister_button(f"known_user_{index}")
        if not scene.show_user_dropdown or not scene.known_usernames:
            return

        SC = SceneColors
        visible_users = scene.known_usernames[:USER_DROPDOWN_MAX_ITEMS]
        option_w = min(INPUT_W, anchor_rect.right - (anchor_rect.x - INPUT_W + USER_DROPDOWN_W))
        option_w = max(option_w, anchor_rect.width)
        menu_x = anchor_rect.right - option_w
        menu_y = anchor_rect.bottom + 6
        menu_h = len(visible_users) * USER_DROPDOWN_OPTION_H
        draw_chamfered_panel(surface, menu_x, menu_y, option_w, menu_h, SC.BG_PANEL, SC.GOLD_PRIMARY, SC.GOLD_GLOW, 8)

        for index, username in enumerate(visible_users):
            btn_name = f"known_user_{index}"
            item_rect = pygame.Rect(
                menu_x + 4,
                menu_y + 4 + index * USER_DROPDOWN_OPTION_H,
                option_w - 8,
                USER_DROPDOWN_OPTION_H - 4,
            )
            scene.register_button(btn_name, item_rect)
            hover = scene.is_button_hovered(btn_name)
            fill = SC.BG_PANEL_LIGHT if hover or username == scene.username else SC.BG_PANEL
            border = SC.GOLD_PRIMARY if hover else SC.BORDER_DIM
            draw_chamfered_panel(
                surface, item_rect.x, item_rect.y, item_rect.width, item_rect.height, fill, border, None, 5
            )
            color = SC.GOLD_PRIMARY if username == scene.username else SC.TEXT_PRIMARY
            label = fit_text_to_width(scene.tip_font, username, color, item_rect.width - 24)
            surface.blit(label, label.get_rect(midleft=(item_rect.x + 12, item_rect.centery)))

    def _draw_input(self, surface, rect, text, is_active, is_password=False):
        SC = SceneColors
        scene = self._scene

        border_color = SC.GOLD_PRIMARY if is_active else SC.BORDER_DIM
        bg_color = SC.BG_PANEL if is_active else SC.BG_PANEL_LIGHT

        if is_active:
            draw_chamfered_panel(
                surface,
                rect.x - 3,
                rect.y - 3,
                rect.width + 6,
                rect.height + 6,
                SC.BG_PANEL,
                SC.GOLD_GLOW,
                SC.GOLD_GLOW,
                8,
            )
        draw_chamfered_panel(surface, rect.x, rect.y, rect.width, rect.height, bg_color, border_color, None, 6)

        # Text content
        display = text
        if is_password and display:
            display = "*" * len(display)
        text_surf = scene.input_font.render(display, True, SC.TEXT_PRIMARY)
        text_rect = text_surf.get_rect(midleft=(rect.x + 16, rect.centery))
        # Clamp CJK text overflow: shift left so text stays within input box
        max_right = rect.right - 6
        if text_rect.right > max_right:
            text_rect.right = max_right
        surface.blit(text_surf, text_rect)

        # Placeholder
        if not text:
            ph = t("welcome.username_placeholder") if not is_password else t("welcome.password_placeholder")
            ph_surf = scene.input_font.render(ph, True, SC.TEXT_DIM)
            ph_rect = ph_surf.get_rect(midleft=(rect.x + 16, rect.centery))
            surface.blit(ph_surf, ph_rect)

        # Cursor
        if is_active and scene.cursor_visible:
            cx = text_rect.right + 3 if text else rect.x + 16
            pygame.draw.line(surface, SC.GOLD_PRIMARY, (cx, rect.y + 12), (cx, rect.y + rect.height - 12), 2)

    def _draw_button(self, surface, rect, text, button_name, color, is_primary=False, is_focused=False):
        """Render a primary/secondary panel button with chamfered styling."""
        SC = SceneColors
        scene = self._scene
        scene.register_button(button_name, rect)
        hover = scene.is_button_hovered(button_name)
        active = hover or is_focused

        btn_color = tuple(min(c + 30, 255) for c in color) if active else color

        if (is_primary and hover) or (is_focused and not hover):
            draw_chamfered_panel(
                surface,
                rect.x - 4,
                rect.y - 4,
                rect.width + 8,
                rect.height + 8,
                SC.BG_PANEL,
                SC.GOLD_GLOW,
                SC.GOLD_GLOW,
                8,
            )

        draw_chamfered_panel(
            surface,
            rect.x,
            rect.y,
            rect.width,
            rect.height,
            btn_color,
            SC.GOLD_PRIMARY if active else SC.BORDER_DIM,
            None,
            6,
        )

        text_color = SC.TEXT_BRIGHT if active else SC.TEXT_PRIMARY
        text_surf = fit_text_to_width(scene.button_font, text, text_color, rect.width - 32)
        surface.blit(text_surf, text_surf.get_rect(center=rect.center))

    def _draw_ghost_button(self, surface, rect, text, button_name):
        """Ghost-style button — blends into panel, border highlights on hover."""
        SC = SceneColors
        scene = self._scene
        scene.register_button(button_name, rect)
        hover = scene.is_button_hovered(button_name)

        fill = SC.BG_PANEL if hover else SC.BG_PANEL_LIGHT
        border = SC.GOLD_PRIMARY if hover else SC.BORDER_DIM
        draw_chamfered_panel(surface, rect.x, rect.y, rect.width, rect.height, fill, border, None, 6)

        text_color = SC.TEXT_PRIMARY if hover else SC.TEXT_DIM
        font = scene._tokens_typography_font("SMALL_SIZE")
        text_surf = fit_text_to_width(font, text, text_color, rect.width - 28)
        surface.blit(text_surf, text_surf.get_rect(center=rect.center))

    # -- Input handling -------------------------------------------------

    def handle_user_dropdown_click(self, pos: tuple[int, int]) -> bool:
        """If the dropdown is open, dispatch a click on a known user.

        Returns True when a known-user entry consumed the click (caller
        should stop further event processing), False otherwise.
        """
        scene = self._scene
        if not scene.show_user_dropdown:
            return False
        for index in range(min(len(scene.known_usernames), USER_DROPDOWN_MAX_ITEMS)):
            rect = scene.get_button_rect(f"known_user_{index}")
            if rect and rect.collidepoint(pos):
                self.select_known_user(index)
                return True
        return False

    def handle_input_key(self, event: pygame.event.Event) -> None:
        """Apply a key event to the focused username/password input."""
        scene = self._scene
        if event.key == pygame.K_BACKSPACE:
            if scene.focus == "username":
                scene.username = scene.username[:-1]
                scene.show_user_dropdown = bool(scene.known_usernames)
            else:
                scene.password = scene.password[:-1]
        elif event.key == pygame.K_UP or event.key == pygame.K_DOWN:
            scene.cycle_focus()
            scene.show_user_dropdown = False
        else:
            # Defensive: synthetic KEYDOWN events (smoke tests, automation)
            # may omit the `unicode` field, so use getattr() to fall back to
            # an empty string instead of crashing on AttributeError.
            unicode = getattr(event, "unicode", "") or ""
            # Filter control characters so Enter/Tab don't become input
            if not unicode or unicode in ("\r", "\n", "\t", "\x08"):
                return
            if scene.focus == "username" and len(scene.username) < 16:
                scene.username += unicode
                scene.show_user_dropdown = bool(scene.known_usernames)
            elif scene.focus == "password" and len(scene.password) < 16:
                scene.password += unicode

    def focus_username_field(self) -> None:
        scene = self._scene
        scene.focus = "username"
        scene.show_user_dropdown = bool(scene.known_usernames)

    def toggle_user_dropdown(self) -> None:
        scene = self._scene
        scene.focus = "username"
        scene.show_user_dropdown = bool(scene.known_usernames) and not scene.show_user_dropdown

    def focus_password_field(self) -> None:
        scene = self._scene
        scene.focus = "password"
        scene.show_user_dropdown = False

    def select_known_user(self, index: int) -> None:
        scene = self._scene
        if index < 0 or index >= len(scene.known_usernames):
            return
        scene.username = scene.known_usernames[index]
        scene.password = ""
        scene.focus = "password"
        scene.show_user_dropdown = False

    # -- Database operations -------------------------------------------

    def load_known_usernames(self) -> None:
        """Refresh ``known_usernames`` from the database; auto-restore last user."""
        scene = self._scene
        try:
            scene.known_usernames = scene.db.list_usernames()
            last_user = scene.db.get_last_login_user()
        except DatabaseError:
            logger.warning("Failed to load known user names", exc_info=True)
            scene.known_usernames = []
            last_user = None
        if last_user:
            scene.username = last_user
            scene.password = ""
            scene.focus = "password"

    def do_login(self) -> None:
        scene = self._scene
        if not scene.username or not scene.password:
            scene._set_error_message(t("welcome.error.empty_credentials"))
            return
        try:
            verified = scene.db.verify_user(scene.username, scene.password)
        except DatabaseError:
            logger.warning("Failed to verify user credentials", exc_info=True)
            scene._set_error_message(t("welcome.error.db_read_failed"))
            return
        if verified:
            try:
                scene.db.record_login(scene.username)
            except DatabaseError:
                logger.warning("Failed to record user login", exc_info=True)
                scene._set_error_message(t("welcome.error.delete_db_failed"))
                return
            scene.message = ""
            scene._is_error = False
            scene.running = False
        else:
            scene._set_error_message(t("welcome.error.wrong_credentials"))

    def do_register(self) -> None:
        scene = self._scene
        if not scene.username or not scene.password:
            scene._set_error_message(t("welcome.error.empty_credentials"))
            return
        if len(scene.username) < 3:
            scene._set_error_message(t("welcome.error.short_username"))
            return
        if len(scene.password) < 3:
            scene._set_error_message(t("welcome.error.short_password"))
            return
        try:
            created = scene.db.create_user(scene.username, scene.password)
        except DatabaseError:
            logger.warning("Failed to create user account", exc_info=True)
            scene._set_error_message(t("welcome.error.delete_db_failed"))
            return
        if created:
            scene._set_info_message(t("welcome.info.register_success"))
            scene.password = ""
            self.load_known_usernames()
        else:
            scene._set_error_message(t("welcome.error.username_exists"))

    def request_delete_user(self) -> None:
        scene = self._scene
        if scene.username:
            scene.delete_username = scene.username
            scene.show_delete_confirm = True
            scene.delete_confirm_focus = "no"
        else:
            scene._set_error_message(t("welcome.error.delete_user_missing"))

    def do_delete_user(self) -> None:
        scene = self._scene
        if not scene.delete_username:
            scene._set_error_message(t("welcome.error.delete_user_missing"))
            scene.show_delete_confirm = False
            return
        if not scene.password:
            scene._set_error_message(t("welcome.error.delete_requires_password"))
            scene.show_delete_confirm = False
            scene.focus = "password"
            return
        try:
            deleted = scene.db.delete_user(scene.delete_username, scene.password)
        except DatabaseError:
            logger.warning("Failed to delete user account data", exc_info=True)
            scene._set_error_message(t("welcome.error.delete_db_failed"))
            scene.show_delete_confirm = False
            return
        if deleted:
            scene._set_info_message(t("welcome.info.delete_success", username=scene.delete_username))
            scene.username = ""
            scene.password = ""
            self.load_known_usernames()
        else:
            scene._set_error_message(t("welcome.error.delete_failed"))
        scene.show_delete_confirm = False

    def dismiss_delete_confirm(self) -> None:
        self._scene.show_delete_confirm = False
