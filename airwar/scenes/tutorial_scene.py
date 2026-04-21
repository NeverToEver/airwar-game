import pygame
import math
import random
from .scene import Scene
from airwar.utils.responsive import ResponsiveHelper


class TutorialScene(Scene):
    def enter(self, **kwargs) -> None:
        self.running = True
        self.want_to_quit = False
        self.animation_time = 0
        self.particles = []
        self.stars = []

        self.base_panel_width = 500
        self.base_panel_height = 580

        pygame.font.init()
        self.title_font = pygame.font.Font(None, 90)
        self.section_font = pygame.font.Font(None, 36)
        self.content_font = pygame.font.Font(None, 28)
        self.hint_font = pygame.font.Font(None, 24)

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
            'section_bg': (20, 28, 55),
            'content_text': (200, 210, 240),
            'hint': (70, 75, 120),
            'particle': (100, 180, 255),
            'highlight': (0, 255, 150),
        }

    def _init_particles(self) -> None:
        for _ in range(40):
            self.particles.append({
                'x': random.random(),
                'y': random.random(),
                'size': random.uniform(1.5, 3.5),
                'speed': random.uniform(0.3, 0.9),
                'alpha': random.randint(80, 180),
                'pulse_speed': random.uniform(0.02, 0.05),
                'pulse_offset': random.random() * math.pi * 2,
            })

    def _init_stars(self) -> None:
        for _ in range(100):
            self.stars.append({
                'x': random.random(),
                'y': random.random(),
                'size': random.uniform(0.5, 2.0),
                'brightness': random.randint(50, 150),
                'twinkle_speed': random.uniform(0.03, 0.08),
                'twinkle_offset': random.random() * math.pi * 2,
            })

    def _reset_rects(self, width, height):
        scale = ResponsiveHelper.get_scale_factor(width, height)

        self.panel_width = ResponsiveHelper.scale(self.base_panel_width, scale)
        self.panel_height = ResponsiveHelper.scale(self.base_panel_height, scale)
        self.panel_x = width // 2 - self.panel_width // 2
        self.panel_y = height // 2 - self.panel_height // 2

        btn_width = ResponsiveHelper.scale(180, scale)
        btn_height = ResponsiveHelper.scale(55, scale)
        btn_gap = ResponsiveHelper.scale(30, scale)
        btn_y = self.panel_y + self.panel_height - ResponsiveHelper.scale(90, scale)
        
        self.back_btn = pygame.Rect(
            width // 2 - btn_width // 2, 
            btn_y, 
            btn_width, 
            btn_height
        )

    def exit(self) -> None:
        pass

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            self._handle_keyboard_event(event)
        elif event.type == pygame.MOUSEMOTION:
            self._handle_mouse_motion(event)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._handle_mouse_event(event)

    def _handle_mouse_motion(self, event) -> None:
        pass

    def _handle_keyboard_event(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_ESCAPE:
            self.want_to_quit = True
            self.running = False
        elif event.key == pygame.K_RETURN:
            self.want_to_quit = True
            self.running = False
        elif event.key == pygame.K_SPACE:
            self.want_to_quit = True
            self.running = False

    def _handle_mouse_event(self, event: pygame.event.Event) -> None:
        mx, my = event.pos
        if self.back_btn.collidepoint(mx, my):
            self.want_to_quit = True
            self.running = False

    def update(self, *args, **kwargs) -> None:
        self.animation_time += 1

        for star in self.stars:
            star['y'] += star.get('speed', 0.008) * 0.008
            if star['y'] > 1:
                star['y'] = 0
                star['x'] = random.random()

        for p in self.particles[:]:
            p['y'] -= p['speed'] * 0.003
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
            pulse = math.sin(self.animation_time * p['pulse_speed'] + p['pulse_offset'])
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

        self._render_panel(surface)
        self._render_title(surface)
        self._render_content(surface)
        self._render_back_button(surface)
        self._render_hints(surface)

    def _render_panel(self, surface) -> None:
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

    def _render_title(self, surface) -> None:
        glow_offset = math.sin(self.animation_time * 0.05) * 3
        title_y = self.panel_y + 45

        for blur, alpha, color in [(6, 18, (50, 120, 180)), (4, 30, (70, 160, 220)), (2, 45, (100, 200, 255))]:
            glow_surf = self.title_font.render("TUTORIAL", True, color)
            glow_surf.set_alpha(alpha)
            for offset_x in range(-blur, blur + 1, 2):
                for offset_y in range(-blur, blur + 1, 2):
                    if offset_x * offset_x + offset_y * offset_y <= blur * blur:
                        glow_rect = glow_surf.get_rect(
                            center=(surface.get_width() // 2 + offset_x, int(title_y + glow_offset) + offset_y))
                        surface.blit(glow_surf, glow_rect)

        title_shadow = self.title_font.render("TUTORIAL", True, (20, 60, 100))
        surface.blit(title_shadow, title_shadow.get_rect(
            center=(surface.get_width() // 2 + 2, int(title_y + glow_offset) + 2)))

        title = self.title_font.render("TUTORIAL", True, self.colors['title'])
        surface.blit(title, title.get_rect(center=(surface.get_width() // 2, int(title_y + glow_offset))))

    def _render_content(self, surface) -> None:
        sections = [
            ("CONTROLS", [
                ("W / UP", "Move Upward"),
                ("S / DOWN", "Move Downward"),
                ("A / LEFT", "Move Left"),
                ("D / RIGHT", "Move Right"),
                ("SPACE", "Fire Weapons"),
            ]),
            ("MOTHER SHIP", [
                ("H (Hold)", "Dock / Enter"),
                ("H (Hold)", "Take Off"),
            ]),
            ("OTHER", [
                ("ESC", "Return to Menu"),
                ("K (Hold)", "Give Up Game"),
            ]),
        ]

        start_y = self.panel_y + 110
        section_gap = 130

        for sec_idx, (section_title, items) in enumerate(sections):
            section_y = start_y + sec_idx * section_gap

            title_surf = self.section_font.render(section_title, True, self.colors['title_glow'])
            surface.blit(title_surf, (self.panel_x + 25, section_y))

            content_rect = pygame.Rect(
                self.panel_x + 25,
                section_y + 35,
                self.panel_width - 50,
                80
            )
            pygame.draw.rect(surface, self.colors['section_bg'], content_rect, border_radius=8)
            border_surf = pygame.Surface((content_rect.width, content_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(border_surf, (*self.colors['panel_border'], 100),
                          border_surf.get_rect(), width=1, border_radius=8)
            surface.blit(border_surf, content_rect.topleft)

            item_y = section_y + 45
            item_gap = 18

            for item_idx, (key, desc) in enumerate(items):
                key_surf = self.content_font.render(key, True, self.colors['highlight'])
                desc_surf = self.content_font.render(desc, True, self.colors['content_text'])
                surface.blit(key_surf, (content_rect.x + 15, item_y + item_idx * item_gap))
                surface.blit(desc_surf, (content_rect.right - 15 - desc_surf.get_width(), item_y + item_idx * item_gap))

    def _render_back_button(self, surface) -> None:
        mouse_pos = pygame.mouse.get_pos()
        hover = self.back_btn.collidepoint(mouse_pos)

        btn_color = (30, 70, 130) if hover else (20, 50, 100)

        if hover:
            for i in range(4, 0, -1):
                expand = i * 3
                glow_surf = pygame.Surface((self.back_btn.width + expand * 2, self.back_btn.height + expand * 2), pygame.SRCALPHA)
                alpha = max(3, 20 // i)
                pygame.draw.rect(glow_surf, (*self.colors['title_glow'], alpha),
                              glow_surf.get_rect(), border_radius=12)
                surface.blit(glow_surf, (self.back_btn.x - expand, self.back_btn.y - expand))

        pygame.draw.rect(surface, btn_color, self.back_btn, border_radius=10)

        border_surf = pygame.Surface((self.back_btn.width, self.back_btn.height), pygame.SRCALPHA)
        pygame.draw.rect(border_surf, (*self.colors['title_glow'], 120 if hover else 100),
                        border_surf.get_rect(), width=2, border_radius=10)
        surface.blit(border_surf, self.back_btn.topleft)

        text_surf = self.section_font.render("BACK", True, (245, 250, 255))
        text_rect = text_surf.get_rect(center=self.back_btn.center)
        surface.blit(text_surf, text_rect)

    def _render_hints(self, surface) -> None:
        width = surface.get_width()
        height = surface.get_height()

        if (self.animation_time // 30) % 2 == 0:
            hint_color = (70, 75, 120)
        else:
            hint_color = (100, 105, 150)

        hints = "ESC / ENTER / SPACE to return"
        hint_surf = self.hint_font.render(hints, True, hint_color)
        surface.blit(hint_surf, hint_surf.get_rect(center=(width // 2, height - 40)))

    def is_ready(self) -> bool:
        return not self.running

    def should_quit(self) -> bool:
        return self.want_to_quit

    def is_running(self) -> bool:
        return self.running
