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

        pygame.font.init()
        self.title_font = pygame.font.Font(None, 100)
        self.option_font = pygame.font.Font(None, 44)
        self.hint_font = pygame.font.Font(None, 28)
        self.desc_font = pygame.font.Font(None, 24)

        self.colors = {
            'bg': (10, 10, 30),
            'bg_gradient': (20, 20, 60),
            'title': (255, 255, 255),
            'title_glow': (100, 200, 255),
            'selected': (0, 255, 150),
            'selected_glow': (0, 200, 255),
            'unselected': (80, 80, 120),
            'hint': (60, 60, 100),
            'back': (200, 100, 100),
        }

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
        self.animation_time += 1
        self.glow_offset = math.sin(self.animation_time * 0.05) * 10

    def _draw_gradient_background(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        for y in range(height):
            ratio = y / height
            r = int(self.colors['bg'][0] * (1 - ratio) + self.colors['bg_gradient'][0] * ratio)
            g = int(self.colors['bg'][1] * (1 - ratio) + self.colors['bg_gradient'][1] * ratio)
            b = int(self.colors['bg'][2] * (1 - ratio) + self.colors['bg_gradient'][2] * ratio)
            pygame.draw.line(surface, (r, g, b), (0, y), (width, y))

    def _draw_glow_text(self, surface: pygame.Surface, text: str, font: pygame.font.Font,
                        pos: tuple, color: tuple, glow_color: tuple, glow_radius: int = 2) -> None:
        for i in range(glow_radius, 0, -1):
            alpha = int(100 / i)
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

        box_width = 350
        box_height = 55
        box_rect = pygame.Rect(center_x - box_width // 2, y - box_height // 2, box_width, box_height)

        if is_selected:
            glow_color = self.colors['selected_glow']
            for i in range(3, 0, -1):
                glow_rect = box_rect.inflate(i * 4, i * 4)
                glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (*glow_color, 50 // i), glow_surf.get_rect())
                surface.blit(glow_surf, glow_rect)

            pygame.draw.rect(surface, (30, 30, 60), box_rect)
            pygame.draw.rect(surface, self.colors['selected'], box_rect, 2)
        else:
            pygame.draw.rect(surface, (20, 20, 40), box_rect)
            pygame.draw.rect(surface, self.colors['unselected'], box_rect, 1)

        arrow = "> " if is_selected else "  "
        option_text = self.option_font.render(f"{arrow}{text.upper()}", True,
                                             self.colors['selected'] if is_selected else self.colors['unselected'])
        text_rect = option_text.get_rect(center=(center_x - 70, y))
        surface.blit(option_text, text_rect)

        shots_text = self.desc_font.render(f"[ {shots} ]", True,
                                          self.colors['selected'] if is_selected else self.colors['unselected'])
        shots_rect = shots_text.get_rect(center=(center_x + 90, y))
        surface.blit(shots_text, shots_rect)

    def _draw_back_button(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        back_text = self.hint_font.render("ESC to return to login", True, self.colors['back'])
        surface.blit(back_text, back_text.get_rect(center=(width // 2, height - 40)))

    def render(self, surface: pygame.Surface) -> None:
        self._draw_gradient_background(surface)
        width, height = surface.get_size()

        title_y = 120 + self.glow_offset * 0.5
        title_text = "AIR WAR"
        self._draw_glow_text(surface, title_text, self.title_font,
                           (width // 2, title_y), self.colors['title'], self.colors['title_glow'], 4)

        subtitle = self.hint_font.render("ARCADE EDITION", True, (100, 100, 150))
        surface.blit(subtitle, subtitle.get_rect(center=(width // 2, title_y + 45)))

        difficulty_info = {
            'easy': '3 SHOTS',
            'medium': '4 SHOTS',
            'hard': '5 SHOTS'
        }

        start_y = 280
        for i, diff in enumerate(self.difficulty_options):
            self._draw_option_box(surface, diff, start_y + i * 70, i == self.selected_index, difficulty_info[diff])

        start_text = self.hint_font.render("PRESS ENTER TO START", True,
                                           (100, 100, 150) if (self.animation_time // 30) % 2 == 0 else (150, 150, 200))
        surface.blit(start_text, start_text.get_rect(center=(width // 2, height - 80)))

        controls = self.desc_font.render("W/S or UP/DOWN to select", True, (50, 50, 80))
        surface.blit(controls, controls.get_rect(center=(width // 2, height - 55)))

        self._draw_back_button(surface)

    def get_difficulty(self) -> str:
        return self.difficulty

    def is_selection_confirmed(self) -> bool:
        return self.selection_confirmed

    def is_ready(self) -> bool:
        return not self.running

    def should_go_back(self) -> bool:
        return self.back_requested
