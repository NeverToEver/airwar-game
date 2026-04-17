import pygame
import math
from .scene import Scene, PauseAction
from airwar.utils.render_cache import SurfaceCache


class PauseScene(Scene):
    def enter(self, **kwargs) -> None:
        self.running = True
        self.result: PauseAction = None
        self.options = ['RESUME', 'MAIN MENU', 'QUIT']
        self.selected_index = 0
        self.animation_time = 0
        self.glow_offset = 0
        self.particles = []
        self.stars = []

        pygame.font.init()
        self.title_font = pygame.font.Font(None, 100)
        self.option_font = pygame.font.Font(None, 48)
        self.hint_font = pygame.font.Font(None, 28)
        self.desc_font = pygame.font.Font(None, 24)

        self._init_particles()
        self._init_stars()

        self.colors = {
            'bg': (8, 8, 25),
            'bg_gradient': (15, 15, 50),
            'overlay': (5, 5, 20, 180),
            'title': (255, 255, 255),
            'title_glow': (100, 200, 255),
            'selected': (0, 255, 150),
            'selected_glow': (0, 200, 255),
            'unselected': (90, 90, 130),
            'hint': (70, 70, 110),
            'particle': (100, 180, 255),
        }

    def _init_particles(self) -> None:
        import random
        self.particles = []
        for _ in range(25):
            self.particles.append({
                'x': random.random(),
                'y': random.random(),
                'size': random.uniform(1.5, 3.0),
                'speed': random.uniform(0.2, 0.6),
                'alpha': random.randint(60, 150),
                'pulse_speed': random.uniform(0.02, 0.05),
                'pulse_offset': random.random() * math.pi * 2,
            })

    def _init_stars(self) -> None:
        import random
        self.stars = []
        for _ in range(80):
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
                self.running = False
                self.result = PauseAction.RESUME
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.selected_index = (self.selected_index - 1) % len(self.options)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected_index = (self.selected_index + 1) % len(self.options)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._select_option()

    def _select_option(self) -> None:
        self.running = False
        if self.selected_index == 0:
            self.result = PauseAction.RESUME
        elif self.selected_index == 1:
            self.result = PauseAction.MAIN_MENU
        elif self.selected_index == 2:
            self.result = PauseAction.QUIT

    def update(self, *args, **kwargs) -> None:
        import random
        self.animation_time += 1
        self.glow_offset = math.sin(self.animation_time * 0.05) * 8

        for star in self.stars:
            star['y'] += star.get('speed', 0.005) * 0.005
            if star['y'] > 1:
                star['y'] = 0
                star['x'] = random.random()

        active_particles = []
        for p in self.particles:
            p['y'] -= p['speed'] * 0.002
            if p['y'] < -0.1:
                p['y'] = 1.1
                p['x'] = random.random()
                p['alpha'] = random.randint(60, 150)
            active_particles.append(p)
        self.particles = active_particles

    def _draw_gradient_background(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        surface.blit(
            SurfaceCache.get_vertical_gradient(width, height, self.colors['bg'], self.colors['bg_gradient']),
            (0, 0),
        )

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
            particle_surf = SurfaceCache.get_particle_glow(size, self.colors['particle'], alpha)
            surface.blit(particle_surf, (x - size * 2, y - size * 2))

    def _draw_glow_text(self, surface: pygame.Surface, text: str, font: pygame.font.Font,
                        pos: tuple, color: tuple, glow_color: tuple, glow_radius: int = 3) -> None:
        for i in range(glow_radius, 0, -1):
            alpha = int(100 / i)
            glow_surf = font.render(text, True, glow_color)
            glow_surf.set_alpha(alpha)
            glow_rect = glow_surf.get_rect(center=(pos[0], pos[1] + i))
            surface.blit(glow_surf, glow_rect)

        main_text = font.render(text, True, color)
        surface.blit(main_text, main_text.get_rect(center=pos))

    def _draw_option_box(self, surface: pygame.Surface, text: str, y: int, is_selected: bool) -> None:
        width, height = surface.get_size()
        center_x = width // 2

        box_width = 350
        box_height = 60
        box_rect = pygame.Rect(center_x - box_width // 2, y - box_height // 2, box_width, box_height)

        if is_selected:
            glow_color = self.colors['selected_glow']
            for i in range(4, 0, -1):
                glow_rect = box_rect.inflate(i * 4, i * 4)
                glow_surf = SurfaceCache.get_rect_glow(
                    glow_rect.width,
                    glow_rect.height,
                    (*glow_color, 50 // i),
                )
                surface.blit(glow_surf, glow_rect)

            surface.blit(
                SurfaceCache.get_rect_fill(box_width, box_height, (25, 35, 65), border_radius=12),
                box_rect.topleft,
            )
            surface.blit(
                SurfaceCache.get_rect_border(box_width, box_height, self.colors['selected'], 3, border_radius=12),
                box_rect.topleft,
            )
        else:
            surface.blit(
                SurfaceCache.get_rect_fill(box_width, box_height, (18, 20, 40), border_radius=12),
                box_rect.topleft,
            )
            surface.blit(
                SurfaceCache.get_rect_border(box_width, box_height, self.colors['unselected'], 2, border_radius=12),
                box_rect.topleft,
            )

        arrow = ">> " if is_selected else "   "
        option_text = self.option_font.render(f"{arrow}{text}", True,
                                             self.colors['selected'] if is_selected else self.colors['unselected'])
        text_rect = option_text.get_rect(center=(center_x, y))
        surface.blit(option_text, text_rect)

    def _draw_decorative_lines(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        center_x = width // 2

        line_color = (*self.colors['selected_glow'], 40)
        for i in range(3):
            offset_y = -100 + i * 20
            line_surf = SurfaceCache.get_line_surface(300, 2, (*self.colors['particle'][:3], 30 - i * 8))
            surface.blit(line_surf, (center_x - 150, height // 3 + offset_y))

    def _draw_icon_decoration(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        center_x = width // 2
        title_y = height // 3 + self.glow_offset * 0.3

        color = self.colors['selected']
        size = 8
        spacing = 20

        for i in range(-2, 3):
            pulse = math.sin(self.animation_time * 0.08 + i * 0.5)
            alpha = int(150 + 50 * pulse)
            x = center_x + i * spacing
            dot_surf = SurfaceCache.get_circle_surface(size, (*color, alpha))
            surface.blit(dot_surf, (x - size, title_y - size))

    def render(self, surface: pygame.Surface) -> None:
        self._draw_gradient_background(surface)
        self._draw_stars(surface)
        self._draw_particles(surface)

        width, height = surface.get_size()

        title_y = height // 3 + self.glow_offset * 0.3
        self._draw_glow_text(surface, "PAUSED", self.title_font,
                           (width // 2, title_y), self.colors['title'], self.colors['title_glow'], 4)

        self._draw_decorative_lines(surface)
        self._draw_icon_decoration(surface)

        option_spacing = 85
        start_y = height // 2 + 30
        for i, option in enumerate(self.options):
            self._draw_option_box(surface, option, start_y + i * option_spacing, i == self.selected_index)

        blink = (self.animation_time // 30) % 2 == 0
        hint_text = "PRESS ENTER TO CONFIRM" if blink else "                "
        hint = self.hint_font.render(hint_text, True, self.colors['hint'])
        surface.blit(hint, hint.get_rect(center=(width // 2, height - 120)))

        controls = self.desc_font.render("W/S or UP/DOWN to select", True, (60, 60, 100))
        surface.blit(controls, controls.get_rect(center=(width // 2, height - 80)))

        esc_hint = self.desc_font.render("ESC to resume", True, (70, 70, 110))
        surface.blit(esc_hint, esc_hint.get_rect(center=(width // 2, height - 50)))

    def get_result(self) -> PauseAction:
        return self.result

    def is_paused(self) -> bool:
        return self.running
