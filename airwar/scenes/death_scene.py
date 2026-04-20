import pygame
import math
from .scene import Scene
from airwar.utils.responsive import ResponsiveHelper


class DeathScene(Scene):
    def enter(self, **kwargs) -> None:
        self.running = True
        self.result = None
        self.score = kwargs.get('score', 0)
        self.kills = kwargs.get('kills', 0)
        self.username = kwargs.get('username', 'Player')
        self.animation_time = 0
        self.glow_offset = 0
        self.particles = []
        self.stars = []
        self.ripples = []

        self.base_option_spacing = 65
        self.base_box_width = 400
        self.base_box_height = 55
        self.base_score_spacing = 30

        pygame.font.init()
        self.title_font = pygame.font.Font(None, 80)
        self.score_font = pygame.font.Font(None, 48)
        self.option_font = pygame.font.Font(None, 42)
        self.hint_font = pygame.font.Font(None, 26)
        self.desc_font = pygame.font.Font(None, 22)

        self.options = ['RETURN TO MAIN MENU', 'QUIT GAME']
        self.selected_index = 0

        self._init_particles()
        self._init_stars()

        self.colors = {
            'bg': (5, 5, 20),
            'bg_gradient': (20, 10, 40),
            'title': (255, 80, 80),
            'title_glow': (255, 50, 50),
            'score': (255, 255, 255),
            'kills': (200, 200, 100),
            'selected': (100, 255, 150),
            'selected_glow': (80, 200, 120),
            'unselected': (80, 80, 110),
            'hint': (60, 60, 100),
            'particle': (255, 100, 100),
        }

    def _init_particles(self) -> None:
        import random
        self.particles = []
        for _ in range(30):
            self.particles.append({
                'x': random.random(),
                'y': random.random(),
                'size': random.uniform(2.0, 4.0),
                'speed': random.uniform(0.3, 0.7),
                'alpha': random.randint(80, 180),
                'pulse_speed': random.uniform(0.03, 0.06),
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
                'brightness': random.randint(40, 120),
                'twinkle_speed': random.uniform(0.02, 0.06),
                'twinkle_offset': random.random() * math.pi * 2,
            })

    def exit(self) -> None:
        pass

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected_index = (self.selected_index - 1) % len(self.options)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected_index = (self.selected_index + 1) % len(self.options)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._select_option()

    def _select_option(self) -> None:
        self.running = False
        if self.selected_index == 0:
            self.result = 'return_to_menu'
        elif self.selected_index == 1:
            self.result = 'quit'

    def update(self, *args, **kwargs) -> None:
        import random
        self.animation_time += 1
        self.glow_offset = math.sin(self.animation_time * 0.03) * 10

        for star in self.stars:
            star['y'] += star.get('speed', 0.005) * 0.003
            if star['y'] > 1:
                star['y'] = 0
                star['x'] = random.random()

        for p in self.particles[:]:
            p['y'] -= p['speed'] * 0.003
            if p['y'] < -0.1:
                p['y'] = 1.1
                p['x'] = random.random()
                p['alpha'] = random.randint(80, 180)

        for ripple in self.ripples[:]:
            ripple['radius'] += 1.5
            ripple['alpha'] -= 3
            if ripple['alpha'] <= 0:
                self.ripples.remove(ripple)

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
            pygame.draw.circle(surface, (brightness, brightness, brightness + 20), (x, y), int(star['size']))

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

    def _draw_ripples(self, surface: pygame.Surface) -> None:
        for ripple in self.ripples:
            ripple_surf = pygame.Surface((int(ripple['radius'] * 2), int(ripple['radius'] * 2)), pygame.SRCALPHA)
            pygame.draw.circle(ripple_surf, (255, 80, 80, ripple['alpha']),
                             (int(ripple['radius']), int(ripple['radius'])),
                             int(ripple['radius']), 2)
            surface.blit(ripple_surf,
                        (ripple['x'] - int(ripple['radius']),
                         ripple['y'] - int(ripple['radius'])))

    def _draw_glow_text(self, surface: pygame.Surface, text: str, font: pygame.font.Font,
                        pos: tuple, color: tuple, glow_color: tuple, glow_radius: int = 3) -> None:
        for i in range(glow_radius, 0, -1):
            alpha = int(80 / i)
            glow_surf = font.render(text, True, glow_color)
            glow_surf.set_alpha(alpha)
            glow_rect = glow_surf.get_rect(center=(pos[0], pos[1] + i * 2))
            surface.blit(glow_surf, glow_rect)

        main_text = font.render(text, True, color)
        surface.blit(main_text, main_text.get_rect(center=pos))

    def _draw_option_box(self, surface: pygame.Surface, text: str, y: int, is_selected: bool, scale: float = 1.0) -> None:
        width, height = surface.get_size()
        center_x = width // 2

        box_width = ResponsiveHelper.scale(self.base_box_width, scale)
        box_height = ResponsiveHelper.scale(self.base_box_height, scale)
        box_rect = pygame.Rect(center_x - box_width // 2, y - box_height // 2, box_width, box_height)

        if is_selected:
            glow_color = self.colors['selected_glow']
            for i in range(5, 0, -1):
                glow_rect = box_rect.inflate(i * 4, i * 4)
                glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (*glow_color, 40 // i), glow_surf.get_rect())
                surface.blit(glow_surf, glow_rect)

            pygame.draw.rect(surface, (30, 25, 45), box_rect, border_radius=12)
            pygame.draw.rect(surface, self.colors['selected'], box_rect, 3, border_radius=12)
        else:
            pygame.draw.rect(surface, (20, 18, 35), box_rect, border_radius=12)
            pygame.draw.rect(surface, self.colors['unselected'], box_rect, 2, border_radius=12)

        arrow = ">> " if is_selected else "   "
        option_text = self.option_font.render(f"{arrow}{text}", True,
                                             self.colors['selected'] if is_selected else self.colors['unselected'])
        text_rect = option_text.get_rect(center=(center_x, y))
        surface.blit(option_text, text_rect)

    def _draw_decorative_lines(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        center_x = width // 2

        for i in range(3):
            offset_y = -80 + i * 15
            line_surf = pygame.Surface((250, 2), pygame.SRCALPHA)
            line_surf.fill((*self.colors['particle'][:3], 25 - i * 6))
            surface.blit(line_surf, (center_x - 125, height // 3 + offset_y))

    def _draw_icon_decoration(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        center_x = width // 2
        title_y = height // 3 + self.glow_offset * 0.3

        color = self.colors['title']
        size = 7
        spacing = 18

        for i in range(-2, 3):
            pulse = math.sin(self.animation_time * 0.06 + i * 0.5)
            alpha = int(130 + 50 * pulse)
            x = center_x + i * spacing
            dot_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(dot_surf, (*color[:3], alpha), (size, size), size)
            surface.blit(dot_surf, (x - size, title_y - size))

    def render(self, surface: pygame.Surface) -> None:
        self._draw_gradient_background(surface)
        self._draw_stars(surface)
        self._draw_particles(surface)
        self._draw_ripples(surface)

        width, height = surface.get_size()
        scale = ResponsiveHelper.get_scale_factor(width, height)

        title_y = height // 3 + self.glow_offset * 0.3
        self._draw_glow_text(surface, "GAME OVER", self.title_font,
                           (width // 2, title_y), self.colors['title'], self.colors['title_glow'], 5)

        self._draw_decorative_lines(surface)
        self._draw_icon_decoration(surface)

        score_text = self.score_font.render(f"SCORE: {self.score}", True, self.colors['score'])
        surface.blit(score_text, score_text.get_rect(center=(width // 2, height // 2 - ResponsiveHelper.scale(30, scale))))

        kills_text = self.score_font.render(f"KILLS: {self.kills}", True, self.colors['kills'])
        surface.blit(kills_text, kills_text.get_rect(center=(width // 2, height // 2 + ResponsiveHelper.scale(20, scale))))

        option_spacing = ResponsiveHelper.scale(self.base_option_spacing, scale)
        start_y = height // 2 + ResponsiveHelper.scale(100, scale)
        for i, option in enumerate(self.options):
            self._draw_option_box(surface, option, start_y + i * option_spacing, i == self.selected_index, scale)

        blink = (self.animation_time // 30) % 2 == 0
        hint_text = "PRESS ENTER TO CONFIRM" if blink else "                "
        hint = self.hint_font.render(hint_text, True, self.colors['hint'])
        surface.blit(hint, hint.get_rect(center=(width // 2, height - ResponsiveHelper.scale(100, scale))))

        controls = self.desc_font.render("W/S or UP/DOWN to select", True, (50, 50, 80))
        surface.blit(controls, controls.get_rect(center=(width // 2, height - ResponsiveHelper.scale(70, scale))))

    def get_result(self):
        return self.result

    def is_running(self) -> bool:
        return self.running
