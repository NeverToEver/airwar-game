"""Welcome scene -- single-page beginner interface combining login, difficulty, and quick tips.

The scene coordinates five panels extracted under ``airwar.scenes.welcome``:

* :mod:`.welcome.layout` -- shared layout constants
* :mod:`.welcome.login_panel` -- username/password inputs, user dropdown, login/register/delete
* :mod:`.welcome.difficulty_panel` -- difficulty radio, tutorial CTA, controls reference
* :mod:`.welcome.welcome_modals` -- guest-confirm and delete-confirm overlays
* :mod:`.welcome.leaderboard_overlay` -- leaderboard toggle and view mount

The scene keeps login, difficulty selection, tutorial access, settings, and
the leaderboard in one compact start surface.
"""

import logging

import pygame

from airwar.config.design_tokens import SceneColors, SceneLayout, get_design_tokens
from airwar.i18n import t
from airwar.leaderboard import LeaderboardService
from airwar.ui.chamfered_panel import draw_chamfered_panel
from airwar.ui.menu_background import MenuBackground
from airwar.ui.particles import ParticleSystem
from airwar.utils.database import UserDB
from airwar.utils.fonts import get_cjk_font
from airwar.utils.mouse_interaction import MouseInteractiveMixin
from airwar.utils.responsive import ResponsiveHelper
from airwar.window.window import get_window

from .scene import Scene
from .welcome import DifficultyPanel, LeaderboardOverlay, LoginPanel, WelcomeModals
from .welcome import layout as _layout

logger = logging.getLogger(__name__)


def _request(scene, kind: str) -> None:
    """Mark a navigation request on the scene and stop the welcome loop."""
    if kind == "tutorial":
        scene.tutorial_requested = True
    elif kind == "settings":
        scene.settings_requested = True
    elif kind == "quit":
        scene.want_to_quit = True
    scene.running = False


