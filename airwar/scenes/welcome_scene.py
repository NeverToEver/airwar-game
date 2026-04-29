"""Welcome scene -- single-page beginner interface combining login, difficulty, and quick tips."""
import pygame
import math
from .scene import Scene
from airwar.utils.database import UserDB
from airwar.utils.responsive import ResponsiveHelper
from airwar.ui.menu_background import MenuBackground
from airwar.ui.particles import ParticleSystem
from airwar.ui.chamfered_panel import draw_chamfered_panel
from airwar.config.design_tokens import get_design_tokens, SceneColors, SystemUI
from airwar.window.window import get_window
from airwar.utils.mouse_interaction import MouseInteractiveMixin


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
    PANEL_W = 440
    PANEL_H = 460
    CHAMFER = 12
    INPUT_W = 340
    INPUT_H = 54
    BTN_W = 150
    BTN_H = 48
    DIFF_OPTION_H = 48
    DIFF_GAP = 8

    def __init__(self):
        Scene.__init__(self)
        MouseInteractiveMixin.__init__(self)

    def enter(self, **kwargs) -> None:
        self.clear_hover()
        self.clear_buttons()
        self.db = UserDB()
        self.running = True
        self.mode = 'login'
        self.username = ""
        self.password = ""
        self.message = ""
        self.message_timer = 0
        self.want_to_quit = False
        self.show_guest_confirm = False
        self.guest_confirm_focus = 'yes'  # 'yes' | 'no'
        self.animation_time = 0
        self.cursor_visible = True
        self.cursor_timer = 0

        # Difficulty
        self.difficulty_options = ['easy', 'medium', 'hard']
        self.difficulty_labels = {'easy': 'EASY', 'medium': 'MEDIUM', 'hard': 'HARD'}
        self.selected_difficulty = 'medium'
        self.difficulty_index = 1

        # Focus: 'username' | 'password' | 'difficulty'
        self.focus = 'username'

        self._tokens = get_design_tokens()
        self._background = MenuBackground()
        self._particles = ParticleSystem()
        self._particles.reset(self._tokens.components.PARTICLE_COUNT, 'particle')

        pygame.font.init()
        tokens = self._tokens
        self.title_font = pygame.font.Font(None, tokens.typography.TITLE_SIZE)
        self.section_font = pygame.font.Font(None, tokens.typography.SUBHEADING_SIZE)
        self.input_font = pygame.font.Font(None, tokens.typography.BODY_SIZE)
        self.button_font = pygame.font.Font(None, tokens.typography.BODY_SIZE)
        self.hint_font = pygame.font.Font(None, tokens.typography.HUD_SIZE)
        self.tip_font = pygame.font.Font(None, tokens.typography.TINY_SIZE)

    def exit(self) -> None:
        pass

    # -- Event handling -------------------------------------------------

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            self._handle_keydown(event)
        elif event.type == pygame.MOUSEMOTION:
            self.handle_mouse_motion(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.handle_mouse_click(event.pos):
                btn = self.get_hovered_button()
                if btn:
                    self._handle_button_click(btn)
                # Clicking on input areas sets focus (only outside confirm mode)
                if not self.show_guest_confirm:
                    if btn == 'username_field':
                        self.focus = 'username'
                    elif btn == 'password_field':
                        self.focus = 'password'

    def _handle_keydown(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_ESCAPE:
            if self.show_guest_confirm:
                self.show_guest_confirm = False
                return
            self.want_to_quit = True
            self.running = False
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
            else:
                self.password = self.password[:-1]
        elif event.key == pygame.K_UP or event.key == pygame.K_DOWN:
            self._cycle_focus()
        else:
            # Filter control characters so Enter/Tab don't become input
            if not event.unicode or event.unicode in ('\r', '\n', '\t', '\x08'):
                return
            if self.focus == 'username' and len(self.username) < 16:
                self.username += event.unicode
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
        if button_name == 'login':
            self._do_login()
        elif button_name == 'register':
            self._do_register()
        elif button_name == 'skip_login':
            self.username = 'Guest'
            self.running = False
        elif button_name == 'fullscreen':
            get_window().toggle_fullscreen()
        elif button_name == 'quit':
            self.want_to_quit = True
            self.running = False
        elif button_name == 'username_field':
            self.focus = 'username'
        elif button_name == 'password_field':
            self.focus = 'password'
        elif button_name == 'diff_easy':
            self.difficulty_index = 0
            self.selected_difficulty = 'easy'
            self.focus = 'difficulty'
        elif button_name == 'diff_medium':
            self.difficulty_index = 1
            self.selected_difficulty = 'medium'
            self.focus = 'difficulty'
        elif button_name == 'diff_hard':
            self.difficulty_index = 2
            self.selected_difficulty = 'hard'
            self.focus = 'difficulty'
        elif button_name == 'guest_confirm_yes':
            self.username = 'Guest'
            self.running = False
        elif button_name == 'guest_confirm_no':
            self.show_guest_confirm = False

    def _do_login(self) -> None:
        if not self.username or not self.password:
            self.message = "Enter username and password"
            self.message_timer = 120
            return
        if self.db.verify_user(self.username, self.password):
            self.message = ""
            self.running = False
        else:
            self.message = "Invalid username or password"
            self.message_timer = 120

    def _do_register(self) -> None:
        if not self.username or not self.password:
            self.message = "Enter username and password"
            self.message_timer = 120
            return
        if len(self.username) < 3:
            self.message = "Username min 3 characters"
            self.message_timer = 120
            return
        if len(self.password) < 3:
            self.message = "Password min 3 characters"
            self.message_timer = 120
            return
        if self.db.create_user(self.username, self.password):
            self.message = "Registration successful! You can now start."
            self.message_timer = 120
            self.mode = 'login'
            self.password = ""
        else:
            self.message = "Username already exists"
            self.message_timer = 120

    # -- Update ---------------------------------------------------------

    def update(self, *args, **kwargs) -> None:
        self.animation_time += 1
        if self.message_timer > 0:
            self.message_timer -= 1
            if self.message_timer == 0:
                self.message = ""
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
        total_w = self.PANEL_W * 2 + 30
        start_x = (sw - total_w) // 2
        panel_y = sh // 2 - self.PANEL_H // 2 - 20

        # Left panel: Login
        self._render_left_panel(surface, start_x, panel_y)

        # Right panel: Difficulty + Quick Tips
        self._render_right_panel(surface, start_x + self.PANEL_W + 30, panel_y)

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

    def _render_title(self, surface):
        SC = SceneColors
        sw = surface.get_width()
        ty = 45 + math.sin(self.animation_time * 0.04) * 4

        for blur, alpha, color in [(4, 18, SC.GOLD_DIM), (2, 30, SC.GOLD_PRIMARY)]:
            glow = self.title_font.render("AIR WAR", True, color)
            glow.set_alpha(alpha)
            for ox in range(-blur, blur + 1, 2):
                for oy in range(-blur, blur + 1, 2):
                    if ox * ox + oy * oy <= blur * blur:
                        r = glow.get_rect(center=(sw // 2 + ox, int(ty) + oy))
                        surface.blit(glow, r)
        title = self.title_font.render("AIR WAR", True, SC.GOLD_PRIMARY)
        surface.blit(title, title.get_rect(center=(sw // 2, int(ty))))

    def _render_left_panel(self, surface, px, py):
        SC = SceneColors
        scale = ResponsiveHelper.get_scale_factor(surface.get_width(), surface.get_height())

        # Panel background
        draw_chamfered_panel(surface, px, py, self.PANEL_W, self.PANEL_H,
                             SC.BG_PANEL_LIGHT, SC.BORDER_DIM, SC.GOLD_GLOW, self.CHAMFER)

        # Section title
        title = self.section_font.render("PILOT LOGIN", True, SC.GOLD_PRIMARY)
        surface.blit(title, title.get_rect(center=(px + self.PANEL_W // 2, py + 32)))

        # Decorative separator
        sep_y = py + 58
        pygame.draw.line(surface, SC.BORDER_DIM,
                         (px + 30, sep_y), (px + self.PANEL_W - 30, sep_y), 1)

        # Username field
        input_x = px + (self.PANEL_W - self.INPUT_W) // 2
        uname_y = py + 90
        uname_rect = pygame.Rect(input_x, uname_y, self.INPUT_W, self.INPUT_H)
        self.register_button('username_field', uname_rect)
        self._draw_input(surface, uname_rect, "USERNAME", self.username,
                         self.focus == 'username')

        # Password field
        pass_y = uname_y + self.INPUT_H + 30
        pass_rect = pygame.Rect(input_x, pass_y, self.INPUT_W, self.INPUT_H)
        self.register_button('password_field', pass_rect)
        self._draw_input(surface, pass_rect, "PASSWORD", self.password,
                         self.focus == 'password', is_password=True)

        # Buttons
        btn_y = pass_y + self.INPUT_H + 35
        login_rect = pygame.Rect(px + self.PANEL_W // 2 - self.BTN_W - 12, btn_y,
                                 self.BTN_W, self.BTN_H)
        register_rect = pygame.Rect(px + self.PANEL_W // 2 + 12, btn_y,
                                    self.BTN_W, self.BTN_H)
        self._draw_button(surface, login_rect, "LOGIN", 'login',
                         SceneColors.FOREST_GREEN, is_primary=True)
        self._draw_button(surface, register_rect, "REGISTER", 'register',
                         SceneColors.GOLD_DIM)

        # Guest mode button (ghost style — subtle border, fills on hover)
        guest_btn_w = self.BTN_W
        guest_btn_h = 40
        guest_y = btn_y + self.BTN_H + 18
        guest_rect = pygame.Rect(px + self.PANEL_W // 2 - guest_btn_w // 2,
                                 guest_y, guest_btn_w, guest_btn_h)
        self._draw_ghost_button(surface, guest_rect, "Play as Guest", 'skip_login')

    def _render_right_panel(self, surface, px, py):
        SC = SceneColors

        # Panel background
        draw_chamfered_panel(surface, px, py, self.PANEL_W, self.PANEL_H,
                             SC.BG_PANEL_LIGHT, SC.BORDER_DIM, SC.GOLD_GLOW, self.CHAMFER)

        # Section title
        title = self.section_font.render("MISSION BRIEFING", True, SC.GOLD_PRIMARY)
        surface.blit(title, title.get_rect(center=(px + self.PANEL_W // 2, py + 32)))

        sep_y = py + 58
        pygame.draw.line(surface, SC.BORDER_DIM,
                         (px + 30, sep_y), (px + self.PANEL_W - 30, sep_y), 1)

        # -- Difficulty selection --
        diff_title_y = py + 80
        diff_label = self.hint_font.render("DIFFICULTY", True, SC.TEXT_DIM)
        surface.blit(diff_label, (px + 35, diff_title_y))

        diff_start_y = diff_title_y + 26
        for i, opt in enumerate(self.difficulty_options):
            dy = diff_start_y + i * (self.DIFF_OPTION_H + self.DIFF_GAP)
            is_sel = (i == self.difficulty_index)
            self._draw_diff_option(surface, px + 20, dy, self.PANEL_W - 40,
                                   self.difficulty_labels[opt], i, is_sel)

        # -- Quick Controls reference --
        tips_title_y = diff_start_y + len(self.difficulty_options) * (self.DIFF_OPTION_H + self.DIFF_GAP) + 14
        tips_label = self.hint_font.render("QUICK CONTROLS", True, SC.TEXT_DIM)
        surface.blit(tips_label, (px + 35, tips_title_y))

        controls = [
            ("WASD / Arrows", "Move ship"),
            ("SHIFT (hold)", "Boost speed"),
            ("H (hold 3s)", "Dock in mothership"),
            ("K (hold 3s)", "Surrender run"),
            ("ESC", "Pause game"),
            ("L", "Toggle HUD panel"),
        ]
        tip_y = tips_title_y + 26
        for key, desc in controls:
            key_surf = self.tip_font.render(key, True, SC.ACCENT_PRIMARY)
            desc_surf = self.tip_font.render(desc, True, SC.TEXT_DIM)
            surface.blit(key_surf, (px + 35, tip_y))
            surface.blit(desc_surf, (px + self.PANEL_W - desc_surf.get_width() - 35, tip_y))
            tip_y += 20

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

    def _draw_input(self, surface, rect, label, text, is_active, is_password=False):
        SC = SceneColors
        scale = ResponsiveHelper.get_scale_factor(surface.get_width(), surface.get_height())

        border_color = SC.GOLD_PRIMARY if is_active else SC.BORDER_DIM
        bg_color = SC.BG_PANEL if is_active else SC.BG_PANEL_LIGHT

        if is_active:
            draw_chamfered_panel(surface, rect.x - 3, rect.y - 3,
                                 rect.width + 6, rect.height + 6,
                                 SC.BG_PANEL, SC.GOLD_GLOW, SC.GOLD_GLOW, 8)
        draw_chamfered_panel(surface, rect.x, rect.y, rect.width, rect.height,
                             bg_color, border_color, None, 6)

        # Label above
        label_y = rect.y - 22
        label_color = SC.GOLD_PRIMARY if is_active else SC.TEXT_DIM
        label_surf = self.hint_font.render(label, True, label_color)
        surface.blit(label_surf, (rect.x + 8, label_y))

        # Text content
        display = text
        if is_password and display:
            display = '*' * len(display)
        text_surf = self.input_font.render(display, True, SC.TEXT_PRIMARY)
        text_rect = text_surf.get_rect(midleft=(rect.x + 16, rect.centery))
        surface.blit(text_surf, text_rect)

        # Placeholder
        if not text:
            ph = "Enter username..." if not is_password else "Enter password..."
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
        text_surf = self.button_font.render(text, True, text_color)
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
        font = pygame.font.Font(None, self._tokens.typography.SMALL_SIZE)
        text_surf = font.render(text, True, text_color)
        surface.blit(text_surf, text_surf.get_rect(center=rect.center))

    def _render_bottom_hint(self, surface, sw, sh):
        SC = SceneColors
        blink = (self.animation_time // 30) % 2 == 0
        color = SC.TEXT_DIM if blink else SC.TEXT_PRIMARY
        if self.show_guest_confirm:
            hints = "← → : select  |  ENTER: confirm  |  ESC: back"
        else:
            hints = "TAB: switch focus  |  ENTER: confirm  |  ESC: quit"
        hint_surf = self.hint_font.render(hints, True, color)
        surface.blit(hint_surf, hint_surf.get_rect(center=(sw // 2, sh - 40)))

    def _render_message(self, surface, sw, sh):
        SC = SceneColors
        is_error = "Invalid" in self.message or "min" in self.message or "exists" in self.message
        color = SC.DANGER_RED if is_error else SC.FOREST_GREEN
        msg_surf = self.input_font.render(self.message, True, color)
        surface.blit(msg_surf, msg_surf.get_rect(center=(sw // 2, sh - 75)))

    def _render_guest_confirm(self, surface):
        """Overlay confirmation dialog: 'Continue as Guest?'"""
        SC = SceneColors
        sw, sh = surface.get_width(), surface.get_height()

        # Dim overlay
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))

        # Dialog box
        dlg_w, dlg_h = 480, 280
        dlg_x = (sw - dlg_w) // 2
        dlg_y = (sh - dlg_h) // 2
        draw_chamfered_panel(surface, dlg_x, dlg_y, dlg_w, dlg_h,
                             SC.BG_PANEL_LIGHT, SC.GOLD_PRIMARY, SC.GOLD_GLOW, 12)

        # Title
        title = self.section_font.render("GUEST MODE", True, SC.GOLD_PRIMARY)
        surface.blit(title, title.get_rect(center=(sw // 2, dlg_y + 50)))

        # Description
        desc = self.hint_font.render(
            "Play without an account — progress and", True, SC.TEXT_DIM)
        desc2 = self.hint_font.render(
            "high scores will not be saved.", True, SC.TEXT_DIM)
        surface.blit(desc, desc.get_rect(center=(sw // 2, dlg_y + 115)))
        surface.blit(desc2, desc2.get_rect(center=(sw // 2, dlg_y + 148)))

        # Buttons
        btn_w, btn_h = 170, 46
        gap = 20
        total_btn_w = btn_w * 2 + gap
        btn_start_x = sw // 2 - total_btn_w // 2
        btn_y = dlg_y + dlg_h - 70

        # Confirm button (primary)
        confirm_rect = pygame.Rect(btn_start_x, btn_y, btn_w, btn_h)
        self._draw_button(surface, confirm_rect, "PLAY AS GUEST",
                          'guest_confirm_yes', SC.FOREST_GREEN, is_primary=True,
                          is_focused=(self.guest_confirm_focus == 'yes'))

        # Cancel button (secondary)
        cancel_rect = pygame.Rect(btn_start_x + btn_w + gap, btn_y, btn_w, btn_h)
        self._draw_button(surface, cancel_rect, "GO BACK",
                          'guest_confirm_no', SC.GOLD_DIM,
                          is_focused=(self.guest_confirm_focus == 'no'))

    def _render_fullscreen_button(self, surface, sw, sh):
        SC = SceneColors
        window = get_window()
        fs_text = "Exit Fullscreen" if window.is_fullscreen() else "Fullscreen"
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
        return not self.running

    def should_quit(self) -> bool:
        return self.want_to_quit
