import pygame
import math
import random
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
        self.animation_time = 0
        self.cursor_visible = True
        self.cursor_timer = 0
        self.particles = []
        self.stars = []

        pygame.font.init()

        self.title_font = pygame.font.Font(None, 100)
        self.input_font = pygame.font.Font(None, 42)
        self.button_font = pygame.font.Font(None, 36)
        self.hint_font = pygame.font.Font(None, 26)

        self._init_colors()
        self._init_particles()
        self._init_stars()

    def _init_colors(self) -> None:
        self.colors = {
            'bg': (5, 5, 20),
            'bg_gradient': (12, 12, 45),
            'panel': (15, 20, 40),
            'panel_border': (50, 80, 140),
            'title': (255, 255, 255),
            'title_glow': (100, 200, 255),
            'input_bg': (20, 28, 55),
            'input_active': (30, 45, 75),
            'input_text': (230, 240, 255),
            'input_hint': (90, 100, 140),
            'hint': (70, 75, 120),
            'button_login': (20, 50, 100),
            'button_register': (40, 80, 60),
            'button_quit': (80, 40, 40),
            'button_hover': (30, 70, 130),
            'error': (255, 100, 100),
            'success': (100, 255, 150),
            'particle': (100, 180, 255),
        }

    def _init_particles(self) -> None:
        self.particles = []
        for _ in range(50):
            self.particles.append({
                'x': random.random(),
                'y': random.random(),
                'size': random.uniform(1.5, 4.0),
                'speed': random.uniform(0.3, 1.0),
                'alpha': random.randint(80, 180),
                'pulse_speed': random.uniform(0.02, 0.06),
                'pulse_offset': random.random() * math.pi * 2,
            })

    def _init_stars(self) -> None:
        self.stars = []
        for _ in range(120):
            self.stars.append({
                'x': random.random(),
                'y': random.random(),
                'size': random.uniform(0.5, 2.5),
                'brightness': random.randint(40, 160),
                'twinkle_speed': random.uniform(0.02, 0.07),
                'twinkle_offset': random.random() * math.pi * 2,
            })

    def _reset_rects(self, width, height):
        self.panel_width = 460
        self.panel_height = 500
        self.panel_x = width // 2 - self.panel_width // 2
        self.panel_y = height // 2 - self.panel_height // 2 - 30

        self.input_width = 380
        self.input_height = 65
        self.input_x = width // 2 - self.input_width // 2
        self.username_input_y = self.panel_y + 160
        self.password_input_y = self.panel_y + 280

        btn_width = 165
        btn_height = 58
        btn_gap = 30
        btn_y = self.password_input_y + 140
        self.login_btn = pygame.Rect(width // 2 - btn_width - btn_gap // 2, btn_y, btn_width, btn_height)
        self.register_btn = pygame.Rect(width // 2 + btn_gap // 2, btn_y, btn_width, btn_height)
        self.quit_btn = pygame.Rect(width // 2 - 75, btn_y + 75, 150, 50)

    def exit(self) -> None:
        pass

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            self._handle_keyboard_event(event)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._handle_mouse_event(event)

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
                self._spawn_input_particles()
            elif len(self.password) < 16 and self.input_active == 'password':
                self.password += event.unicode

    def _handle_mouse_event(self, event: pygame.event.Event) -> None:
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

    def _spawn_input_particles(self) -> None:
        for _ in range(5):
            self.particles.append({
                'x': 0.5 + random.uniform(-0.08, 0.08),
                'y': 0.5 + random.uniform(-0.05, 0.05),
                'size': random.uniform(2.0, 4.5),
                'speed': random.uniform(0.5, 1.5),
                'alpha': random.randint(120, 200),
                'pulse_speed': random.uniform(0.05, 0.1),
                'pulse_offset': random.random() * math.pi * 2,
                'is_burst': True,
                'burst_timer': 50,
            })

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

        for star in self.stars:
            star['y'] += star['speed'] * 0.008 if hasattr(star, 'speed') else 0.008
            if star['y'] > 1:
                star['y'] = 0
                star['x'] = random.random()

        for p in self.particles[:]:
            p['y'] -= p['speed'] * 0.003

            if p.get('is_burst'):
                p['burst_timer'] -= 1
                p['alpha'] = max(0, p['alpha'] - 5)
                if p['burst_timer'] <= 0 or p['alpha'] <= 0:
                    self.particles.remove(p)
            else:
                if p['y'] < -0.1:
                    p['y'] = 1.1
                    p['x'] = random.random()
                    p['alpha'] = random.randint(80, 180)

    def _draw_gradient_background(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        for y in range(0, height, 3):
            ratio = y / height
            r = int(self.colors['bg'][0] * (1 - ratio * 0.6) + self.colors['bg_gradient'][0] * ratio * 0.6)
            g = int(self.colors['bg'][1] * (1 - ratio * 0.6) + self.colors['bg_gradient'][1] * ratio * 0.6)
            b = int(self.colors['bg'][2] * (1 - ratio * 0.6) + self.colors['bg_gradient'][2] * ratio * 0.6)
            pygame.draw.line(surface, (r, g, b), (0, y), (width, y))

    def _draw_stars(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        for star in self.stars:
            x = int(star['x'] * width)
            y = int(star['y'] * height)
            twinkle = math.sin(self.animation_time * star['twinkle_speed'] + star['twinkle_offset'])
            brightness = int(star['brightness'] * (0.5 + 0.5 * twinkle))
            pygame.draw.circle(surface, (brightness, brightness, brightness + 40), (x, y), int(star['size']))

    def _draw_particles(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        for p in self.particles:
            x = int(p['x'] * width)
            y = int(p['y'] * height)
            pulse = math.sin(self.animation_time * p['pulse_speed'] + p.get('pulse_offset', 0))
            alpha = int(p['alpha'] * (0.6 + 0.4 * pulse))
            size = int(p['size'] * (0.7 + 0.3 * pulse))

            particle_surf = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
            for i in range(size * 2, 0, -2):
                layer_alpha = int(alpha * (size * 2 - i) / (size * 2) * 0.4)
                pygame.draw.circle(particle_surf, (*self.colors['particle'], layer_alpha),
                                 (size * 2, size * 2), i)
            surface.blit(particle_surf, (x - size * 2, y - size * 2))

    def render(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        self._draw_gradient_background(surface)
        self._draw_stars(surface)
        self._draw_particles(surface)

        self._reset_rects(width, height)

        self._render_panel(surface, width, height)
        self._render_title(surface, width)
        self._render_inputs(surface)
        self._render_buttons(surface)
        self._render_hints(surface, width, height)

        if self.message:
            self._render_message(surface, width, height)

    def _render_panel(self, surface, width, height):
        panel_rect = pygame.Rect(self.panel_x, self.panel_y, self.panel_width, self.panel_height)

        for i in range(4, 0, -1):
            expand = i * 4
            glow_surf = pygame.Surface((self.panel_width + expand * 2, self.panel_height + expand * 2), pygame.SRCALPHA)
            alpha = max(5, 30 // i)
            pygame.draw.rect(glow_surf, (*self.colors['title_glow'], alpha),
                          glow_surf.get_rect(), border_radius=18)
            surface.blit(glow_surf, (self.panel_x - expand, self.panel_y - expand))

        pygame.draw.rect(surface, self.colors['panel'], panel_rect, border_radius=15)

        border_surf = pygame.Surface((self.panel_width, self.panel_height), pygame.SRCALPHA)
        pygame.draw.rect(border_surf, (*self.colors['panel_border'], 150),
                       border_surf.get_rect(), width=2, border_radius=15)
        surface.blit(border_surf, panel_rect.topleft)

        pygame.draw.line(surface, self.colors['panel_border'],
                        (self.panel_x + 25, self.panel_y + 85),
                        (self.panel_x + self.panel_width - 25, self.panel_y + 85), width=1)

    def _render_title(self, surface, width):
        title_text = "LOGIN" if self.mode == 'login' else "REGISTER"

        glow_offset = math.sin(self.animation_time * 0.05) * 3

        for blur, alpha, color in [(6, 18, (50, 120, 180)), (4, 30, (70, 160, 220)), (2, 45, (100, 200, 255))]:
            glow_surf = self.title_font.render(title_text, True, color)
            glow_surf.set_alpha(alpha)
            for offset_x in range(-blur, blur + 1, 2):
                for offset_y in range(-blur, blur + 1, 2):
                    if offset_x * offset_x + offset_y * offset_y <= blur * blur:
                        glow_rect = glow_surf.get_rect(
                            center=(width // 2 + offset_x, int(self.panel_y + 45 + glow_offset) + offset_y))
                        surface.blit(glow_surf, glow_rect)

        title_shadow = self.title_font.render(title_text, True, (20, 60, 100))
        surface.blit(title_shadow, title_shadow.get_rect(
            center=(width // 2 + 2, int(self.panel_y + 45 + glow_offset) + 2)))

        title = self.title_font.render(title_text, True, self.colors['title'])
        surface.blit(title, title.get_rect(center=(width // 2, int(self.panel_y + 45 + glow_offset))))

    def _render_inputs(self, surface):
        self.username_input_rect = pygame.Rect(self.input_x, self.username_input_y,
                                              self.input_width, self.input_height)
        self.password_input_rect = pygame.Rect(self.input_x, self.password_input_y,
                                             self.input_width, self.input_height)

        self._render_input_box(surface, self.username_input_rect, "USERNAME", self.username, True)
        self._render_input_box(surface, self.password_input_rect, "PASSWORD", self.password, False)

    def _render_input_box(self, surface, rect, label, text, is_username):
        is_active = self.input_active == label.split('_')[0].lower()
        self._draw_input_glow(surface, rect, is_active)
        self._draw_input_bg(surface, rect, is_active)
        self._draw_input_label(surface, rect, label, is_active)
        self._draw_input_content(surface, rect, text, is_username)

    def _draw_input_glow(self, surface, rect, is_active):
        if not is_active:
            return
        for i in range(5, 0, -1):
            expand = i * 3
            glow_rect = pygame.Rect(rect.x - expand, rect.y - expand,
                                  rect.width + expand * 2, rect.height + expand * 2)
            glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
            alpha = max(3, 25 // i)
            pygame.draw.rect(glow_surf, (*self.colors['title_glow'], alpha),
                           glow_surf.get_rect(), border_radius=12)
            surface.blit(glow_surf, glow_rect)

    def _draw_input_bg(self, surface, rect, is_active):
        bg_color = self.colors['input_active'] if is_active else self.colors['input_bg']
        pygame.draw.rect(surface, bg_color, rect, border_radius=10)
        border_color = self.colors['title'] if is_active else self.colors['panel_border']
        border_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(border_surf, (*border_color, 180 if is_active else 120),
                        border_surf.get_rect(), width=2, border_radius=10)
        surface.blit(border_surf, rect.topleft)

    def _draw_input_label(self, surface, rect, label, is_active):
        label_y = rect.y - 32
        label_surf = self.input_font.render(label, True,
                                          self.colors['title_glow'] if is_active else self.colors['input_hint'])
        surface.blit(label_surf, (rect.x + 10, label_y))

    def _draw_input_content(self, surface, rect, text, is_username):
        display_text = text if text else ""
        if not is_username and display_text:
            display_text = '*' * len(display_text)
        text_surf = self.input_font.render(display_text, True, self.colors['input_text'])
        text_rect = text_surf.get_rect(midleft=(rect.x + 20, rect.y + rect.height // 2))
        surface.blit(text_surf, text_rect)
        if not text:
            placeholder = "Enter username..." if is_username else "Enter password..."
            ph_surf = self.input_font.render(placeholder, True, (60, 70, 100))
            ph_rect = ph_surf.get_rect(midleft=(rect.x + 20, rect.y + rect.height // 2))
            surface.blit(ph_surf, ph_rect)
        if self.cursor_visible:
            cursor_x = text_rect.right + 3 if text else rect.x + 20
            pygame.draw.line(surface, self.colors['title'],
                           (cursor_x, rect.y + 15), (cursor_x, rect.y + rect.height - 15), 2)

    def _render_buttons(self, surface):
        self._render_button(surface, self.login_btn, "LOGIN", self.colors['button_login'], True)
        self._render_button(surface, self.register_btn, "REGISTER", self.colors['button_register'], False)
        self._render_button(surface, self.quit_btn, "QUIT", self.colors['button_quit'], False)

    def _render_button(self, surface, rect, text, color, is_primary):
        mouse_pos = pygame.mouse.get_pos()
        hover = rect.collidepoint(mouse_pos)

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

        text_surf = self.button_font.render(text, True, (245, 250, 255))
        text_rect = text_surf.get_rect(center=rect.center)
        surface.blit(text_surf, text_rect)

    def _render_hints(self, surface, width, height):
        pulse = (math.sin(self.animation_time * 0.08) + 1) / 2
        if (self.animation_time // 60) % 2 == 0:
            hint_color = (70, 75, 120)
        else:
            hint_color = (100, 105, 150)

        hints = "TAB: switch  |  ENTER: submit  |  ESC: quit"
        hint_surf = self.hint_font.render(hints, True, hint_color)
        surface.blit(hint_surf, hint_surf.get_rect(center=(width // 2, height - 50)))

    def _render_message(self, surface, width, height):
        msg_color = self.colors['error'] if "Invalid" in self.message or "min" in self.message or "exists" in self.message else self.colors['success']
        msg_surf = self.input_font.render(self.message, True, msg_color)
        msg_y = self.password_input_y + self.input_height + 70
        surface.blit(msg_surf, msg_surf.get_rect(center=(width // 2, msg_y)))

    def get_username(self) -> str:
        return self.username

    def is_ready(self) -> bool:
        return not self.running

    def should_quit(self) -> bool:
        return self.want_to_quit
