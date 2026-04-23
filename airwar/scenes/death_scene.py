import pygame
import math
from .scene import Scene
from airwar.utils.responsive import ResponsiveHelper
from airwar.ui.menu_background import MenuBackground
from airwar.ui.particles import ParticleSystem
from airwar.ui.effects import EffectsRenderer
from airwar.config.design_tokens import get_design_tokens
from airwar.utils.mouse_interaction import MouseSelectableMixin


class DeathScene(Scene, MouseSelectableMixin):
    def __init__(self):
        Scene.__init__(self)
        MouseSelectableMixin.__init__(self)

    def enter(self, **kwargs) -> None:
        self.running = True
        self.result = None
        self.score = kwargs.get('score', 0)
        self.kills = kwargs.get('kills', 0)
        self.username = kwargs.get('username', 'Player')
        self.animation_time = 0
        self.glow_offset = 0
        self.ripples = []

        self._tokens = get_design_tokens()

        self.base_option_spacing = 65
        self.base_box_width = self._tokens.spacing.BOX_WIDTH
        self.base_box_height = 55
        self.base_score_spacing = 30

        pygame.font.init()
        tokens = self._tokens
        self.title_font = pygame.font.Font(None, tokens.typography.SUBHEADING_SIZE)
        self.score_font = pygame.font.Font(None, tokens.typography.OPTION_SIZE)
        self.option_font = pygame.font.Font(None, tokens.typography.BODY_SIZE)
        self.hint_font = pygame.font.Font(None, tokens.typography.HUD_SIZE)
        self.desc_font = pygame.font.Font(None, tokens.typography.TINY_SIZE)

        self.options = ['RETURN TO MAIN MENU', 'QUIT GAME']
        self.selected_index = 0

        self._background_renderer = MenuBackground()
        self._particle_system = ParticleSystem()
        self._effects_renderer = EffectsRenderer()
        self._particle_system.reset(tokens.components.PARTICLE_PARTICLE_ALT_COUNT, 'particle')

        self._init_colors()

    def _init_colors(self) -> None:
        colors = self._tokens.colors
        self.colors = {
            'bg': colors.BACKGROUND_PRIMARY,
            'bg_gradient': colors.BACKGROUND_SECONDARY,
            'title': colors.HEALTH_DANGER,
            'title_glow': colors.HEALTH_DANGER,
            'score': colors.TEXT_PRIMARY,
            'kills': colors.PROGRESS_COLOR,
            'selected': colors.BUTTON_SELECTED_PRIMARY,
            'selected_glow': colors.BUTTON_SELECTED_GLOW,
            'unselected': colors.TEXT_MUTED,
            'hint': colors.TEXT_HINT,
            'particle': colors.PARTICLE_ALT,
        }

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
        elif event.type == pygame.MOUSEMOTION:
            self.handle_mouse_motion(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.handle_mouse_click(event.pos):
                self._select_option()

    def _select_option(self) -> None:
        self.running = False
        if self.selected_index == 0:
            self.result = 'return_to_menu'
        elif self.selected_index == 1:
            self.result = 'quit'

    def update(self, *args, **kwargs) -> None:
        self.animation_time += 1
        self.glow_offset = math.sin(self.animation_time * self._tokens.animation.GLOW_SPEED * 0.6) * 10

        self._background_renderer._animation_time = self.animation_time
        self._background_renderer.update()

        self._particle_system._animation_time = self.animation_time
        self._particle_system.update(direction=-1)

        for ripple in self.ripples[:]:
            ripple['radius'] += 1.5
            ripple['alpha'] -= 3
            if ripple['alpha'] <= 0:
                self.ripples.remove(ripple)

    def _draw_ripples(self, surface: pygame.Surface) -> None:
        colors = self._tokens.colors
        for ripple in self.ripples:
            ripple_surf = pygame.Surface((int(ripple['radius'] * 2), int(ripple['radius'] * 2)), pygame.SRCALPHA)
            pygame.draw.circle(ripple_surf, (*colors.HEALTH_DANGER, ripple['alpha']),
                             (int(ripple['radius']), int(ripple['radius'])),
                             int(ripple['radius']), 2)
            surface.blit(ripple_surf,
                        (ripple['x'] - int(ripple['radius']),
                         ripple['y'] - int(ripple['radius'])))

    def _draw_glow_text(self, surface: pygame.Surface, text: str, font: pygame.font.Font,
                        pos: tuple, color: tuple, glow_color: tuple, glow_radius: int = None) -> None:
        if glow_radius is None:
            glow_radius = self._tokens.animation.GLOW_RADIUS_TITLE

        for i in range(glow_radius, 0, -1):
            alpha = int(80 / i)
            glow_surf = font.render(text, True, glow_color)
            glow_surf.set_alpha(alpha)
            glow_rect = glow_surf.get_rect(center=(pos[0], pos[1] + i * 2))
            surface.blit(glow_surf, glow_rect)

        main_text = font.render(text, True, color)
        surface.blit(main_text, main_text.get_rect(center=pos))

    def _draw_option_box(self, surface: pygame.Surface, text: str, y: int, is_selected: bool, scale: float = 1.0) -> None:
        colors = self._tokens.colors
        width, height = surface.get_size()
        center_x = width // 2

        box_width = ResponsiveHelper.scale(self.base_box_width, scale)
        box_height = ResponsiveHelper.scale(self.base_box_height, scale)
        box_rect = pygame.Rect(center_x - box_width // 2, y - box_height // 2, box_width, box_height)
        self.append_option_rect(box_rect)

        if is_selected:
            glow_color = self.colors['selected_glow']
            for i in range(5, 0, -1):
                glow_rect = box_rect.inflate(i * 4, i * 4)
                glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (*glow_color, 40 // i), glow_surf.get_rect())
                surface.blit(glow_surf, glow_rect)

            pygame.draw.rect(surface, colors.BUTTON_SELECTED_BG, box_rect, border_radius=12)
            pygame.draw.rect(surface, self.colors['selected'], box_rect, 3, border_radius=12)
        else:
            pygame.draw.rect(surface, colors.BUTTON_UNSELECTED_BG, box_rect, border_radius=12)
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
        self._background_renderer.render(surface, self.colors)
        self._particle_system.render(surface, self.colors['particle'])
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
        
        self.clear_option_rects()
        effective_index = self.get_effective_selected_index(self.selected_index)
        for i, option in enumerate(self.options):
            self._draw_option_box(surface, option, start_y + i * option_spacing, i == effective_index, scale)

        blink_interval = self._tokens.animation.BLINK_INTERVAL
        blink = (self.animation_time // blink_interval) % 2 == 0
        hint_text = "CLICK or ENTER to confirm" if blink else "                       "
        hint = self.hint_font.render(hint_text, True, self.colors['hint'])
        surface.blit(hint, hint.get_rect(center=(width // 2, height - ResponsiveHelper.scale(100, scale))))

        controls = self.desc_font.render("Click or W/S to select", True, (50, 50, 80))
        surface.blit(controls, controls.get_rect(center=(width // 2, height - ResponsiveHelper.scale(70, scale))))

    def get_result(self):
        return self.result

    def is_running(self) -> bool:
        return self.running
