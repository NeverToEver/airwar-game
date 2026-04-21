import pygame
import math
from .scene import Scene, PauseAction
from airwar.utils.responsive import ResponsiveHelper
from airwar.scenes.ui.background import BackgroundRenderer
from airwar.scenes.ui.particles import ParticleSystem
from airwar.scenes.ui.effects import EffectsRenderer


class PauseScene(Scene):
    def enter(self, **kwargs) -> None:
        self.running = True
        self.result: PauseAction = None
        self.options = ['RESUME', 'MAIN MENU', 'SAVE AND QUIT', 'QUIT WITHOUT SAVING']
        self.selected_index = 0
        self.animation_time = 0
        self.glow_offset = 0

        self.base_option_spacing = 70
        self.base_box_width = 350
        self.base_box_height = 60

        pygame.font.init()
        self.title_font = pygame.font.Font(None, 100)
        self.option_font = pygame.font.Font(None, 48)
        self.hint_font = pygame.font.Font(None, 26)
        self.desc_font = pygame.font.Font(None, 24)

        self._background_renderer = BackgroundRenderer()
        self._particle_system = ParticleSystem()
        self._effects_renderer = EffectsRenderer()
        self._particle_system.reset(25, 'particle')

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
            self.result = PauseAction.SAVE_AND_QUIT
        elif self.selected_index == 3:
            self.result = PauseAction.QUIT_WITHOUT_SAVING

    def update(self, *args, **kwargs) -> None:
        self.animation_time += 1
        self.glow_offset = math.sin(self.animation_time * 0.05) * 8

        self._background_renderer._animation_time = self.animation_time
        self._background_renderer.update()

        self._particle_system._animation_time = self.animation_time
        self._particle_system.update(direction=-1)

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

    def _draw_option_box(self, surface: pygame.Surface, text: str, y: int, is_selected: bool, scale: float = 1.0) -> None:
        width, height = surface.get_size()
        center_x = width // 2

        box_width = ResponsiveHelper.scale(self.base_box_width, scale)
        box_height = ResponsiveHelper.scale(self.base_box_height, scale)
        box_rect = pygame.Rect(center_x - box_width // 2, y - box_height // 2, box_width, box_height)

        if is_selected:
            glow_color = self.colors['selected_glow']
            for i in range(4, 0, -1):
                glow_rect = box_rect.inflate(i * 4, i * 4)
                glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (*glow_color, 50 // i), glow_surf.get_rect())
                surface.blit(glow_surf, glow_rect)

            pygame.draw.rect(surface, (25, 35, 65), box_rect, border_radius=12)
            pygame.draw.rect(surface, self.colors['selected'], box_rect, 3, border_radius=12)
        else:
            pygame.draw.rect(surface, (18, 20, 40), box_rect, border_radius=12)
            pygame.draw.rect(surface, self.colors['unselected'], box_rect, 2, border_radius=12)

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
            line_surf = pygame.Surface((300, 2), pygame.SRCALPHA)
            line_surf.fill((*self.colors['particle'][:3], 30 - i * 8))
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
            dot_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(dot_surf, (*color, alpha), (size, size), size)
            surface.blit(dot_surf, (x - size, title_y - size))

    def render(self, surface: pygame.Surface) -> None:
        self._background_renderer.render(surface, self.colors)
        self._particle_system.render(surface, self.colors['particle'])

        width, height = surface.get_size()
        scale = ResponsiveHelper.get_scale_factor(width, height)

        title_y = height // 3 + self.glow_offset * 0.3
        self._draw_glow_text(surface, "PAUSED", self.title_font,
                           (width // 2, title_y), self.colors['title'], self.colors['title_glow'], 4)

        self._draw_decorative_lines(surface)
        self._draw_icon_decoration(surface)

        option_spacing = ResponsiveHelper.scale(self.base_option_spacing, scale)
        start_y = height // 2 + ResponsiveHelper.scale(20, scale)
        for i, option in enumerate(self.options):
            self._draw_option_box(surface, option, start_y + i * option_spacing, i == self.selected_index, scale)

        blink = (self.animation_time // 30) % 2 == 0
        hint_text = "PRESS ENTER TO CONFIRM" if blink else "                "
        hint = self.hint_font.render(hint_text, True, self.colors['hint'])
        surface.blit(hint, hint.get_rect(center=(width // 2, height - ResponsiveHelper.scale(120, scale))))

        controls = self.desc_font.render("W/S or UP/DOWN to select", True, (60, 60, 100))
        surface.blit(controls, controls.get_rect(center=(width // 2, height - ResponsiveHelper.scale(80, scale))))

        esc_hint = self.desc_font.render("ESC to resume", True, (70, 70, 110))
        surface.blit(esc_hint, esc_hint.get_rect(center=(width // 2, height - ResponsiveHelper.scale(50, scale))))

    def get_result(self) -> PauseAction:
        return self.result

    def is_paused(self) -> bool:
        return self.running