class WelcomeScene(Scene, MouseInteractiveMixin):
    """Single-page beginner interface combining login, difficulty, and quick tips.

    Layout (side-by-side):
        Left panel  -- Login/Register
        Right panel -- Difficulty selection + Quick Controls reference
        Start button at bottom center.

    Keyboard navigation:
        TAB -- cycle focus between username, password, difficulty
        Up/Down -- change difficulty when focused
        ENTER -- submit login / register / start
        ESC -- quit
    """

    # Layout constants shared by the panel renderers.
    PANEL_W, PANEL_H = _layout.PANEL_W, _layout.PANEL_H
    CHAMFER, INPUT_W, INPUT_H, BTN_H = _layout.CHAMFER, _layout.INPUT_W, _layout.INPUT_H, _layout.BTN_H
    LOGIN_PAD_X, LOGIN_LABEL_W, LOGIN_LABEL_GAP = _layout.LOGIN_PAD_X, _layout.LOGIN_LABEL_W, _layout.LOGIN_LABEL_GAP
    LOGIN_ROW_GAP, LOGIN_PRIMARY_GAP = _layout.LOGIN_ROW_GAP, _layout.LOGIN_PRIMARY_GAP
    LOGIN_PRIMARY_W = _layout.LOGIN_PRIMARY_W
    LOGIN_SECONDARY_W, LOGIN_SECONDARY_H = _layout.LOGIN_SECONDARY_W, _layout.LOGIN_SECONDARY_H
    USER_DROPDOWN_W = _layout.USER_DROPDOWN_W
    USER_DROPDOWN_OPTION_H, USER_DROPDOWN_MAX_ITEMS = _layout.USER_DROPDOWN_OPTION_H, _layout.USER_DROPDOWN_MAX_ITEMS
    DIFF_OPTION_H, DIFF_GAP = _layout.DIFF_OPTION_H, _layout.DIFF_GAP
    PANEL_GAP, STACKED_PANEL_GAP = _layout.PANEL_GAP, _layout.STACKED_PANEL_GAP
    MESSAGE_DISPLAY_FRAMES = _layout.MESSAGE_DISPLAY_FRAMES

    def __init__(self):
        Scene.__init__(self)
        MouseInteractiveMixin.__init__(self)
        self._is_error = False
        # Panels are wired in enter() so they always see the latest state.
        self._login_panel: LoginPanel | None = None
        self._difficulty_panel: DifficultyPanel | None = None
        self._modals: WelcomeModals | None = None
        self._leaderboard_overlay: LeaderboardOverlay | None = None

    def enter(self, **kwargs) -> None:
        """Initialize welcome-scene state when the scene becomes active.

        Resets the mouse hover/button registries, opens the user
        database, restores the last logged-in username, sets up fonts
        and background, and seeds the particle system. Accepts
        `**kwargs` to satisfy the `Scene` contract; no keyword
        arguments are interpreted.

        Args:
            **kwargs: Ignored scene-enter arguments.
        """
        self.clear_hover()
        self.clear_buttons()
        self.db = UserDB()
        self.leaderboard_service = LeaderboardService(self.db)
        self.running = True
        self.username = ""
        self.password = ""
        self.message = ""
        self._is_error = False
        self.message_timer = 0
        self.want_to_quit = False
        self.tutorial_requested = False
        self.settings_requested = False
        self.show_guest_confirm = False
        self.guest_confirm_focus = "yes"  # 'yes' | 'no'
        self.show_delete_confirm = False
        self.delete_confirm_focus = "no"  # 'yes' | 'no'
        self.delete_username = ""
        self.animation_time = 0
        self.cursor_visible = True
        self.cursor_timer = 0
        self.known_usernames = []
        self.show_user_dropdown = False
        self.show_leaderboard = False

        # Difficulty
        self.difficulty_options = ["easy", "medium", "hard"]
        self.difficulty_labels = {
            "easy": t("welcome.difficulty.easy"),
            "medium": t("welcome.difficulty.medium"),
            "hard": t("welcome.difficulty.hard"),
        }
        self.selected_difficulty = "medium"
        self.difficulty_index = 1

        # Focus: 'username' | 'password' | 'difficulty'
        self.focus = "username"

        # Mount panels now that state attrs exist.
        self._login_panel = LoginPanel(self)
        self._difficulty_panel = DifficultyPanel(self)
        self._modals = WelcomeModals(self)
        self._leaderboard_overlay = LeaderboardOverlay(self)

        self._load_known_usernames()

        self._tokens = get_design_tokens()
        self._background = MenuBackground()
        self._particles = ParticleSystem()
        self._particles.reset(self._tokens.components.PARTICLE_COUNT, "particle")

        pygame.font.init()
        tokens = self._tokens
        self.title_font = get_cjk_font(tokens.typography.TITLE_SIZE)
        self.section_font = get_cjk_font(tokens.typography.SUBHEADING_SIZE)
        self.input_font = get_cjk_font(tokens.typography.BODY_SIZE)
        self.button_font = get_cjk_font(tokens.typography.BODY_SIZE)
        self.hint_font = get_cjk_font(tokens.typography.HUD_SIZE)
        self.tip_font = get_cjk_font(tokens.typography.TINY_SIZE)

    def exit(self) -> None:
        pass

    # -- Internal helpers used by the panels ----------------------------

    def _tokens_typography_font(self, name: str):
        """Return a CJK font sized to the named typography token (e.g. ``SMALL_SIZE``)."""
        size = getattr(self._tokens.typography, name)
        return get_cjk_font(size)

    def _set_error_message(self, text: str) -> None:
        """Display ``text`` in the message line for ``MESSAGE_DISPLAY_FRAMES`` frames."""
        self.message = text
        self._is_error = True
        self.message_timer = self.MESSAGE_DISPLAY_FRAMES

    def _set_info_message(self, text: str) -> None:
        """Display ``text`` in green for ``MESSAGE_DISPLAY_FRAMES`` frames."""
        self.message = text
        self._is_error = False
        self.message_timer = self.MESSAGE_DISPLAY_FRAMES

    def cycle_focus(self) -> None:
        """Forward focus cycling to the difficulty panel helper."""
        if self._difficulty_panel is not None:
            self._difficulty_panel.cycle_focus()

    # -- Event handling -------------------------------------------------

    def handle_events(self, event: pygame.event.Event) -> None:
        """Dispatch a single pygame event to the appropriate handler.

        Routes keydown, mouse motion, and mouse button events to
        keyboard handling, mouse interaction, and the dropdown / modal
        click paths. Drops user-dropdown when the user clicks
        elsewhere.

        Args:
            event: The pygame event to process this frame.
        """
        if event.type == pygame.KEYDOWN:
            self._handle_keydown(event)
        elif event.type == pygame.MOUSEMOTION:
            self.handle_mouse_motion(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and self._login_panel.handle_user_dropdown_click(event.pos):
            return
        elif event.type == pygame.MOUSEBUTTONDOWN and self.show_delete_confirm:
            self._modals.handle_modal_mouse_click(event.pos, {"delete_confirm_yes", "delete_confirm_no"})
        elif event.type == pygame.MOUSEBUTTONDOWN and self.handle_mouse_click(event.pos):
            btn = self.get_hovered_button()
            if btn:
                self._handle_button_click(btn)
            # Clicking on input areas sets focus (only outside confirm mode)
            if not self.show_guest_confirm:
                if btn == "username_field":
                    self._login_panel.focus_username_field()
                elif btn == "password_field":
                    self._login_panel.focus_password_field()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self.show_user_dropdown = False

    def _handle_keydown(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_ESCAPE:
            if self.show_guest_confirm:
                self.show_guest_confirm = False
                return
            if self.show_user_dropdown:
                self.show_user_dropdown = False
                return
            self.want_to_quit = True
            self.running = False
            return

        # Delete user confirmation mode — navigate buttons, Enter to confirm
        if self.show_delete_confirm:
            if event.key == pygame.K_RETURN:
                if self.delete_confirm_focus == "yes":
                    self._do_delete_user()
                else:
                    self.show_delete_confirm = False
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB):
                self.delete_confirm_focus = "no" if self.delete_confirm_focus == "yes" else "yes"
            return

        # Guest confirmation mode — navigate buttons, Enter to confirm
        if self.show_guest_confirm:
            if event.key == pygame.K_RETURN:
                if self.guest_confirm_focus == "yes":
                    self.username = "Guest"
                    self.running = False
                else:
                    self.show_guest_confirm = False
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB):
                self.guest_confirm_focus = "no" if self.guest_confirm_focus == "yes" else "yes"
            return

        if event.key == pygame.K_TAB:
            self.show_user_dropdown = False
            self.cycle_focus()
            return

        # ENTER — login with credentials, or prompt guest confirmation
        if event.key == pygame.K_RETURN:
            if self.username and self.password:
                self._do_login()
            else:
                self.show_guest_confirm = True
                self.guest_confirm_focus = "yes"
                return

        if self.focus in ("username", "password"):
            self._login_panel.handle_input_key(event)
        elif self.focus == "difficulty":
            self._difficulty_panel.handle_difficulty_key(event)

    def _handle_button_click(self, button_name: str) -> None:
        lp = self._login_panel
        dp = self._difficulty_panel
        mod = self._modals
        lb = self._leaderboard_overlay
        window = get_window()
        scene = self
        handlers = {
            "login": lp.do_login,
            "register": lp.do_register,
            "skip_login": mod.start_guest_session,
            "fullscreen": window.toggle_fullscreen,
            "tutorial": lambda: _request(scene, "tutorial"),
            "settings": lambda: _request(scene, "settings"),
            "quit": lambda: _request(scene, "quit"),
            "username_field": lp.focus_username_field,
            "username_dropdown": lp.toggle_user_dropdown,
            "password_field": lp.focus_password_field,
            "diff_easy": lambda: dp.select_difficulty("easy"),
            "diff_medium": lambda: dp.select_difficulty("medium"),
            "diff_hard": lambda: dp.select_difficulty("hard"),
            "guest_confirm_yes": mod.start_guest_session,
            "guest_confirm_no": mod.dismiss_guest_confirm,
            "delete_user": lp.request_delete_user,
            "delete_confirm_yes": lp.do_delete_user,
            "delete_confirm_no": lp.dismiss_delete_confirm,
            "leaderboard": lb.open,
            "leaderboard_close": lb.close,
        }
        handler = handlers.get(button_name)
        if handler:
            handler()
        elif button_name.startswith("known_user_"):
            index_text = button_name.rsplit("_", 1)[-1]
            if index_text.isdigit():
                lp.select_known_user(int(index_text))

    # -- Internal click handlers --

    def _do_delete_user(self) -> None:
        self._login_panel.do_delete_user()

    def _do_login(self) -> None:
        self._login_panel.do_login()

    def _load_known_usernames(self) -> None:
        self._login_panel.load_known_usernames()

    def _select_known_user(self, index: int) -> None:
        self._login_panel.select_known_user(index)

    # -- Update ---------------------------------------------------------

    def update(self, *args, **kwargs) -> None:
        """Advance welcome-scene animations and timers by one frame.

        Updates the global animation clock, ticks the message-display
        timer (clearing expired messages), blinks the text-input cursor
        at 30-frame intervals, and forwards updates to the background
        and particle systems so they animate consistently with the HUD.

        Args:
            *args: Ignored (uniform signature with other scenes).
            **kwargs: Ignored (uniform signature with other scenes).
        """
        self.animation_time += 1
        if self.message_timer > 0:
            self.message_timer -= 1
            if self.message_timer == 0:
                self.message = ""
                self._is_error = False
        self.cursor_timer += 1
        if self.cursor_timer >= 30:
            self.cursor_timer = 0
            self.cursor_visible = not self.cursor_visible
        self._background._animation_time = self.animation_time
        self._background.update()
        self._particles._animation_time = self.animation_time
        self._particles.update(direction=-1)

    # -- Render ---------------------------------------------------------

    def render(self, surface: pygame.Surface) -> None:
        """Render the welcome scene to the given surface for this frame.

        Draws the animated background and particles, the title, the
        login and difficulty panels, the bottom hint, the message line
        (if any), the fullscreen button, and finally the leaderboard,
        guest-confirm, and delete-confirm overlays (topmost).

        Args:
            surface: Target pygame surface, typically the game window.
        """
        SC = SceneColors
        sw, sh = surface.get_width(), surface.get_height()

        # Background
        self._background.render_themed_style(
            surface,
            {
                "bg": SC.BG_PRIMARY,
                "bg_gradient": SC.BG_PANEL,
            },
        )
        self._particles.render(surface, "particle")

        # Title
        self._render_title(surface)

        # Compute layout
        layout = self._get_layout(sw, sh)

        # Left panel: Login
        self._login_panel.render(surface, layout["left_x"], layout["left_y"], panel_h=layout["panel_h"])

        # Right panel: Difficulty + Quick Tips
        self._difficulty_panel.render(surface, layout["right_x"], layout["right_y"], panel_h=layout["panel_h"])

        # Bottom hint
        self._render_bottom_hint(surface, sw, sh)

        # Message
        if self.message:
            self._render_message(surface, sw, sh)

        # Fullscreen button
        self._render_fullscreen_button(surface, sw, sh)

        # Leaderboard overlay (topmost non-modal layer)
        if self.show_leaderboard:
            self._leaderboard_overlay.render(surface, sw, sh)

        # Guest confirmation overlay (topmost)
        if self.show_guest_confirm:
            self._modals.render_guest_confirm(surface)

        # Delete user confirmation overlay (topmost)
        if self.show_delete_confirm:
            self._modals.render_delete_confirm(surface)

    def _get_layout(self, sw: int, sh: int) -> dict:
        """Compute panel positions and the responsive ``panel_h`` for the
        current viewport.

        The returned ``panel_h`` is the actual height both panels will
        render at. At the design size (1920x1080) it equals
        :data:`PANEL_H`; at smaller viewports it shrinks so both panels
        stay within the screen bounds so the leaderboard remains reachable.
        """
        title_clearance = 110
        bottom_clearance = 96
        panel_gap = min(self.PANEL_GAP, 24)
        stacked_gap = self.STACKED_PANEL_GAP

        min_side_margin = 8
        side_by_side_gap = min(panel_gap, max(8, sw - self.PANEL_W * 2 - min_side_margin * 2))
        if sw >= self.PANEL_W * 2 + min_side_margin * 2 + 8:
            # Side-by-side: cap panel_h at available vertical space.
            start_x = (sw - (self.PANEL_W * 2 + side_by_side_gap)) // 2
            available_h = max(0, sh - title_clearance - bottom_clearance)
            panel_h = min(self.PANEL_H, available_h)
            panel_y = max(title_clearance, (sh - panel_h) // 2 - 20)
            return {
                "left_x": start_x,
                "left_y": panel_y,
                "right_x": start_x + self.PANEL_W + side_by_side_gap,
                "right_y": panel_y,
                "panel_h": panel_h,
            }

        # Stacked: split available height between the two panels.
        available_h = max(0, sh - 2 * title_clearance - bottom_clearance - stacked_gap)
        panel_h = min(self.PANEL_H, available_h // 2)
        panel_x = max(20, (sw - self.PANEL_W) // 2)
        panel_y = title_clearance
        return {
            "left_x": panel_x,
            "left_y": panel_y,
            "right_x": panel_x,
            "right_y": panel_y + panel_h + stacked_gap,
            "panel_h": panel_h,
        }

    def _render_title(self, surface):
        import math

        SC = SceneColors
        sw, sh = surface.get_width(), surface.get_height()
        title_size = min(self._tokens.typography.TITLE_SIZE, max(72, sh // 10))
        title_font = get_cjk_font(title_size)
        ty = max(62, int(title_size * 0.72)) + math.sin(self.animation_time * 0.04) * 3

        for blur, alpha, color in [(4, 18, SC.GOLD_DIM), (2, 30, SC.GOLD_PRIMARY)]:
            glow = title_font.render(t("welcome.title"), True, color)
            glow.set_alpha(alpha)
            for ox in range(-blur, blur + 1, 2):
                for oy in range(-blur, blur + 1, 2):
                    if ox * ox + oy * oy <= blur * blur:
                        r = glow.get_rect(center=(sw // 2 + ox, int(ty) + oy))
                        surface.blit(glow, r)
        title = title_font.render(t("welcome.title"), True, SC.GOLD_PRIMARY)
        surface.blit(title, title.get_rect(center=(sw // 2, int(ty))))

    def _render_bottom_hint(self, surface, sw, sh):
        SC = SceneColors
        blink = (self.animation_time // 30) % 2 == 0
        color = SC.TEXT_DIM if blink else SC.TEXT_PRIMARY
        hints = t("welcome.hint.guest_confirm") if self.show_guest_confirm else t("welcome.hint.default")
        hint_surf = self.hint_font.render(hints, True, color)
        surface.blit(hint_surf, hint_surf.get_rect(center=(sw // 2, sh - SceneLayout.WELCOME_BOTTOM_HINT_OFFSET)))

    def _render_message(self, surface, sw, sh):
        SC = SceneColors
        color = SC.DANGER_RED if self._is_error else SC.FOREST_GREEN
        msg_surf = self.input_font.render(self.message, True, color)
        surface.blit(msg_surf, msg_surf.get_rect(center=(sw // 2, sh - SceneLayout.WELCOME_BOTTOM_HINT_OFFSET_ALT)))

    def _render_fullscreen_button(self, surface, sw, sh):
        SC = SceneColors
        window = get_window()
        fs_text = t("welcome.fullscreen_exit") if window.is_fullscreen() else t("welcome.fullscreen_enter")
        scale = ResponsiveHelper.get_scale_factor(sw, sh)
        btn_w = ResponsiveHelper.scale(160, scale)
        btn_h = ResponsiveHelper.scale(38, scale)
        rect = pygame.Rect(
            sw - btn_w - SceneLayout.FULLSCREEN_BTN_INSET,
            sh - btn_h - SceneLayout.FULLSCREEN_BTN_INSET,
            btn_w,
            btn_h,
        )

        self.register_button("fullscreen", rect)
        hover = self.is_button_hovered("fullscreen")
        draw_chamfered_panel(
            surface,
            rect.x,
            rect.y,
            rect.width,
            rect.height,
            SC.BG_PANEL_LIGHT if hover else SC.BG_PANEL,
            SC.GOLD_PRIMARY if hover else SC.BORDER_DIM,
            None,
            6,
        )
        fs_surf = self.tip_font.render(fs_text, True, SC.TEXT_PRIMARY if hover else SC.TEXT_DIM)
        surface.blit(fs_surf, fs_surf.get_rect(center=rect.center))

    # -- Public interface (used by SceneDirector) -----------------------

    def get_username(self) -> str:
        """Return the entered username, falling back to "Guest".

        Returns:
            str: The username the player typed, or the literal "Guest"
            when the input is empty.
        """
        return self.username if self.username else "Guest"

    def get_difficulty(self) -> str:
        """Return the currently selected difficulty level.

        Returns:
            str: One of "easy", "medium", or "hard".
        """
        return self.selected_difficulty

    def is_running(self) -> bool:
        """Return whether the scene is still accepting input.

        Returns:
            bool: True while the scene has not produced a result yet
            (login not submitted, no navigation requested).
        """
        return self.running

    def is_ready(self) -> bool:
        """Return whether the scene is ready to advance to gameplay.

        The scene is ready when the player has finished entering
        credentials and has not requested a side flow (tutorial,
        settings) or a quit.

        Returns:
            bool: True if the scene should hand off to the next scene.
        """
        return not self.running and not self.tutorial_requested and not self.want_to_quit

    def should_quit(self) -> bool:
        """Return whether the user requested to quit from this scene.

        Returns:
            bool: True if the quit button (or ESC) was triggered.
        """
        return self.want_to_quit

    def should_open_tutorial(self) -> bool:
        """Return whether the user requested the tutorial scene.

        Returns:
            bool: True if the tutorial button (or "新手教程" CTA) was
            triggered.
        """
        return self.tutorial_requested

    def should_open_settings(self) -> bool:
        """Return whether the user requested the settings scene.

        Returns:
            bool: True if the settings button was triggered.
        """
        return self.settings_requested

    # -- Panel forwarders ------------------------------------------------

    def _get_login_layout(self, px: int, py: int) -> dict:
        return self._login_panel.get_login_layout(px, py)

    def _handle_user_dropdown_click(self, pos: tuple[int, int]) -> bool:
        return self._login_panel.handle_user_dropdown_click(pos)

    def _cycle_focus(self) -> None:
        self.cycle_focus()

    def _handle_input_key(self, event: pygame.event.Event) -> None:
        self._login_panel.handle_input_key(event)

    def _handle_difficulty_key(self, event: pygame.event.Event) -> None:
        self._difficulty_panel.handle_difficulty_key(event)

    def _handle_modal_mouse_click(self, pos: tuple[int, int], allowed_buttons: set[str]) -> None:
        self._modals.handle_modal_mouse_click(pos, allowed_buttons)
