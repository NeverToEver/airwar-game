import pygame
import math
from .scene import Scene
from airwar.utils.database import UserDB
from airwar.utils.responsive import ResponsiveHelper
from airwar.ui.menu_background import MenuBackground
from airwar.config.design_tokens import get_design_tokens, ForestColors, MilitaryUI
from airwar.window.window import get_window
from airwar.utils.mouse_interaction import MouseInteractiveMixin
from airwar.ui.chamfered_panel import draw_chamfered_panel


class LoginScene(Scene, MouseInteractiveMixin):
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
        self.input_active = 'username'
        self.want_to_quit = False
        self.animation_time = 0
        self.cursor_visible = True
        self.cursor_timer = 0

        self._tokens = get_design_tokens()

        self.base_panel_width = 460
        self.base_panel_height = 500
        self.base_input_width = 380
        self.base_input_height = 65
        self.base_btn_width = 165
        self.base_btn_height = 58

        pygame.font.init()
        tokens = self._tokens

        self.title_font = pygame.font.Font(None, tokens.typography.TITLE_SIZE)
        self.input_font = pygame.font.Font(None, tokens.typography.SUBHEADING_SIZE)
        self.button_font = pygame.font.Font(None, tokens.typography.BODY_SIZE)
        self.hint_font = pygame.font.Font(None, tokens.typography.HUD_SIZE)

        self._background_renderer = MenuBackground()
        self._init_colors()
        self._init_military_colors()

    def _init_colors(self) -> None:
        colors = self._tokens.colors
        self.colors = {
            'bg': colors.BACKGROUND_PRIMARY,
            'bg_gradient': colors.BACKGROUND_SECONDARY,
            'panel': colors.BACKGROUND_PANEL,
            'panel_border': colors.PANEL_BORDER,
            'title': colors.TEXT_PRIMARY,
            'title_glow': colors.HUD_AMBER_BRIGHT,
            'input_bg': (20, 28, 55),
            'input_active': (30, 45, 75),
            'input_text': colors.TEXT_SECONDARY,
            'input_hint': colors.TEXT_MUTED,
            'hint': colors.TEXT_HINT,
            'button_login': (20, 50, 100),
            'button_register': (40, 80, 60),
            'button_quit': colors.DANGER_BUTTON_UNSELECTED_PRIMARY,
            'button_hover': colors.BUTTON_SELECTED_GLOW,
            'button_fullscreen': (30, 60, 90),
            'error': colors.HEALTH_DANGER,
            'success': colors.SUCCESS,
            'particle': colors.PARTICLE_PRIMARY,
        }

    def _init_military_colors(self) -> None:
        self.use_military_style = True
        self.military_colors = {
            'bg': ForestColors.BG_PRIMARY,
            'bg_gradient': ForestColors.BG_PANEL,
            'panel': ForestColors.BG_PANEL,
            'panel_border': ForestColors.BORDER_GLOW,
            'title': ForestColors.TEXT_PRIMARY,
            'title_glow': ForestColors.GOLD_GLOW,
            'input_bg': ForestColors.BG_PANEL_LIGHT,
            'input_active': ForestColors.BG_PANEL,
            'input_text': ForestColors.TEXT_PRIMARY,
            'input_hint': ForestColors.TEXT_DIM,
            'hint': ForestColors.TEXT_DIM,
            'button_login': ForestColors.FOREST_GREEN,
            'button_register': ForestColors.GOLD_DIM,
            'button_quit': ForestColors.DANGER_RED_DIM,
            'button_hover': ForestColors.GOLD_PRIMARY,
            'button_fullscreen': ForestColors.BG_PANEL_LIGHT,
            'error': ForestColors.DANGER_RED,
            'success': ForestColors.FOREST_GREEN,
            'particle': ForestColors.GOLD_PRIMARY,
        }

    def _reset_rects(self, width, height):
        scale = ResponsiveHelper.get_scale_factor(width, height)

        self.panel_width = ResponsiveHelper.scale(self.base_panel_width, scale)
        self.panel_height = ResponsiveHelper.scale(self.base_panel_height, scale)
        self.panel_x = width // 2 - self.panel_width // 2
        self.panel_y = height // 2 - self.panel_height // 2 - ResponsiveHelper.scale(30, scale)

        self.input_width = ResponsiveHelper.scale(self.base_input_width, scale)
        self.input_height = ResponsiveHelper.scale(self.base_input_height, scale)
        self.input_x = width // 2 - self.input_width // 2
        self.username_input_y = self.panel_y + ResponsiveHelper.scale(160, scale)
        self.password_input_y = self.panel_y + ResponsiveHelper.scale(280, scale)

        btn_width = ResponsiveHelper.scale(self.base_btn_width, scale)
        btn_height = ResponsiveHelper.scale(self.base_btn_height, scale)
        btn_gap = ResponsiveHelper.scale(30, scale)
        btn_y = self.password_input_y + ResponsiveHelper.scale(140, scale)
        self.login_btn = pygame.Rect(width // 2 - btn_width - btn_gap // 2, btn_y, btn_width, btn_height)
        self.register_btn = pygame.Rect(width // 2 + btn_gap // 2, btn_y, btn_width, btn_height)
        self.quit_btn = pygame.Rect(width // 2 - ResponsiveHelper.scale(75, scale), btn_y + ResponsiveHelper.scale(75, scale), ResponsiveHelper.scale(150, scale), ResponsiveHelper.scale(50, scale))

        fullscreen_btn_width = ResponsiveHelper.scale(180, scale)
        fullscreen_btn_height = ResponsiveHelper.scale(45, scale)
        self.fullscreen_btn = pygame.Rect(width - ResponsiveHelper.scale(50, scale) - fullscreen_btn_width, height // 2 - fullscreen_btn_height // 2, fullscreen_btn_width, fullscreen_btn_height)

    def exit(self) -> None:
        pass

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            self._handle_keyboard_event(event)
        elif event.type == pygame.MOUSEMOTION:
            self.handle_mouse_motion(event.pos)
            self._update_input_active_from_hover()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.handle_mouse_click(event.pos):
                self._handle_button_click(self.get_hovered_button())

    def _update_input_active_from_hover(self) -> None:
        hovered = self.get_hovered_button()
        if hovered == 'username':
            self.input_active = 'username'
        elif hovered == 'password':
            self.input_active = 'password'

    def _handle_button_click(self, button_name: str) -> None:
        if button_name is None:
            return
        
        if button_name == 'login':
            self._do_login()
        elif button_name == 'register':
            self._do_register()
        elif button_name == 'quit':
            self.want_to_quit = True
            self.running = False
        elif button_name == 'fullscreen':
            window = get_window()
            window.toggle_fullscreen()
        elif button_name == 'username':
            self.input_active = 'username'
        elif button_name == 'password':
            self.input_active = 'password'

    def _handle_keyboard_event(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_TAB:
            self.input_active = 'password' if self.input_active == 'username' else 'username'
        elif event.key == pygame.K_BACKSPACE:
            if self.input_active == 'username':
                self.username = self.username[:-1]
            else:
                self.password = self.password[:-1]
        elif event.key == pygame.K_RETURN:
            if self.mode == 'login':
                self._do_login()
            else:
                self._do_register()
        elif event.key == pygame.K_ESCAPE:
            self.want_to_quit = True
            self.running = False
        elif event.key in (pygame.K_UP, pygame.K_DOWN):
            self.input_active = 'password' if self.input_active == 'username' else 'username'
        else:
            if len(self.username) < 16 and self.input_active == 'username':
                self.username += event.unicode
            elif len(self.password) < 16 and self.input_active == 'password':
                self.password += event.unicode

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
            self.message = "Registration successful! Login now."
            self.message_timer = 120
            self.mode = 'login'
            self.password = ""
        else:
            self.message = "Username already exists"
            self.message_timer = 120

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

        self._background_renderer._animation_time = self.animation_time
        self._background_renderer.update()

    def render(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        if self.use_military_style:
            self._background_renderer.render_military_style(surface, self.military_colors)
        else:
            self._background_renderer.render(surface, self.colors)

        self._reset_rects(width, height)

        self._render_panel(surface, width, height)
        self._render_title(surface, width)
        self._render_inputs(surface)
        self._render_buttons(surface)
        self._render_hints(surface, width, height)

        if self.message:
            self._render_message(surface, width, height)

    def _render_panel(self, surface, width, height):
        scale = ResponsiveHelper.get_scale_factor(width, height)

        if self.use_military_style:
            # Military style: chamfered panel
            colors = self.military_colors
            draw_chamfered_panel(
                surface,
                self.panel_x,
                self.panel_y,
                self.panel_width,
                self.panel_height,
                colors['panel'],
                colors['panel_border'],
                colors['title_glow'],
                MilitaryUI.CHAMFER_DEPTH
            )
            # Decorative line
            pygame.draw.line(
                surface,
                ForestColors.BORDER_DIM,
                (self.panel_x + ResponsiveHelper.scale(25, scale), self.panel_y + ResponsiveHelper.scale(85, scale)),
                (self.panel_x + self.panel_width - ResponsiveHelper.scale(25, scale), self.panel_y + ResponsiveHelper.scale(85, scale)),
                1
            )
        else:
            # Original style
            colors = self.colors
            panel_rect = pygame.Rect(self.panel_x, self.panel_y, self.panel_width, self.panel_height)

            for i in range(4, 0, -1):
                expand = i * 4
                glow_surf = pygame.Surface((self.panel_width + expand * 2, self.panel_height + expand * 2), pygame.SRCALPHA)
                alpha = max(5, 30 // i)
                pygame.draw.rect(glow_surf, (*colors['title_glow'], alpha),
                              glow_surf.get_rect(), border_radius=18)
                surface.blit(glow_surf, (self.panel_x - expand, self.panel_y - expand))

            pygame.draw.rect(surface, colors['panel'], panel_rect, border_radius=15)

            border_surf = pygame.Surface((self.panel_width, self.panel_height), pygame.SRCALPHA)
            pygame.draw.rect(border_surf, (*colors['panel_border'], 150),
                           border_surf.get_rect(), width=2, border_radius=15)
            surface.blit(border_surf, panel_rect.topleft)

            pygame.draw.line(surface, colors['panel_border'],
                            (self.panel_x + ResponsiveHelper.scale(25, scale), self.panel_y + ResponsiveHelper.scale(85, scale)),
                            (self.panel_x + self.panel_width - ResponsiveHelper.scale(25, scale), self.panel_y + ResponsiveHelper.scale(85, scale)), width=1)

    def _render_title(self, surface, width):
        height = surface.get_height()
        scale = ResponsiveHelper.get_scale_factor(width, height)
        title_text = "LOGIN" if self.mode == 'login' else "REGISTER"

        glow_offset = math.sin(self.animation_time * 0.05) * 3
        title_y = self.panel_y + ResponsiveHelper.scale(45, scale)

        if self.use_military_style:
            # Military style: amber glow
            colors = self.military_colors
            for blur, alpha, color in [(4, 15, ForestColors.GOLD_DIM), (2, 25, ForestColors.GOLD_PRIMARY)]:
                glow_surf = self.title_font.render(title_text, True, color)
                glow_surf.set_alpha(alpha)
                for offset_x in range(-blur, blur + 1, 2):
                    for offset_y in range(-blur, blur + 1, 2):
                        if offset_x * offset_x + offset_y * offset_y <= blur * blur:
                            glow_rect = glow_surf.get_rect(
                                center=(width // 2 + offset_x, int(title_y + glow_offset) + offset_y))
                            surface.blit(glow_surf, glow_rect)

            title_shadow = self.title_font.render(title_text, True, ForestColors.BG_PANEL)
            surface.blit(title_shadow, title_shadow.get_rect(
                center=(width // 2 + 2, int(title_y + glow_offset) + 2)))

            title = self.title_font.render(title_text, True, ForestColors.GOLD_PRIMARY)
            surface.blit(title, title.get_rect(center=(width // 2, int(title_y + glow_offset))))
        else:
            # Original style
            colors = self.colors
            for blur, alpha, color in [
                (6, 18, ForestColors.TITLE_GLOW_OUTER),
                (4, 30, ForestColors.TITLE_GLOW_MIDDLE),
                (2, 45, ForestColors.TITLE_GLOW_INNER)
            ]:
                glow_surf = self.title_font.render(title_text, True, color)
                glow_surf.set_alpha(alpha)
                for offset_x in range(-blur, blur + 1, 2):
                    for offset_y in range(-blur, blur + 1, 2):
                        if offset_x * offset_x + offset_y * offset_y <= blur * blur:
                            glow_rect = glow_surf.get_rect(
                                center=(width // 2 + offset_x, int(title_y + glow_offset) + offset_y))
                            surface.blit(glow_surf, glow_rect)

            title_shadow = self.title_font.render(title_text, True, ForestColors.TITLE_SHADOW)
            surface.blit(title_shadow, title_shadow.get_rect(
                center=(width // 2 + 2, int(title_y + glow_offset) + 2)))

            title = self.title_font.render(title_text, True, colors['title'])
            surface.blit(title, title.get_rect(center=(width // 2, int(title_y + glow_offset))))

    def _render_inputs(self, surface):
        self.username_input_rect = pygame.Rect(self.input_x, self.username_input_y,
                                              self.input_width, self.input_height)
        self.password_input_rect = pygame.Rect(self.input_x, self.password_input_y,
                                             self.input_width, self.input_height)

        self.register_button('username', self.username_input_rect)
        self.register_button('password', self.password_input_rect)

        self._render_input_box(surface, self.username_input_rect, "USERNAME", self.username, True)
        self._render_input_box(surface, self.password_input_rect, "PASSWORD", self.password, False)

    def _render_input_box(self, surface, rect, label, text, is_username):
        is_active = self.input_active == label.split('_')[0].lower()
        is_hovered = self.is_button_hovered(label.split('_')[0].lower())

        if self.use_military_style:
            colors = self.military_colors
            self._draw_military_input(surface, rect, label, text, is_username, is_active, is_hovered)
        else:
            colors = self.colors
            self._draw_input_glow(surface, rect, is_active or is_hovered, colors)
            self._draw_input_bg(surface, rect, is_active, is_hovered, colors)
            self._draw_input_label(surface, rect, label, is_active, colors)
            self._draw_input_content(surface, rect, text, is_username, colors)

    def _draw_military_input(self, surface, rect, label, text, is_username, is_active, is_hovered):
        """Draw input box in military style with chamfered corners."""
        colors = self.military_colors
        scale = ResponsiveHelper.get_scale_factor(surface.get_width(), surface.get_height())

        # Draw glow if active
        if is_active:
            glow_color = ForestColors.GOLD_GLOW
            draw_chamfered_panel(
                surface,
                rect.x - 3, rect.y - 3,
                rect.width + 6, rect.height + 6,
                ForestColors.BG_PANEL,
                glow_color,
                glow_color,
                8
            )

        # Draw chamfered input background
        draw_chamfered_panel(
            surface,
            rect.x, rect.y,
            rect.width, rect.height,
            colors['input_bg'] if is_active else ForestColors.BG_PANEL_LIGHT,
            ForestColors.BORDER_DIM if is_active else ForestColors.BG_PANEL,
            None,
            6
        )

        # Draw label
        label_y = rect.y - ResponsiveHelper.scale(28, scale)
        label_color = ForestColors.GOLD_PRIMARY if is_active else ForestColors.TEXT_DIM
        label_surf = self.input_font.render(label, True, label_color)
        surface.blit(label_surf, (rect.x + ResponsiveHelper.scale(10, scale), label_y))

        # Draw content
        display_text = text if text else ""
        if not is_username and display_text:
            display_text = '*' * len(display_text)
        text_surf = self.input_font.render(display_text, True, ForestColors.TEXT_PRIMARY)
        text_rect = text_surf.get_rect(midleft=(rect.x + ResponsiveHelper.scale(20, scale), rect.y + rect.height // 2))
        surface.blit(text_surf, text_rect)

        if not text:
            placeholder = "Enter username..." if is_username else "Enter password..."
            ph_surf = self.input_font.render(placeholder, True, ForestColors.TEXT_DIM)
            ph_rect = ph_surf.get_rect(midleft=(rect.x + ResponsiveHelper.scale(20, scale), rect.y + rect.height // 2))
            surface.blit(ph_surf, ph_rect)

        if self.cursor_visible:
            cursor_x = text_rect.right + 3 if text else rect.x + ResponsiveHelper.scale(20, scale)
            pygame.draw.line(surface, ForestColors.GOLD_PRIMARY,
                           (cursor_x, rect.y + ResponsiveHelper.scale(15, scale)), (cursor_x, rect.y + rect.height - ResponsiveHelper.scale(15, scale)), 2)

    def _draw_input_glow(self, surface, rect, is_active, colors):
        if not is_active:
            return
        for i in range(5, 0, -1):
            expand = i * 3
            glow_rect = pygame.Rect(rect.x - expand, rect.y - expand,
                                  rect.width + expand * 2, rect.height + expand * 2)
            glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
            alpha = max(3, 25 // i)
            pygame.draw.rect(glow_surf, (*colors['title_glow'], alpha),
                           glow_surf.get_rect(), border_radius=12)
            surface.blit(glow_surf, glow_rect)

    def _draw_input_bg(self, surface, rect, is_active, is_hovered=False, colors=None):
        if colors is None:
            colors = self.colors
        bg_color = colors['input_active'] if is_active else colors['input_bg']
        if is_hovered and not is_active:
            bg_color = tuple(min(c + 10, 255) for c in bg_color)
        pygame.draw.rect(surface, bg_color, rect, border_radius=10)
        border_color = colors['title'] if is_active else colors['panel_border']
        border_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(border_surf, (*border_color, 180 if is_active else 120),
                        border_surf.get_rect(), width=2, border_radius=10)
        surface.blit(border_surf, rect.topleft)

    def _draw_input_label(self, surface, rect, label, is_active, colors=None):
        if colors is None:
            colors = self.colors
        width, height = surface.get_size()
        scale = ResponsiveHelper.get_scale_factor(width, height)
        label_y = rect.y - ResponsiveHelper.scale(32, scale)
        label_surf = self.input_font.render(label, True,
                                          colors['title_glow'] if is_active else colors['input_hint'])
        surface.blit(label_surf, (rect.x + ResponsiveHelper.scale(10, scale), label_y))

    def _draw_input_content(self, surface, rect, text, is_username, colors=None):
        if colors is None:
            colors = self.colors
        width, height = surface.get_size()
        scale = ResponsiveHelper.get_scale_factor(width, height)
        display_text = text if text else ""
        if not is_username and display_text:
            display_text = '*' * len(display_text)
        text_surf = self.input_font.render(display_text, True, colors['input_text'])
        text_rect = text_surf.get_rect(midleft=(rect.x + ResponsiveHelper.scale(20, scale), rect.y + rect.height // 2))
        surface.blit(text_surf, text_rect)
        if not text:
            placeholder = "Enter username..." if is_username else "Enter password..."
            ph_surf = self.input_font.render(placeholder, True, ForestColors.INPUT_PLACEHOLDER)
            ph_rect = ph_surf.get_rect(midleft=(rect.x + ResponsiveHelper.scale(20, scale), rect.y + rect.height // 2))
            surface.blit(ph_surf, ph_rect)
        if self.cursor_visible:
            cursor_x = text_rect.right + 3 if text else rect.x + ResponsiveHelper.scale(20, scale)
            pygame.draw.line(surface, colors['title'],
                           (cursor_x, rect.y + ResponsiveHelper.scale(15, scale)), (cursor_x, rect.y + rect.height - ResponsiveHelper.scale(15, scale)), 2)

    def _render_buttons(self, surface):
        if self.use_military_style:
            self._render_military_button(surface, self.login_btn, "LOGIN", ForestColors.FOREST_GREEN, True, 'login')
            self._render_military_button(surface, self.register_btn, "REGISTER", ForestColors.GOLD_DIM, False, 'register')
            self._render_military_button(surface, self.quit_btn, "QUIT", ForestColors.DANGER_RED_DIM, False, 'quit')
        else:
            self._render_button(surface, self.login_btn, "LOGIN", self.colors['button_login'], True, 'login')
            self._render_button(surface, self.register_btn, "REGISTER", self.colors['button_register'], False, 'register')
            self._render_button(surface, self.quit_btn, "QUIT", self.colors['button_quit'], False, 'quit')

        window = get_window()
        fullscreen_text = "Exit Fullscreen" if window.is_fullscreen() else "Enter Fullscreen"
        if self.use_military_style:
            self._render_military_button(surface, self.fullscreen_btn, fullscreen_text, ForestColors.BG_PANEL_LIGHT, False, 'fullscreen')
        else:
            self._render_button(surface, self.fullscreen_btn, fullscreen_text, self.colors['button_fullscreen'], False, 'fullscreen')

    def _render_military_button(self, surface, rect, text, color, is_primary, button_name=None):
        """Render button in military style with chamfered corners."""
        self.register_button(button_name, rect)
        hover = self.is_button_hovered(button_name) if button_name else False

        btn_color = color
        if hover:
            btn_color = tuple(min(c + 30, 255) for c in color)

        # Draw glow for primary buttons
        if is_primary and hover:
            draw_chamfered_panel(
                surface,
                rect.x - 4, rect.y - 4,
                rect.width + 8, rect.height + 8,
                ForestColors.BG_PANEL,
                ForestColors.GOLD_GLOW,
                ForestColors.GOLD_GLOW,
                8
            )

        # Draw chamfered button
        draw_chamfered_panel(
            surface,
            rect.x, rect.y,
            rect.width, rect.height,
            btn_color,
            ForestColors.GOLD_PRIMARY if hover else ForestColors.BORDER_DIM,
            None,
            6
        )

        text_color = ForestColors.TEXT_BRIGHT if hover else ForestColors.TEXT_PRIMARY
        text_surf = self.button_font.render(text, True, text_color)
        text_rect = text_surf.get_rect(center=rect.center)
        surface.blit(text_surf, text_rect)

    def _render_button(self, surface, rect, text, color, is_primary, button_name=None):
        self.register_button(button_name, rect)
        hover = self.is_button_hovered(button_name) if button_name else False

        btn_color = tuple(min(c + 30, 255) for c in color) if hover else color

        if is_primary and hover:
            for i in range(4, 0, -1):
                expand = i * 3
                glow_surf = pygame.Surface((rect.width + expand * 2, rect.height + expand * 2), pygame.SRCALPHA)
                alpha = max(3, 20 // i)
                pygame.draw.rect(glow_surf, (*self.colors['title_glow'], alpha),
                               glow_surf.get_rect(), border_radius=12)
                surface.blit(glow_surf, (rect.x - expand, rect.y - expand))

        pygame.draw.rect(surface, btn_color, rect, border_radius=10)

        border_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(border_surf, (*self.colors['title_glow'], 120 if hover else 100),
                        border_surf.get_rect(), width=2, border_radius=10)
        surface.blit(border_surf, rect.topleft)

        text_surf = self.button_font.render(text, True, ForestColors.BUTTON_TEXT)
        text_rect = text_surf.get_rect(center=rect.center)
        surface.blit(text_surf, text_rect)

    def _render_hints(self, surface, width, height):
        pulse = (math.sin(self.animation_time * 0.08) + 1) / 2
        if self.use_military_style:
            hint_color = ForestColors.TEXT_DIM
            if (self.animation_time // 60) % 2 == 0:
                hint_color = ForestColors.TEXT_DIM
            else:
                hint_color = ForestColors.TEXT_PRIMARY
        else:
            if (self.animation_time // 60) % 2 == 0:
                hint_color = ForestColors.HINT_DIM
            else:
                hint_color = ForestColors.HINT_BRIGHT

        hints = "TAB: switch  |  ENTER: submit  |  ESC: quit"
        hint_surf = self.hint_font.render(hints, True, hint_color)
        surface.blit(hint_surf, hint_surf.get_rect(center=(width // 2, height - 50)))

    def _render_message(self, surface, width, height):
        scale = ResponsiveHelper.get_scale_factor(width, height)
        if self.use_military_style:
            msg_color = ForestColors.DANGER_RED if "Invalid" in self.message or "min" in self.message or "exists" in self.message else ForestColors.FOREST_GREEN
        else:
            msg_color = self.colors['error'] if "Invalid" in self.message or "min" in self.message or "exists" in self.message else self.colors['success']
        msg_surf = self.input_font.render(self.message, True, msg_color)
        msg_y = self.password_input_y + self.input_height + ResponsiveHelper.scale(70, scale)
        surface.blit(msg_surf, msg_surf.get_rect(center=(width // 2, msg_y)))

    def get_username(self) -> str:
        return self.username

    def is_ready(self) -> bool:
        return not self.running

    def should_quit(self) -> bool:
        return self.want_to_quit
