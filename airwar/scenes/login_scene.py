import pygame
from .scene import Scene
from airwar.utils.database import UserDB


class LoginScene(Scene):
    def enter(self, **kwargs) -> None:
        self.db = UserDB()
        self.running = True
        self.mode = 'login'
        self.username = ""
        self.password = ""
        self.message = ""
        self.message_timer = 0
        self.input_active = 'username'
        self.want_to_quit = False

        pygame.font.init()

        self.title_font = pygame.font.Font(None, 80)
        self.input_font = pygame.font.Font(None, 42)
        self.button_font = pygame.font.Font(None, 36)
        self.hint_font = pygame.font.Font(None, 26)
        self.big_font = pygame.font.Font(None, 120)

        self.colors = {
            'bg': (8, 8, 25),
            'panel': (12, 15, 35),
            'panel_border': (50, 70, 120),
            'title': (120, 220, 255),
            'input_bg': (18, 22, 48),
            'input_active': (28, 45, 75),
            'input_text': (230, 240, 255),
            'input_hint': (90, 110, 150),
            'button_login': (25, 200, 130),
            'button_register': (70, 100, 180),
            'button_quit': (180, 55, 55),
            'button_hover': (50, 230, 160),
            'error': (255, 110, 110),
            'success': (110, 255, 180),
            'hint': (80, 90, 130),
        }

        self._create_stars()
        self._reset_rects(1200, 700)

    def _create_stars(self):
        import random
        self.stars = []
        for _ in range(80):
            self.stars.append({
                'x': random.random(),
                'y': random.random(),
                'size': random.random() * 2.5 + 1,
                'speed': random.random() * 0.4 + 0.15,
                'brightness': random.randint(80, 180),
            })

    def _reset_rects(self, width, height):
        import random
        self.panel_width = 440
        self.panel_height = 480
        self.panel_x = width // 2 - self.panel_width // 2
        self.panel_y = height // 2 - self.panel_height // 2 - 20

        self.input_width = 360
        self.input_height = 65
        self.input_x = width // 2 - self.input_width // 2
        self.username_input_y = self.panel_y + 150
        self.password_input_y = self.panel_y + 260

        btn_width = 155
        btn_height = 58
        btn_gap = 30
        btn_y = self.password_input_y + 130
        self.login_btn = pygame.Rect(width // 2 - btn_width - btn_gap // 2, btn_y, btn_width, btn_height)
        self.register_btn = pygame.Rect(width // 2 + btn_gap // 2, btn_y, btn_width, btn_height)
        self.quit_btn = pygame.Rect(width // 2 - 75, btn_y + 75, 150, 50)

    def exit(self) -> None:
        pass

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
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
                if len(self.username) < 16:
                    if self.input_active == 'username':
                        self.username += event.unicode
                if len(self.password) < 16:
                    if self.input_active == 'password':
                        self.password += event.unicode

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            if self.username_input_rect.collidepoint(mx, my):
                self.input_active = 'username'
            elif self.password_input_rect.collidepoint(mx, my):
                self.input_active = 'password'
            elif self.login_btn.collidepoint(mx, my):
                self._do_login()
            elif self.register_btn.collidepoint(mx, my):
                self._do_register()
            elif self.quit_btn.collidepoint(mx, my):
                self.want_to_quit = True
                self.running = False

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
        import random
        if self.message_timer > 0:
            self.message_timer -= 1
            if self.message_timer == 0:
                self.message = ""

        for star in self.stars:
            star['y'] += star['speed'] * 0.01
            if star['y'] > 1:
                star['y'] = 0
                star['x'] = random.random()

    def render(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        surface.fill(self.colors['bg'])

        self._reset_rects(width, height)

        self._render_stars(surface, width, height)

        self._render_panel(surface, width, height)

        self._render_title(surface, width)

        self._render_inputs(surface)

        self._render_buttons(surface)

        self._render_hints(surface, width, height)

        if self.message:
            self._render_message(surface, width, height)

    def _render_stars(self, surface, width, height):
        for star in self.stars:
            x = int(star['x'] * width)
            y = int(star['y'] * height)
            brightness = star['brightness']
            pygame.draw.circle(surface, (brightness, brightness, brightness + 20), (x, y), int(star['size']))

    def _render_panel(self, surface, width, height):
        panel_rect = pygame.Rect(self.panel_x, self.panel_y, self.panel_width, self.panel_height)
        pygame.draw.rect(surface, self.colors['panel'], panel_rect, border_radius=15)
        pygame.draw.rect(surface, self.colors['panel_border'], panel_rect, width=2, border_radius=15)

        pygame.draw.line(surface, self.colors['panel_border'],
                        (self.panel_x + 20, self.panel_y + 80),
                        (self.panel_x + self.panel_width - 20, self.panel_y + 80), width=1)

    def _render_title(self, surface, width):
        title_text = "LOGIN" if self.mode == 'login' else "REGISTER"
        title = self.title_font.render(title_text, True, self.colors['title'])
        title_shadow = self.title_font.render(title_text, True, (20, 60, 100))
        surface.blit(title_shadow, title.get_rect(center=(width // 2 + 2, self.panel_y + 45 + 2)))
        surface.blit(title, title.get_rect(center=(width // 2, self.panel_y + 45)))

    def _render_inputs(self, surface):
        self.username_input_rect = pygame.Rect(self.input_x, self.username_input_y, self.input_width, self.input_height)
        self.password_input_rect = pygame.Rect(self.input_x, self.password_input_y, self.input_width, self.input_height)

        self._render_input_box(surface, self.username_input_rect, "USERNAME", self.username, True)
        self._render_input_box(surface, self.password_input_rect, "PASSWORD", self.password, False)

    def _render_input_box(self, surface, rect, label, text, is_username):
        bg_color = self.colors['input_active'] if self.input_active == label.split('_')[0].lower() else self.colors['input_bg']
        pygame.draw.rect(surface, bg_color, rect, border_radius=10)

        border_color = self.colors['title'] if self.input_active == label.split('_')[0].lower() else self.colors['panel_border']
        pygame.draw.rect(surface, border_color, rect, width=2, border_radius=10)

        label_y = rect.y - 28
        label_surf = self.input_font.render(label, True, self.colors['input_hint'])
        surface.blit(label_surf, (rect.x + 8, label_y))

        display_text = text if text else ""
        if not is_username and display_text:
            display_text = '*' * len(display_text)
        
        text_surf = self.input_font.render(display_text, True, self.colors['input_text'])
        text_rect = text_surf.get_rect(midleft=(rect.x + 20, rect.y + rect.height // 2))
        surface.blit(text_surf, text_rect)

        if not text:
            placeholder = "Enter username..." if is_username else "Enter password..."
            ph_surf = self.input_font.render(placeholder, True, (50, 60, 90))
            ph_rect = ph_surf.get_rect(midleft=(rect.x + 20, rect.y + rect.height // 2))
            surface.blit(ph_surf, ph_rect)

        if is_username:
            cursor_x = text_rect.right + 3 if text else rect.x + 20
        else:
            cursor_x = rect.x + 20 + len(text) * 18 if text else rect.x + 20
        if (pygame.time.get_ticks() // 500) % 2 == 0 and self.input_active == label.split('_')[0].lower():
            pygame.draw.line(surface, self.colors['title'], (cursor_x, rect.y + 15), (cursor_x, rect.y + rect.height - 15), 2)

    def _render_buttons(self, surface):
        self._render_button(surface, self.login_btn, "LOGIN", self.colors['button_login'], True)
        self._render_button(surface, self.register_btn, "REGISTER", self.colors['button_register'], False)
        self._render_button(surface, self.quit_btn, "QUIT", self.colors['button_quit'], False)

    def _render_button(self, surface, rect, text, color, is_primary):
        mouse_pos = pygame.mouse.get_pos()
        hover = rect.collidepoint(mouse_pos)

        btn_color = self.colors['button_hover'] if hover and is_primary else color
        if hover:
            btn_color = tuple(min(c + 30, 255) for c in btn_color)

        pygame.draw.rect(surface, btn_color, rect, border_radius=10)
        pygame.draw.rect(surface, (100, 130, 190), rect, width=2, border_radius=10)

        text_surf = self.button_font.render(text, True, (245, 250, 255))
        text_rect = text_surf.get_rect(center=rect.center)
        surface.blit(text_surf, text_rect)

    def _render_hints(self, surface, width, height):
        hints = "TAB: switch  |  ENTER: submit  |  ESC: quit"
        hint_surf = self.hint_font.render(hints, True, self.colors['hint'])
        surface.blit(hint_surf, hint_surf.get_rect(center=(width // 2, height - 50)))

    def _render_message(self, surface, width, height):
        msg_color = self.colors['error'] if "Invalid" in self.message or "min" in self.message or "exists" in self.message else self.colors['success']
        msg_surf = self.input_font.render(self.message, True, msg_color)
        msg_y = self.password_input_y + self.input_height + 60
        surface.blit(msg_surf, msg_surf.get_rect(center=(width // 2, msg_y)))

    def get_username(self) -> str:
        return self.username

    def is_ready(self) -> bool:
        return not self.running

    def should_quit(self) -> bool:
        return self.want_to_quit
