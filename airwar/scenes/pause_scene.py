"""Pause menu overlay with resume, restart, and quit options."""

import pygame

from airwar.config.design_tokens import SceneColors, SceneLayout, get_design_tokens
from airwar.i18n import t
from airwar.ui.effects import EffectsRenderer
from airwar.ui.menu_background import MenuBackground
from airwar.ui.particles import ParticleSystem
from airwar.ui.scene_rendering_utils import SceneRenderingUtils
from airwar.utils.fonts import get_cjk_font
from airwar.utils.mouse_interaction import MouseSelectableMixin
from airwar.utils.responsive import ResponsiveHelper

from .scene import PauseAction, Scene
from .themed_scene_mixin import ThemedSceneMixin


class PauseScene(Scene, MouseSelectableMixin, ThemedSceneMixin):
    """Pause scene — overlay menu with resume, restart, and quit options.

    Shown as an overlay on top of GameScene when the player presses ESC.
    """

    def __init__(self):
        Scene.__init__(self)
        MouseSelectableMixin.__init__(self)

    def enter(self, **kwargs) -> None:
        self.running = True
        self.result: PauseAction | str | None = None
        self.options = [
            t("pause.option.resume"),
            t("pause.option.main_menu"),
            t("pause.option.save_quit"),
            t("pause.option.quit_no_save"),
            t("pause.option.settings"),
        ]
        self.selected_index = 0
        self.animation_time = 0
        self.glow_offset = 0
        self.use_themed_style = True

        self._tokens = get_design_tokens()

        self.base_option_spacing = 70
        self.base_box_width = self._tokens.spacing.BOX_WIDTH
        self.base_box_height = self._tokens.spacing.BOX_HEIGHT

        pygame.font.init()
        self.title_font = get_cjk_font(self._tokens.typography.TITLE_SIZE)
        self.option_font = get_cjk_font(self._tokens.typography.OPTION_SIZE)
        self.hint_font = get_cjk_font(self._tokens.typography.SMALL_SIZE)
        self.desc_font = get_cjk_font(self._tokens.typography.TINY_SIZE)

        self._background_renderer = MenuBackground()
        self._particle_system = ParticleSystem()
        self._effects_renderer = EffectsRenderer()
        self._particle_system.reset(self._tokens.components.PARTICLE_PARTICLE_ALT_COUNT, "particle")

        colors = self._tokens.colors
        self.colors = {
            "bg": colors.BACKGROUND_PRIMARY,
            "bg_gradient": colors.BACKGROUND_SECONDARY,
            "overlay": colors.BACKGROUND_OVERLAY,
            "title": colors.TEXT_PRIMARY,
            "title_glow": colors.HUD_AMBER_BRIGHT,
            "selected": colors.HUD_AMBER,
            "selected_glow": colors.HUD_AMBER_BRIGHT,
            "unselected": colors.TEXT_MUTED,
            "hint": colors.TEXT_HINT,
            "particle": colors.PARTICLE_PRIMARY,
        }

        self._init_themed_colors()

    def _init_themed_colors(self) -> None:
        self.themed_colors = {
            "bg": SceneColors.BG_PRIMARY,
            "bg_gradient": SceneColors.BG_PANEL,
            "title": SceneColors.TEXT_PRIMARY,
            "title_glow": SceneColors.GOLD_GLOW,
            "selected": SceneColors.GOLD_PRIMARY,
            "selected_glow": SceneColors.GOLD_BRIGHT,
            "unselected": SceneColors.TEXT_DIM,
            "hint": SceneColors.TEXT_DIM,
            "particle": SceneColors.GOLD_PRIMARY,
        }

    def exit(self) -> None:
        pass

    def is_running(self) -> bool:
        """Check if the pause scene is still active."""
        return self.running

    def update(self, *args, **kwargs) -> None:
        self.animation_time += 1

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
        elif event.type == pygame.MOUSEMOTION:
            self.handle_mouse_motion(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and self.handle_mouse_click(event.pos):
            self._select_option()

    def _select_option(self) -> None:
        self.running = False
        effective = self.get_effective_selected_index(self.selected_index)
        if effective == 0:
            self.result = PauseAction.RESUME
        elif effective == 1:
            self.result = PauseAction.MAIN_MENU
        elif effective == 2:
            self.result = PauseAction.SAVE_AND_QUIT
        elif effective == 3:
            self.result = PauseAction.QUIT_WITHOUT_SAVING
        elif effective == 4:
            self.result = "settings"

    def render(self, surface: pygame.Surface) -> None:
        if self.use_themed_style:
            self._background_renderer.render_themed_style(surface, self.themed_colors)
            self._particle_system.render(surface, self.themed_colors["particle"])
        else:
            self._background_renderer.render(surface, self.colors)
            self._particle_system.render(surface, self.colors["particle"])

        width, height = surface.get_size()
        scale = ResponsiveHelper.get_scale_factor(width, height)

        title_y = int(height // 3 + self.glow_offset * 0.3)
        if self.use_themed_style:
            self._draw_themed_title(surface, t("pause.title"), self.title_font, (width // 2, title_y))
        else:
            SceneRenderingUtils.draw_glow_text(
                surface,
                t("pause.title"),
                self.title_font,
                (width // 2, title_y),
                self.colors["title"],
                self.colors["title_glow"],
                glow_radius=4,
                glow_offset=1,
                alpha_divisor=100,
            )

        if self.use_themed_style:
            self._draw_themed_decorations(surface, width, height)
        else:
            SceneRenderingUtils.draw_decorative_lines(
                surface,
                width // 2,
                height // 3,
                self.colors["particle"],
            )

        option_spacing = ResponsiveHelper.scale(self.base_option_spacing, scale)
        start_y = height // 2 + ResponsiveHelper.scale(SceneLayout.PAUSE_OPTIONS_OFFSET, scale)

        self.clear_option_rects()
        effective_index = self.get_effective_selected_index(self.selected_index)
        for i, option in enumerate(self.options):
            if self.use_themed_style:
                self._draw_themed_option_box(surface, option, start_y + i * option_spacing, i == effective_index, scale)
            else:
                box_width = ResponsiveHelper.scale(self.base_box_width, scale)
                box_height = ResponsiveHelper.scale(self.base_box_height, scale)
                SceneRenderingUtils.draw_option_box(
                    surface,
                    option,
                    self.option_font,
                    start_y + i * option_spacing,
                    i == effective_index,
                    box_width,
                    box_height,
                    self._option_rects,
                    selected_bg_color=SceneColors.PANEL_OVERLAY_DARK,
                    selected_border_color=self.colors["selected"],
                    unselected_bg_color=SceneColors.PANEL_OVERLAY_LIGHT,
                    unselected_border_color=self.colors["unselected"],
                    selected_glow_color=self.colors["selected_glow"],
                    selected_text_color=self.colors["selected"],
                    unselected_text_color=self.colors["unselected"],
                )

        blink_interval = self._tokens.animation.BLINK_INTERVAL
        blink = (self.animation_time // blink_interval) % 2 == 0
        hint_text = t("pause.hint.confirm") if blink else "               "
        hint_color = SceneColors.TEXT_DIM if self.use_themed_style else self.colors["hint"]
        hint = self.hint_font.render(hint_text, True, hint_color)
        hint_offset = ResponsiveHelper.scale(SceneLayout.PAUSE_HINT_OFFSET, scale)
        surface.blit(hint, hint.get_rect(center=(width // 2, height - hint_offset)))

        controls_color = SceneColors.TEXT_DIM if self.use_themed_style else (60, 60, 100)
        controls = self.desc_font.render(t("pause.hint.navigate"), True, controls_color)
        controls_offset = ResponsiveHelper.scale(SceneLayout.PAUSE_CONTROLS_OFFSET, scale)
        surface.blit(controls, controls.get_rect(center=(width // 2, height - controls_offset)))

        esc_hint = self.desc_font.render(t("pause.hint.esc"), True, controls_color)
        esc_offset = ResponsiveHelper.scale(SceneLayout.PAUSE_ESC_OFFSET, scale)
        surface.blit(esc_hint, esc_hint.get_rect(center=(width // 2, height - esc_offset)))

    def get_result(self) -> PauseAction | str | None:
        return self.result
