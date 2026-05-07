"""Welcome scene -- single-page beginner interface combining login, difficulty, and quick tips."""
import logging
import math

import pygame
from airwar.utils.fonts import get_cjk_font
from .scene import Scene
from airwar.utils.database import DatabaseError, UserDB
from airwar.utils.responsive import ResponsiveHelper
from airwar.ui.menu_background import MenuBackground
from airwar.ui.particles import ParticleSystem
from airwar.ui.chamfered_panel import draw_chamfered_panel
from airwar.ui.scene_rendering_utils import fit_text_to_width, wrap_text
from airwar.config.design_tokens import get_design_tokens, SceneColors
from airwar.window.window import get_window
from airwar.utils.mouse_interaction import MouseInteractiveMixin


logger = logging.getLogger(__name__)


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

    # Layout constants
    PANEL_W = 480
    PANEL_H = 500
    CHAMFER = 12
    INPUT_W = 370
    INPUT_H = 54
    BTN_W = 180
    BTN_H = 48
    LOGIN_PAD_X = 36
    LOGIN_LABEL_W = 104
    LOGIN_LABEL_GAP = 16
    LOGIN_ROW_GAP = 24
    LOGIN_PRIMARY_GAP = 16
    LOGIN_PRIMARY_W = 172
    LOGIN_SECONDARY_W = 172
    LOGIN_SECONDARY_H = 42
    USER_DROPDOWN_W = 46
    USER_DROPDOWN_OPTION_H = 38
    USER_DROPDOWN_MAX_ITEMS = 4
    DIFF_OPTION_H = 48
    DIFF_GAP = 8
    PANEL_GAP = 30
    STACKED_PANEL_GAP = 24

    def __init__(self):
        Scene.__init__(self)
        MouseInteractiveMixin.__init__(self)
        self._is_error = False

    def enter(self, **kwargs) -> None:
        self.clear_hover()
        self.clear_buttons()
        self.db = UserDB()
        self.running = True
        self.mode = 'login'
        self.username = ""
        self.password = ""
        self.message = ""
        self._is_error = False
        self.message_timer = 0
        self.want_to_quit = False
        self.tutorial_requested = False
        self.settings_requested = False
        self.show_guest_confirm = False
        self.guest_confirm_focus = 'yes'  # 'yes' | 'no'
        self.show_delete_confirm = False
        self.delete_confirm_focus = 'no'  # 'yes' | 'no'
        self.delete_username = ""
        self.animation_time = 0
        self.cursor_visible = True
        self.cursor_timer = 0
        self.known_usernames = []
        self.show_user_dropdown = False

        # Difficulty
        self.difficulty_options = ['easy', 'medium', 'hard']
        self.difficulty_labels = {'easy': '简单', 'medium': '中等', 'hard': '困难'}
        self.selected_difficulty = 'medium'
        self.difficulty_index = 1

        # Focus: 'username' | 'password' | 'difficulty'
        self.focus = 'username'
        self._load_known_usernames()

        self._tokens = get_design_tokens()
        self._background = MenuBackground()
        self._particles = ParticleSystem()
        self._particles.reset(self._tokens.components.PARTICLE_COUNT, 'particle')

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

    # -- Event handling -------------------------------------------------

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            self._handle_keydown(event)
        elif event.type == pygame.MOUSEMOTION:
            self.handle_mouse_motion(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and self._handle_user_dropdown_click(event.pos):
            return
        elif event.type == pygame.MOUSEBUTTONDOWN and self.show_delete_confirm:
            self._handle_modal_mouse_click(event.pos, {'delete_confirm_yes', 'delete_confirm_no'})
        elif event.type == pygame.MOUSEBUTTONDOWN and self.handle_mouse_click(event.pos):
            btn = self.get_hovered_button()
            if btn:
                self._handle_button_click(btn)
            # Clicking on input areas sets focus (only outside confirm mode)
            if not self.show_guest_confirm:
                if btn == 'username_field':
                    self.focus = 'username'
                elif btn == 'password_field':
                    self.focus = 'password'
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self.show_user_dropdown = False

    def _handle_modal_mouse_click(self, pos: tuple[int, int], allowed_buttons: set[str]) -> None:
        for name in allowed_buttons:
            rect = self.get_button_rect(name)
            if rect and rect.collidepoint(pos):
                self._handle_button_click(name)
                return

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
                if self.delete_confirm_focus == 'yes':
                    self._do_delete_user()
                else:
                    self.show_delete_confirm = False
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB):
                self.delete_confirm_focus = 'no' if self.delete_confirm_focus == 'yes' else 'yes'
            return

        # Guest confirmation mode — navigate buttons, Enter to confirm
        if self.show_guest_confirm:
            if event.key == pygame.K_RETURN:
                if self.guest_confirm_focus == 'yes':
                    self.username = 'Guest'
                    self.running = False
                else:
                    self.show_guest_confirm = False
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB):
                self.guest_confirm_focus = 'no' if self.guest_confirm_focus == 'yes' else 'yes'
            return

        if event.key == pygame.K_TAB:
            self.show_user_dropdown = False
            self._cycle_focus()
            return

        # ENTER — login with credentials, or prompt guest confirmation
        if event.key == pygame.K_RETURN:
            if self.username and self.password:
                self._do_login()
            else:
                self.show_guest_confirm = True
                self.guest_confirm_focus = 'yes'
                return

        if self.focus in ('username', 'password'):
            self._handle_input_key(event)
        elif self.focus == 'difficulty':
            self._handle_difficulty_key(event)

    def _cycle_focus(self):
        order = ['username', 'password', 'difficulty']
        idx = order.index(self.focus) if self.focus in order else 0
        self.focus = order[(idx + 1) % len(order)]

    def _handle_input_key(self, event: pygame.event.Event):
        if event.key == pygame.K_BACKSPACE:
            if self.focus == 'username':
                self.username = self.username[:-1]
                self.show_user_dropdown = bool(self.known_usernames)
            else:
                self.password = self.password[:-1]
        elif event.key == pygame.K_UP or event.key == pygame.K_DOWN:
            self._cycle_focus()
            self.show_user_dropdown = False
        else:
            # Filter control characters so Enter/Tab don't become input
            if not event.unicode or event.unicode in ('\r', '\n', '\t', '\x08'):
                return
            if self.focus == 'username' and len(self.username) < 16:
                self.username += event.unicode
                self.show_user_dropdown = bool(self.known_usernames)
            elif self.focus == 'password' and len(self.password) < 16:
                self.password += event.unicode

    def _handle_difficulty_key(self, event: pygame.event.Event):
        if event.key in (pygame.K_UP, pygame.K_w):
            self.difficulty_index = (self.difficulty_index - 1) % len(self.difficulty_options)
            self.selected_difficulty = self.difficulty_options[self.difficulty_index]
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.difficulty_index = (self.difficulty_index + 1) % len(self.difficulty_options)
            self.selected_difficulty = self.difficulty_options[self.difficulty_index]

    def _handle_button_click(self, button_name: str) -> None:
        handlers = {
            'login': self._do_login,
            'register': self._do_register,
            'skip_login': self._start_guest_session,
            'fullscreen': self._toggle_fullscreen,
            'tutorial': self._request_tutorial,
            'settings': self._request_settings,
            'quit': self._request_quit,
            'username_field': self._focus_username_field,
            'username_dropdown': self._toggle_user_dropdown,
            'password_field': self._focus_password_field,
            'diff_easy': lambda: self._select_difficulty('easy'),
            'diff_medium': lambda: self._select_difficulty('medium'),
            'diff_hard': lambda: self._select_difficulty('hard'),
            'guest_confirm_yes': self._start_guest_session,
            'guest_confirm_no': self._dismiss_guest_confirm,
            'delete_user': self._request_delete_user,
            'delete_confirm_yes': self._do_delete_user,
            'delete_confirm_no': self._dismiss_delete_confirm,
        }
        handler = handlers.get(button_name)
        if handler:
            handler()
        elif button_name.startswith('known_user_'):
            index_text = button_name.rsplit('_', 1)[-1]
            if index_text.isdigit():
                self._select_known_user(int(index_text))

    def _start_guest_session(self) -> None:
        self.username = 'Guest'
        self.running = False

    def _toggle_fullscreen(self) -> None:
        get_window().toggle_fullscreen()

    def _request_quit(self) -> None:
        self.want_to_quit = True
        self.running = False

    def _request_tutorial(self) -> None:
        self.tutorial_requested = True
        self.running = False

    def _request_settings(self) -> None:
        self.settings_requested = True
        self.running = False

    def _focus_username_field(self) -> None:
        self.focus = 'username'
        self.show_user_dropdown = bool(self.known_usernames)

    def _toggle_user_dropdown(self) -> None:
        self.focus = 'username'
        self.show_user_dropdown = bool(self.known_usernames) and not self.show_user_dropdown

    def _focus_password_field(self) -> None:
        self.focus = 'password'
        self.show_user_dropdown = False

    def _select_difficulty(self, difficulty: str) -> None:
        self.difficulty_index = self.difficulty_options.index(difficulty)
        self.selected_difficulty = difficulty
        self.focus = 'difficulty'
        self.show_user_dropdown = False

    def _dismiss_guest_confirm(self) -> None:
        self.show_guest_confirm = False

    def _dismiss_delete_confirm(self) -> None:
        self.show_delete_confirm = False

    def _request_delete_user(self) -> None:
        if self.username:
            self.delete_username = self.username
            self.show_delete_confirm = True
            self.delete_confirm_focus = 'no'
        else:
            self.message = "请先输入用户名"
            self._is_error = True
            self.message_timer = 120

    def _do_delete_user(self) -> None:
        if not self.delete_username:
            self.message = "请输入用户名"
            self._is_error = True
            self.message_timer = 120
            self.show_delete_confirm = False
            return
        if not self.password:
            self.message = "请输入当前密码后再删除"
            self._is_error = True
            self.message_timer = 120
            self.show_delete_confirm = False
            self.focus = 'password'
            return
        try:
            deleted = self.db.delete_user(self.delete_username, self.password)
        except DatabaseError:
            logger.warning("Failed to delete user account data", exc_info=True)
            self.message = "账户数据保存失败"
            self._is_error = True
            self.message_timer = 120
            self.show_delete_confirm = False
            return
        if deleted:
            self.message = f"用户 {self.delete_username} 已删除"
            self._is_error = False
            self.message_timer = 120
            self.username = ""
            self.password = ""
            self._load_known_usernames()
        else:
            self.message = "用户不存在或密码错误"
            self._is_error = True
            self.message_timer = 120
        self.show_delete_confirm = False

    def _do_login(self) -> None:
        if not self.username or not self.password:
            self.message = "请输入用户名和密码"
            self._is_error = True
            self.message_timer = 120
            return
        try:
            verified = self.db.verify_user(self.username, self.password)
        except DatabaseError:
            logger.warning("Failed to verify user credentials", exc_info=True)
            self.message = "账户数据读取失败"
            self._is_error = True
            self.message_timer = 120
            return
        if verified:
            try:
                self.db.record_login(self.username)
            except DatabaseError:
                logger.warning("Failed to record user login", exc_info=True)
                self.message = "账户数据保存失败"
                self._is_error = True
                self.message_timer = 120
                return
            self.message = ""
            self._is_error = False
            self.running = False
        else:
            self.message = "用户名或密码错误"
            self._is_error = True
            self.message_timer = 120

    def _do_register(self) -> None:
        if not self.username or not self.password:
            self.message = "请输入用户名和密码"
            self._is_error = True
            self.message_timer = 120
            return
        if len(self.username) < 3:
            self.message = "用户名至少3个字符"
            self._is_error = True
            self.message_timer = 120
            return
        if len(self.password) < 3:
            self.message = "密码至少3个字符"
            self._is_error = True
            self.message_timer = 120
            return
        try:
            created = self.db.create_user(self.username, self.password)
        except DatabaseError:
            logger.warning("Failed to create user account", exc_info=True)
            self.message = "账户数据保存失败"
            self._is_error = True
            self.message_timer = 120
            return
        if created:
            self.message = "注册成功！现在可以开始游戏了"
            self._is_error = False
            self.message_timer = 120
            self.mode = 'login'
            self.password = ""
            self._load_known_usernames()
        else:
            self.message = "用户名已存在"
            self._is_error = True
            self.message_timer = 120

    def _load_known_usernames(self) -> None:
        try:
            self.known_usernames = self.db.list_usernames()
            last_user = self.db.get_last_login_user()
        except DatabaseError:
            logger.warning("Failed to load known user names", exc_info=True)
            self.known_usernames = []
            last_user = None
        if last_user:
            self.username = last_user
            self.password = ""
            self.focus = 'password'

    def _select_known_user(self, index: int) -> None:
        if index < 0 or index >= len(self.known_usernames):
            return
        self.username = self.known_usernames[index]
        self.password = ""
        self.focus = 'password'
        self.show_user_dropdown = False

    def _handle_user_dropdown_click(self, pos: tuple[int, int]) -> bool:
        if not self.show_user_dropdown:
            return False
        for index in range(min(len(self.known_usernames), self.USER_DROPDOWN_MAX_ITEMS)):
            rect = self.get_button_rect(f'known_user_{index}')
            if rect and rect.collidepoint(pos):
                self._select_known_user(index)
                return True
        return False

    # -- Update ---------------------------------------------------------

    def update(self, *args, **kwargs) -> None:
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
        SC = SceneColors
        sw, sh = surface.get_width(), surface.get_height()

        # Background
        self._background.render_themed_style(surface, {
            'bg': SC.BG_PRIMARY,
            'bg_gradient': SC.BG_PANEL,
        })
        self._particles.render(surface, 'particle')

        # Title
        self._render_title(surface)

        # Compute layout
        layout = self._get_layout(sw, sh)

        # Left panel: Login
        self._render_left_panel(surface, layout["left_x"], layout["left_y"])

        # Right panel: Difficulty + Quick Tips
        self._render_right_panel(surface, layout["right_x"], layout["right_y"])

        # Bottom hint
        self._render_bottom_hint(surface, sw, sh)

        # Message
        if self.message:
            self._render_message(surface, sw, sh)

        # Fullscreen button
        self._render_fullscreen_button(surface, sw, sh)

        # Guest confirmation overlay (topmost)
        if self.show_guest_confirm:
            self._render_guest_confirm(surface)

        # Delete user confirmation overlay (topmost)
        if self.show_delete_confirm:
            self._render_delete_confirm(surface)

    def _get_layout(self, sw: int, sh: int) -> dict:
        total_w = self.PANEL_W * 2 + self.PANEL_GAP
        title_clearance = 110
        bottom_clearance = 96
        if sw >= total_w + 24:
            start_x = (sw - total_w) // 2
            panel_y = max(title_clearance, sh // 2 - self.PANEL_H // 2 - 20)
            return {
                "left_x": start_x,
                "left_y": panel_y,
                "right_x": start_x + self.PANEL_W + self.PANEL_GAP,
                "right_y": panel_y,
            }

        total_h = self.PANEL_H * 2 + self.STACKED_PANEL_GAP
        panel_x = max(20, (sw - self.PANEL_W) // 2)
        panel_y = max(
            title_clearance,
            (sh - bottom_clearance - total_h + title_clearance) // 2,
        )
        return {
            "left_x": panel_x,
            "left_y": panel_y,
            "right_x": panel_x,
            "right_y": panel_y + self.PANEL_H + self.STACKED_PANEL_GAP,
        }

    def _render_title(self, surface):
        SC = SceneColors
        sw, sh = surface.get_width(), surface.get_height()
        title_size = min(self._tokens.typography.TITLE_SIZE, max(72, sh // 10))
        title_font = get_cjk_font(title_size)
        ty = max(62, int(title_size * 0.72)) + math.sin(self.animation_time * 0.04) * 3

        for blur, alpha, color in [(4, 18, SC.GOLD_DIM), (2, 30, SC.GOLD_PRIMARY)]:
            glow = title_font.render("空 战", True, color)
            glow.set_alpha(alpha)
            for ox in range(-blur, blur + 1, 2):
                for oy in range(-blur, blur + 1, 2):
                    if ox * ox + oy * oy <= blur * blur:
                        r = glow.get_rect(center=(sw // 2 + ox, int(ty) + oy))
                        surface.blit(glow, r)
        title = title_font.render("空 战", True, SC.GOLD_PRIMARY)
        surface.blit(title, title.get_rect(center=(sw // 2, int(ty))))

    def _render_left_panel(self, surface, px, py):
        SC = SceneColors
        layout = self._get_login_layout(px, py)

        # Panel background
        draw_chamfered_panel(surface, px, py, self.PANEL_W, self.PANEL_H,
                             SC.BG_PANEL_LIGHT, SC.BORDER_DIM, SC.GOLD_GLOW, self.CHAMFER)

        # Section title
        title = self.section_font.render("飞行员登录", True, SC.GOLD_PRIMARY)
        surface.blit(title, title.get_rect(center=layout["title_center"]))

        # Decorative separator
        sep_y = py + 72
        pygame.draw.line(surface, SC.BORDER_DIM,
                         (px + 30, sep_y), (px + self.PANEL_W - 30, sep_y), 1)

        self._draw_input_row(
            surface,
            layout["username_label"],
            layout["username_field"],
            "用户名",
            self.username,
            self.focus == 'username',
            'username_field',
        )
        self._draw_username_dropdown_button(surface, layout["username_dropdown"])
        self._draw_input_row(
            surface,
            layout["password_label"],
            layout["password_field"],
            "密码",
            self.password,
            self.focus == 'password',
            'password_field',
            is_password=True,
        )

        self._draw_button(surface, layout["login"], "登录", 'login',
                         SceneColors.FOREST_GREEN, is_primary=True)
        self._draw_button(surface, layout["register"], "注册", 'register',
                         SceneColors.GOLD_DIM)

        self._draw_ghost_button(surface, layout["guest"], "游客模式", 'skip_login')

        # Settings button
        settings_rect = layout["settings"]
        self.register_button('settings', settings_rect)
        settings_hover = self.is_button_hovered('settings')
        settings_fill = (20, 32, 42) if settings_hover else SC.BG_PANEL_LIGHT
        settings_border = (82, 180, 200) if settings_hover else SC.BORDER_DIM
        draw_chamfered_panel(surface, settings_rect.x, settings_rect.y,
                             settings_rect.width, settings_rect.height,
                             settings_fill, settings_border, None, 6)
        settings_color = (160, 220, 240) if settings_hover else SC.TEXT_DIM
        settings_font = get_cjk_font(self._tokens.typography.SMALL_SIZE)
        settings_text = settings_font.render("设置", True, settings_color)
        surface.blit(settings_text, settings_text.get_rect(center=settings_rect.center))

        delete_rect = layout["delete"]
        self.register_button('delete_user', delete_rect)
        delete_hover = self.is_button_hovered('delete_user')
        delete_fill = (80, 20, 20) if delete_hover else SC.BG_PANEL_LIGHT
        delete_border = (200, 60, 60) if delete_hover else SC.BORDER_DIM
        draw_chamfered_panel(surface, delete_rect.x, delete_rect.y,
                             delete_rect.width, delete_rect.height,
                             delete_fill, delete_border, None, 6)
        delete_color = (255, 100, 100) if delete_hover else SC.TEXT_DIM
        delete_font = get_cjk_font(self._tokens.typography.SMALL_SIZE)
        delete_text = delete_font.render("删除用户", True, delete_color)
        surface.blit(delete_text, delete_text.get_rect(center=delete_rect.center))
        self._render_user_dropdown(surface, layout["username_dropdown"])

    def _get_login_layout(self, px: int, py: int) -> dict:
        content_x = px + self.LOGIN_PAD_X
        content_w = self.PANEL_W - self.LOGIN_PAD_X * 2
        field_x = content_x + self.LOGIN_LABEL_W + self.LOGIN_LABEL_GAP
        field_w = content_w - self.LOGIN_LABEL_W - self.LOGIN_LABEL_GAP
        username_dropdown_gap = 8
        username_field_w = field_w - self.USER_DROPDOWN_W - username_dropdown_gap

        user_y = py + 106
        pass_y = user_y + self.INPUT_H + self.LOGIN_ROW_GAP
        primary_y = pass_y + self.INPUT_H + 38
        secondary_y = primary_y + self.BTN_H + 20

        primary_total_w = self.LOGIN_PRIMARY_W * 2 + self.LOGIN_PRIMARY_GAP
        primary_x = px + (self.PANEL_W - primary_total_w) // 2
        secondary_total_w = self.LOGIN_SECONDARY_W * 2 + self.LOGIN_PRIMARY_GAP
        secondary_x = px + (self.PANEL_W - secondary_total_w) // 2

        return {
            "title_center": (px + self.PANEL_W // 2, py + 38),
            "username_label": pygame.Rect(content_x, user_y, self.LOGIN_LABEL_W, self.INPUT_H),
            "username_field": pygame.Rect(field_x, user_y, username_field_w, self.INPUT_H),
            "username_dropdown": pygame.Rect(
                field_x + username_field_w + username_dropdown_gap,
                user_y,
                self.USER_DROPDOWN_W,
                self.INPUT_H,
            ),
            "password_label": pygame.Rect(content_x, pass_y, self.LOGIN_LABEL_W, self.INPUT_H),
            "password_field": pygame.Rect(field_x, pass_y, field_w, self.INPUT_H),
            "login": pygame.Rect(primary_x, primary_y, self.LOGIN_PRIMARY_W, self.BTN_H),
            "register": pygame.Rect(
                primary_x + self.LOGIN_PRIMARY_W + self.LOGIN_PRIMARY_GAP,
                primary_y,
                self.LOGIN_PRIMARY_W,
                self.BTN_H,
            ),
            "guest": pygame.Rect(secondary_x, secondary_y, self.LOGIN_SECONDARY_W, self.LOGIN_SECONDARY_H),
            "settings": pygame.Rect(
                px + (self.PANEL_W - self.LOGIN_SECONDARY_W) // 2,
                secondary_y + self.LOGIN_SECONDARY_H + 16,
                self.LOGIN_SECONDARY_W,
                self.LOGIN_SECONDARY_H,
            ),
            "delete": pygame.Rect(
                secondary_x + self.LOGIN_SECONDARY_W + self.LOGIN_PRIMARY_GAP,
                secondary_y,
                self.LOGIN_SECONDARY_W,
                self.LOGIN_SECONDARY_H,
            ),
        }

    def _draw_input_row(self, surface, label_rect, input_rect, label, text, is_active, button_name, is_password=False):
        SC = SceneColors
        label_color = SC.GOLD_PRIMARY if is_active else SC.TEXT_DIM
        label_surf = fit_text_to_width(self.hint_font, label, label_color, label_rect.width)
        surface.blit(label_surf, label_surf.get_rect(midleft=(label_rect.x, label_rect.centery)))

        self.register_button(button_name, input_rect)
        self._draw_input(surface, input_rect, text, is_active, is_password=is_password)

    def _draw_username_dropdown_button(self, surface, rect: pygame.Rect) -> None:
        SC = SceneColors
        self.register_button('username_dropdown', rect)
        hover = self.is_button_hovered('username_dropdown')
        active = self.show_user_dropdown or hover
        border = SC.GOLD_PRIMARY if active else SC.BORDER_DIM
        fill = SC.BG_PANEL if active else SC.BG_PANEL_LIGHT
        if active:
            draw_chamfered_panel(surface, rect.x - 3, rect.y - 3,
                                 rect.width + 6, rect.height + 6,
                                 SC.BG_PANEL, SC.GOLD_GLOW, SC.GOLD_GLOW, 8)
        draw_chamfered_panel(surface, rect.x, rect.y, rect.width, rect.height,
                             fill, border, None, 6)

        arrow = "▲" if self.show_user_dropdown else "▼"
        color = SC.GOLD_PRIMARY if active else SC.TEXT_DIM
        arrow_surf = self.hint_font.render(arrow, True, color)
        surface.blit(arrow_surf, arrow_surf.get_rect(center=rect.center))

    def _render_user_dropdown(self, surface, anchor_rect: pygame.Rect) -> None:
        for index in range(self.USER_DROPDOWN_MAX_ITEMS):
            self.unregister_button(f'known_user_{index}')
        if not self.show_user_dropdown or not self.known_usernames:
            return

        SC = SceneColors
        visible_users = self.known_usernames[:self.USER_DROPDOWN_MAX_ITEMS]
        option_w = min(self.INPUT_W, anchor_rect.right - (anchor_rect.x - self.INPUT_W + self.USER_DROPDOWN_W))
        option_w = max(option_w, anchor_rect.width)
        menu_x = anchor_rect.right - option_w
        menu_y = anchor_rect.bottom + 6
        menu_h = len(visible_users) * self.USER_DROPDOWN_OPTION_H
        draw_chamfered_panel(surface, menu_x, menu_y, option_w, menu_h,
                             SC.BG_PANEL, SC.GOLD_PRIMARY, SC.GOLD_GLOW, 8)

        for index, username in enumerate(visible_users):
            btn_name = f'known_user_{index}'
            item_rect = pygame.Rect(
                menu_x + 4,
                menu_y + 4 + index * self.USER_DROPDOWN_OPTION_H,
                option_w - 8,
                self.USER_DROPDOWN_OPTION_H - 4,
            )
            self.register_button(btn_name, item_rect)
            hover = self.is_button_hovered(btn_name)
            fill = SC.BG_PANEL_LIGHT if hover or username == self.username else SC.BG_PANEL
            border = SC.GOLD_PRIMARY if hover else SC.BORDER_DIM
            draw_chamfered_panel(surface, item_rect.x, item_rect.y,
                                 item_rect.width, item_rect.height,
                                 fill, border, None, 5)
            color = SC.GOLD_PRIMARY if username == self.username else SC.TEXT_PRIMARY
            label = fit_text_to_width(self.tip_font, username, color, item_rect.width - 24)
            surface.blit(label, label.get_rect(midleft=(item_rect.x + 12, item_rect.centery)))

    def _render_right_panel(self, surface, px, py):
        SC = SceneColors

        # Panel background
        draw_chamfered_panel(surface, px, py, self.PANEL_W, self.PANEL_H,
                             SC.BG_PANEL_LIGHT, SC.BORDER_DIM, SC.GOLD_GLOW, self.CHAMFER)

        # Section title
        title = self.section_font.render("任务简报", True, SC.GOLD_PRIMARY)
        surface.blit(title, title.get_rect(center=(px + self.PANEL_W // 2, py + 32)))

        sep_y = py + 58
        pygame.draw.line(surface, SC.BORDER_DIM,
                         (px + 30, sep_y), (px + self.PANEL_W - 30, sep_y), 1)

        # -- Tutorial call-to-action --
        tutorial_y = py + 80
        tutorial_rect = pygame.Rect(px + 22, tutorial_y, self.PANEL_W - 44, 56)
        self._draw_tutorial_cta_button(surface, tutorial_rect)

        # -- Difficulty selection --
        diff_title_y = tutorial_rect.bottom + 14
        diff_label = self.hint_font.render("难度", True, SC.TEXT_DIM)
        surface.blit(diff_label, (px + 35, diff_title_y))

        diff_start_y = diff_title_y + 26
        for i, opt in enumerate(self.difficulty_options):
            dy = diff_start_y + i * (self.DIFF_OPTION_H + self.DIFF_GAP)
            is_sel = (i == self.difficulty_index)
            self._draw_diff_option(surface, px + 20, dy, self.PANEL_W - 40,
                                   self.difficulty_labels[opt], i, is_sel)

        # -- Quick Controls reference --
        tips_title_y = (
            diff_start_y
            + len(self.difficulty_options) * self.DIFF_OPTION_H
            + (len(self.difficulty_options) - 1) * self.DIFF_GAP
            + 12
        )
        tips_label = self.hint_font.render("操作说明", True, SC.TEXT_DIM)
        surface.blit(tips_label, (px + 35, tips_title_y))

        controls = [
            ("WASD / 方向键", "移动战机"),
            ("SHIFT (按住)", "加速"),
            ("B (按住2.4秒)", "返航基地"),
            ("H (按住3秒)", "停靠母舰"),
            ("K (按住3秒)", "投降"),
            ("ESC", "暂停游戏"),
            ("L", "切换HUD面板"),
        ]
        tip_y = tips_title_y + 26
        key_x = px + 35
        desc_right = px + self.PANEL_W - 35
        max_key_w = desc_right - key_x - 92
        for key, desc in controls:
            key_surf = fit_text_to_width(self.tip_font, key, SC.ACCENT_PRIMARY, max_key_w)
            desc_surf = self.tip_font.render(desc, True, SC.TEXT_DIM)
            surface.blit(key_surf, (key_x, tip_y))
            surface.blit(desc_surf, (desc_right - desc_surf.get_width(), tip_y))
            tip_y += 17

    def _draw_diff_option(self, surface, x, y, w, label, index, selected):
        SC = SceneColors
        btn_name = f'diff_{self.difficulty_options[index]}'
        rect = pygame.Rect(x, y, w, self.DIFF_OPTION_H)
        self.register_button(btn_name, rect)

        hover = self.is_button_hovered(btn_name)
        is_active = selected or (self.focus == 'difficulty' and hover)

        if is_active:
            draw_chamfered_panel(surface, x - 2, y - 2, w + 4, self.DIFF_OPTION_H + 4,
                                 SC.BG_PANEL, SC.GOLD_GLOW, SC.GOLD_GLOW, 6)

        draw_chamfered_panel(surface, x, y, w, self.DIFF_OPTION_H,
                             SC.BG_PANEL if is_active else SC.BG_PANEL_LIGHT,
                             SC.GOLD_PRIMARY if is_active else SC.BORDER_DIM,
                             None, 6)

        prefix = ">  " if is_active else "   "
        color = SC.GOLD_PRIMARY if is_active else SC.TEXT_DIM
        text = self.input_font.render(f"{prefix}{label}", True, color)
        surface.blit(text, text.get_rect(midleft=(x + 20, y + self.DIFF_OPTION_H // 2)))

    def _draw_tutorial_cta_button(self, surface, rect: pygame.Rect) -> None:
        """Primary tutorial CTA with the same chamfer language as difficulty options."""
        SC = SceneColors
        self.register_button('tutorial', rect)
        hover = self.is_button_hovered('tutorial')
        pulse = 0.5 + 0.5 * math.sin(self.animation_time * 0.075)
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
        text = fit_text_to_width(self.input_font, "新手教程", text_color, rect.width - 112)
        surface.blit(text, text.get_rect(midleft=(rect.x + 32, rect.centery)))

        chevron_x = rect.right - 42 + int(3 * pulse)
        chevron = [
            (chevron_x, rect.centery - 12),
            (chevron_x + 14, rect.centery),
            (chevron_x, rect.centery + 12),
        ]
        pygame.draw.lines(surface, gold if hover else border, False, chevron, 3)

    def _draw_input(self, surface, rect, text, is_active, is_password=False):
        SC = SceneColors
        ResponsiveHelper.get_scale_factor(surface.get_width(), surface.get_height())

        border_color = SC.GOLD_PRIMARY if is_active else SC.BORDER_DIM
        bg_color = SC.BG_PANEL if is_active else SC.BG_PANEL_LIGHT

        if is_active:
            draw_chamfered_panel(surface, rect.x - 3, rect.y - 3,
                                 rect.width + 6, rect.height + 6,
                                 SC.BG_PANEL, SC.GOLD_GLOW, SC.GOLD_GLOW, 8)
        draw_chamfered_panel(surface, rect.x, rect.y, rect.width, rect.height,
                             bg_color, border_color, None, 6)

        # Text content
        display = text
        if is_password and display:
            display = '*' * len(display)
        text_surf = self.input_font.render(display, True, SC.TEXT_PRIMARY)
        text_rect = text_surf.get_rect(midleft=(rect.x + 16, rect.centery))
        # Clamp CJK text overflow: shift left so text stays within input box
        max_right = rect.right - 6
        if text_rect.right > max_right:
            text_rect.right = max_right
        surface.blit(text_surf, text_rect)

        # Placeholder
        if not text:
            ph = "输入用户名..." if not is_password else "输入密码..."
            ph_surf = self.input_font.render(ph, True, SC.TEXT_DIM)
            ph_rect = ph_surf.get_rect(midleft=(rect.x + 16, rect.centery))
            surface.blit(ph_surf, ph_rect)

        # Cursor
        if is_active and self.cursor_visible:
            cx = text_rect.right + 3 if text else rect.x + 16
            pygame.draw.line(surface, SC.GOLD_PRIMARY,
                             (cx, rect.y + 12), (cx, rect.y + rect.height - 12), 2)

    def _draw_button(self, surface, rect, text, btn_name, color, is_primary=False,
                     is_focused=False):
        SC = SceneColors
        self.register_button(btn_name, rect)
        hover = self.is_button_hovered(btn_name)
        active = hover or is_focused

        btn_color = tuple(min(c + 30, 255) for c in color) if active else color

        if (is_primary and hover) or (is_focused and not hover):
            draw_chamfered_panel(surface, rect.x - 4, rect.y - 4,
                                 rect.width + 8, rect.height + 8,
                                 SC.BG_PANEL, SC.GOLD_GLOW, SC.GOLD_GLOW, 8)

        draw_chamfered_panel(surface, rect.x, rect.y, rect.width, rect.height,
                             btn_color,
                             SC.GOLD_PRIMARY if active else SC.BORDER_DIM,
                             None, 6)

        text_color = SC.TEXT_BRIGHT if active else SC.TEXT_PRIMARY
        text_surf = fit_text_to_width(self.button_font, text, text_color, rect.width - 32)
        surface.blit(text_surf, text_surf.get_rect(center=rect.center))

    def _draw_ghost_button(self, surface, rect, text, btn_name):
        """Ghost-style button — blends into panel, border highlights on hover."""
        SC = SceneColors
        self.register_button(btn_name, rect)
        hover = self.is_button_hovered(btn_name)

        fill = SC.BG_PANEL if hover else SC.BG_PANEL_LIGHT
        border = SC.GOLD_PRIMARY if hover else SC.BORDER_DIM
        draw_chamfered_panel(surface, rect.x, rect.y, rect.width, rect.height,
                             fill, border, None, 6)

        text_color = SC.TEXT_PRIMARY if hover else SC.TEXT_DIM
        font = get_cjk_font(self._tokens.typography.SMALL_SIZE)
        text_surf = fit_text_to_width(font, text, text_color, rect.width - 28)
        surface.blit(text_surf, text_surf.get_rect(center=rect.center))

    def _render_bottom_hint(self, surface, sw, sh):
        SC = SceneColors
        blink = (self.animation_time // 30) % 2 == 0
        color = SC.TEXT_DIM if blink else SC.TEXT_PRIMARY
        if self.show_guest_confirm:
            hints = "← → : 选择  |  ENTER: 确认  |  ESC: 返回"
        else:
            hints = "TAB: 切换焦点  |  ENTER: 确认  |  ESC: 退出"
        hint_surf = self.hint_font.render(hints, True, color)
        surface.blit(hint_surf, hint_surf.get_rect(center=(sw // 2, sh - 40)))

    def _render_message(self, surface, sw, sh):
        SC = SceneColors
        color = SC.DANGER_RED if self._is_error else SC.FOREST_GREEN
        msg_surf = self.input_font.render(self.message, True, color)
        surface.blit(msg_surf, msg_surf.get_rect(center=(sw // 2, sh - 75)))

    def _render_guest_confirm(self, surface):
        """覆盖确认对话框：游客模式不保存进度"""
        SC = SceneColors
        sw, sh = surface.get_width(), surface.get_height()

        # Dim overlay
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))

        # Dialog box
        dlg_w, dlg_h = 560, 300
        dlg_x = (sw - dlg_w) // 2
        dlg_y = (sh - dlg_h) // 2
        draw_chamfered_panel(surface, dlg_x, dlg_y, dlg_w, dlg_h,
                             SC.BG_PANEL_LIGHT, SC.GOLD_PRIMARY, SC.GOLD_GLOW, 12)

        # Title
        title = self.section_font.render("游客模式", True, SC.GOLD_PRIMARY)
        surface.blit(title, title.get_rect(center=(sw // 2, dlg_y + 50)))

        self._render_dialog_lines(
            surface,
            [
                "不登录也可以开始游戏。",
                "游客模式不会保存进度和最高分。",
            ],
            sw // 2,
            dlg_y + 112,
            dlg_w - 80,
        )

        # Buttons
        btn_w, btn_h = 190, 46
        gap = 20
        total_btn_w = btn_w * 2 + gap
        btn_start_x = sw // 2 - total_btn_w // 2
        btn_y = dlg_y + dlg_h - 70

        # Confirm button (primary)
        confirm_rect = pygame.Rect(btn_start_x, btn_y, btn_w, btn_h)
        self._draw_button(surface, confirm_rect, "游客进入",
                          'guest_confirm_yes', SC.FOREST_GREEN, is_primary=True,
                          is_focused=(self.guest_confirm_focus == 'yes'))

        # Cancel button (secondary)
        cancel_rect = pygame.Rect(btn_start_x + btn_w + gap, btn_y, btn_w, btn_h)
        self._draw_button(surface, cancel_rect, "返回",
                          'guest_confirm_no', SC.GOLD_DIM,
                          is_focused=(self.guest_confirm_focus == 'no'))


    def _render_delete_confirm(self, surface):
        """覆盖确认对话框：删除用户账号"""
        SC = SceneColors
        sw, sh = surface.get_width(), surface.get_height()

        # Dim overlay
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))

        # Dialog box
        dlg_w, dlg_h = 620, 280
        dlg_x = (sw - dlg_w) // 2
        dlg_y = (sh - dlg_h) // 2
        draw_chamfered_panel(surface, dlg_x, dlg_y, dlg_w, dlg_h,
                             SC.BG_PANEL_LIGHT, SC.GOLD_PRIMARY, SC.GOLD_GLOW, 12)

        # Title
        title = self.section_font.render("删除用户", True, SC.DANGER_RED)
        surface.blit(title, title.get_rect(center=(sw // 2, dlg_y + 50)))

        self._render_dialog_lines(
            surface,
            [
                f'确定要删除用户 "{self.delete_username}" 吗？',
                "此操作不可撤销，所有数据将被永久删除。",
            ],
            sw // 2,
            dlg_y + 104,
            dlg_w - 80,
        )

        # Buttons
        btn_w, btn_h = 190, 46
        gap = 20
        total_btn_w = btn_w * 2 + gap
        btn_start_x = sw // 2 - total_btn_w // 2
        btn_y = dlg_y + dlg_h - 70

        # Confirm button (danger — red)
        confirm_rect = pygame.Rect(btn_start_x, btn_y, btn_w, btn_h)
        self._draw_button(surface, confirm_rect, "确认删除",
                          'delete_confirm_yes', SC.DANGER_RED, is_primary=True,
                          is_focused=(self.delete_confirm_focus == 'yes'))

        # Cancel button
        cancel_rect = pygame.Rect(btn_start_x + btn_w + gap, btn_y, btn_w, btn_h)
        self._draw_button(surface, cancel_rect, "取消",
                          'delete_confirm_no', SC.GOLD_DIM,
                          is_focused=(self.delete_confirm_focus == 'no'))

    def _render_dialog_lines(self, surface, lines, center_x, start_y, max_width):
        y = start_y
        for line in lines:
            for wrapped in wrap_text(line, self.hint_font, max_width, max_lines=2):
                text = self.hint_font.render(wrapped, True, SceneColors.TEXT_DIM)
                surface.blit(text, text.get_rect(center=(center_x, y)))
                y += 30

    def _render_fullscreen_button(self, surface, sw, sh):
        SC = SceneColors
        window = get_window()
        fs_text = "退出全屏" if window.is_fullscreen() else "全屏"
        scale = ResponsiveHelper.get_scale_factor(sw, sh)
        btn_w = ResponsiveHelper.scale(160, scale)
        btn_h = ResponsiveHelper.scale(38, scale)
        rect = pygame.Rect(sw - btn_w - 30, sh - btn_h - 30, btn_w, btn_h)

        self.register_button('fullscreen', rect)
        hover = self.is_button_hovered('fullscreen')
        draw_chamfered_panel(surface, rect.x, rect.y, rect.width, rect.height,
                             SC.BG_PANEL_LIGHT if hover else SC.BG_PANEL,
                             SC.GOLD_PRIMARY if hover else SC.BORDER_DIM,
                             None, 6)
        fs_surf = self.tip_font.render(fs_text, True,
                                       SC.TEXT_PRIMARY if hover else SC.TEXT_DIM)
        surface.blit(fs_surf, fs_surf.get_rect(center=rect.center))

    # -- Public interface (used by SceneDirector) -----------------------

    def get_username(self) -> str:
        return self.username if self.username else 'Guest'

    def get_difficulty(self) -> str:
        return self.selected_difficulty

    def is_running(self) -> bool:
        return self.running

    def is_ready(self) -> bool:
        return not self.running and not self.tutorial_requested and not self.want_to_quit

    def should_quit(self) -> bool:
        return self.want_to_quit

    def should_open_tutorial(self) -> bool:
        return self.tutorial_requested

    def should_open_settings(self) -> bool:
        return self.settings_requested
