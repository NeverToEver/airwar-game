import pygame
import math
from .scene import Scene


class MenuScene(Scene):
    def enter(self, **kwargs) -> None:
        self.running = True
        self.difficulty = 'medium'
        self.difficulty_options = ['easy', 'medium', 'hard']
        self.selected_index = 1
        self.animation_time = 0
        self.glow_offset = 0
        self.selection_confirmed = False
        self.back_requested = False
        self.particles = []
        self.stars = []

        pygame.font.init()
        self.title_font = pygame.font.Font(None, 120)
        self.option_font = pygame.font.Font(None, 52)
        self.hint_font = pygame.font.Font(None, 32)
        self.desc_font = pygame.font.Font(None, 28)

        self._init_particles()
        self._init_stars()

        self.colors = {
            'bg': (8, 8, 25),
            'bg_gradient': (15, 15, 50),
            'title': (255, 255, 255),
            'title_glow': (100, 200, 255),
            'selected': (0, 255, 150),
            'selected_glow': (0, 200, 255),
            'unselected': (90, 90, 130),
            'hint': (70, 70, 110),
            'back': (220, 110, 110),
            'particle': (100, 180, 255),
        }

    def _init_particles(self) -> None:
        import random
        self.particles = []
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
        import random
        self.stars = []
        for _ in range(100):
            self.stars.append({
                'x': random.random(),
                'y': random.random(),
                'size': random.uniform(0.5, 2.0),
                'brightness': random.randint(50, 150),
                'twinkle_speed': random.uniform(0.03, 0.08),
                'twinkle_offset': random.random() * math.pi * 2,
            })

    def exit(self) -> None:
        pass

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.back_requested = True
                self.running = False
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.selected_index = (self.selected_index - 1) % len(self.difficulty_options)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected_index = (self.selected_index + 1) % len(self.difficulty_options)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.difficulty = self.difficulty_options[self.selected_index]
                self.selection_confirmed = True
                self.running = False

    def update(self, *args, **kwargs) -> None:
        import random
        self.animation_time += 1
        self.glow_offset = math.sin(self.animation_time * 0.05) * 12

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
        for y in range(height):
            ratio = y / height
            r = int(self.colors['bg'][0] * (1 - ratio) + self.colors['bg_gradient'][0] * ratio)
            g = int(self.colors['bg'][1] * (1 - ratio) + self.colors['bg_gradient'][1] * ratio)
            b = int(self.colors['bg'][2] * (1 - ratio) + self.colors['bg_gradient'][2] * ratio)
            pygame.draw.line(surface, (r, g, b), (0, y), (width, y))

    def _draw_stars(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        for star in self.stars:
            x = int(star['x'] * width)
            y = int(star['y'] * height)
            twinkle = math.sin(self.animation_time * star['twinkle_speed'] + star['twinkle_offset'])
            brightness = int(star['brightness'] * (0.5 + 0.5 * twinkle))
            pygame.draw.circle(surface, (brightness, brightness, brightness + 30), (x, y), int(star['size']))

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

    def _draw_glow_text(self, surface: pygame.Surface, text: str, font: pygame.font.Font,
                        pos: tuple, color: tuple, glow_color: tuple, glow_radius: int = 2) -> None:
        for i in range(glow_radius, 0, -1):
            alpha = int(120 / i)
            glow_surf = font.render(text, True, glow_color)
            glow_surf.set_alpha(alpha)
            glow_rect = glow_surf.get_rect(center=(pos[0], pos[1] + i))
            surface.blit(glow_surf, glow_rect)

        main_text = font.render(text, True, color)
        surface.blit(main_text, main_text.get_rect(center=pos))

    def _draw_option_box(self, surface: pygame.Surface, text: str, y: int,
                         is_selected: bool, shots: str) -> None:
        width, height = surface.get_size()
        center_x = width // 2

        box_width = 420
        box_height = 70
        box_rect = pygame.Rect(center_x - box_width // 2, y - box_height // 2, box_width, box_height)

        if is_selected:
            glow_color = self.colors['selected_glow']
            for i in range(4, 0, -1):
                glow_rect = box_rect.inflate(i * 5, i * 5)
                glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (*glow_color, 60 // i), glow_surf.get_rect())
                surface.blit(glow_surf, glow_rect)

            pygame.draw.rect(surface, (25, 35, 65), box_rect, border_radius=12)
            pygame.draw.rect(surface, self.colors['selected'], box_rect, 3, border_radius=12)
        else:
            pygame.draw.rect(surface, (18, 20, 40), box_rect, border_radius=12)
            pygame.draw.rect(surface, self.colors['unselected'], box_rect, 2, border_radius=12)

        arrow = ">> " if is_selected else "   "
        option_text = self.option_font.render(f"{arrow}{text.upper()}", True,
                                             self.colors['selected'] if is_selected else self.colors['unselected'])
        text_rect = option_text.get_rect(center=(center_x - 60, y))
        surface.blit(option_text, text_rect)

        shots_text = self.desc_font.render(f"[ {shots} ]", True,
                                          self.colors['selected'] if is_selected else self.colors['unselected'])
        shots_rect = shots_text.get_rect(center=(center_x + 100, y))
        surface.blit(shots_text, shots_rect)

    def _draw_back_button(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        back_text = self.hint_font.render("ESC to return to login", True, self.colors['back'])
        surface.blit(back_text, back_text.get_rect(center=(width // 2, height - 50)))

    def render(self, surface: pygame.Surface) -> None:
        self._draw_gradient_background(surface)
        self._draw_stars(surface)
        self._draw_particles(surface)
        width, height = surface.get_size()

        title_y = 140 + self.glow_offset * 0.5
        title_text = "AIR WAR"
        self._draw_glow_text(surface, title_text, self.title_font,
                           (width // 2, title_y), self.colors['title'], self.colors['title_glow'], 5)

        subtitle = self.hint_font.render("ARCADE EDITION", True, (110, 110, 160))
        surface.blit(subtitle, subtitle.get_rect(center=(width // 2, title_y + 55)))

        difficulty_info = {
            'easy': '3 SHOTS',
            'medium': '4 SHOTS',
            'hard': '5 SHOTS'
        }

        start_y = 340
        for i, diff in enumerate(self.difficulty_options):
            self._draw_option_box(surface, diff, start_y + i * 90, i == self.selected_index, difficulty_info[diff])

        start_text = self.hint_font.render("PRESS ENTER TO START", True,
                                           (110, 110, 160) if (self.animation_time // 30) % 2 == 0 else (160, 160, 210))
        surface.blit(start_text, start_text.get_rect(center=(width // 2, height - 100)))

        controls = self.desc_font.render("W/S or UP/DOWN to select", True, (60, 60, 100))
        surface.blit(controls, controls.get_rect(center=(width // 2, height - 65)))

        self._draw_back_button(surface)

    def get_difficulty(self) -> str:
        return self.difficulty

    def is_selection_confirmed(self) -> bool:
        return self.selection_confirmed

    def is_ready(self) -> bool:
        return not self.running

    def should_go_back(self) -> bool:
        return self.back_requested
