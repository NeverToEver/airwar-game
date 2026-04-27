"""Death screen — score summary and continue/quit options."""
import pygame
import math
from .scene import Scene
from airwar.utils.responsive import ResponsiveHelper
from airwar.ui.menu_background import MenuBackground
from airwar.ui.particles import ParticleSystem
from airwar.ui.effects import EffectsRenderer
from airwar.config.design_tokens import get_design_tokens, SceneColors
from airwar.utils.mouse_interaction import MouseSelectableMixin
from airwar.ui.scene_rendering_utils import SceneRenderingUtils


class DeathScene(Scene, MouseSelectableMixin):
    """Death scene — post-death score summary and continue options.
    
        Displays final score, kills, and boss kills. Offers options to
        continue (return to menu) or quit.
        """
    def __init__(self):
        Scene.__init__(self)
        MouseSelectableMixin.__init__(self)

    def enter(self, **kwargs) -> None:
        self.running = True
        self.result = None
        self.score = kwargs.get('score', 0)
        self.kills = kwargs.get('kills', 0)
        self.boss_kills = kwargs.get('boss_kills', 0)
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

    def render(self, surface: pygame.Surface) -> None:
        self._background_renderer.render(surface, self.colors)
        self._particle_system.render(surface, self.colors['particle'])
        self._draw_ripples(surface)

        width, height = surface.get_size()
        scale = ResponsiveHelper.get_scale_factor(width, height)

        title_y = height // 3 + self.glow_offset * 0.3
        SceneRenderingUtils.draw_glow_text(surface, "GAME OVER", self.title_font,
            (width // 2, title_y), self.colors['title'], self.colors['title_glow'],
            glow_radius=5, glow_offset=2, alpha_divisor=80)

        SceneRenderingUtils.draw_decorative_lines(
            surface, width // 2, height // 3,
            self.colors['particle'],
            start_offset_y=-80, line_increment_y=15,
            line_width=250, alpha_base=25, alpha_decrement=6,
        )

        score_text = self.score_font.render(f"SCORE: {self.score}", True, self.colors['score'])
        surface.blit(score_text, score_text.get_rect(center=(width // 2, height // 2 - ResponsiveHelper.scale(45, scale))))

        kills_text = self.score_font.render(f"KILLS: {self.kills}", True, self.colors['kills'])
        surface.blit(kills_text, kills_text.get_rect(center=(width // 2, height // 2 + ResponsiveHelper.scale(5, scale))))

        boss_text = self.desc_font.render(f"BOSS KILLS: {self.boss_kills}", True, self.colors['hint'])
        surface.blit(boss_text, boss_text.get_rect(center=(width // 2, height // 2 + ResponsiveHelper.scale(40, scale))))

        option_spacing = ResponsiveHelper.scale(self.base_option_spacing, scale)
        start_y = height // 2 + ResponsiveHelper.scale(100, scale)
        
        self.clear_option_rects()
        effective_index = self.get_effective_selected_index(self.selected_index)
        colors = self._tokens.colors
        box_width = ResponsiveHelper.scale(self.base_box_width, scale)
        box_height = ResponsiveHelper.scale(self.base_box_height, scale)
        for i, option in enumerate(self.options):
            SceneRenderingUtils.draw_option_box(
                surface, option, self.option_font,
                start_y + i * option_spacing, i == effective_index,
                box_width, box_height, self._option_rects,
                selected_bg_color=colors.BUTTON_SELECTED_BG,
                selected_border_color=self.colors['selected'],
                unselected_bg_color=colors.BUTTON_UNSELECTED_BG,
                unselected_border_color=self.colors['unselected'],
                selected_glow_color=self.colors['selected_glow'],
                selected_text_color=self.colors['selected'],
                unselected_text_color=self.colors['unselected'],
                glow_layers=4, glow_alpha_divisor=40,
            )

        blink_interval = self._tokens.animation.BLINK_INTERVAL
        blink = (self.animation_time // blink_interval) % 2 == 0
        hint_text = "CLICK or ENTER to confirm" if blink else "                       "
        hint = self.hint_font.render(hint_text, True, self.colors['hint'])
        surface.blit(hint, hint.get_rect(center=(width // 2, height - ResponsiveHelper.scale(100, scale))))

        controls = self.desc_font.render("Click or W/S to select", True, SceneColors.DESC_TEXT)
        surface.blit(controls, controls.get_rect(center=(width // 2, height - ResponsiveHelper.scale(70, scale))))

    def get_result(self):
        return self.result

    def is_running(self) -> bool:
        return self.running
