"""Pause menu overlay with resume, restart, and quit options."""
import pygame
from airwar.utils.fonts import get_cjk_font
import math
from .scene import Scene, PauseAction
from airwar.utils.responsive import ResponsiveHelper
from airwar.ui.menu_background import MenuBackground
from airwar.ui.particles import ParticleSystem
from airwar.ui.effects import EffectsRenderer
from airwar.config.design_tokens import get_design_tokens, SceneColors, SystemUI
from airwar.utils.mouse_interaction import MouseSelectableMixin
from airwar.ui.chamfered_panel import draw_chamfered_panel
from airwar.ui.scene_rendering_utils import SceneRenderingUtils


class PauseScene(Scene, MouseSelectableMixin):
    """Pause scene — overlay menu with resume, restart, and quit options.
    
        Shown as an overlay on top of GameScene when the player presses ESC.
        """
    def __init__(self):
        Scene.__init__(self)
        MouseSelectableMixin.__init__(self)

    def enter(self, **kwargs) -> None:
        self.running = True
        self.result: PauseAction = None
        self.options = ['继续游戏', '返回主菜单', '保存并退出', '不保存退出']
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
        self._particle_system.reset(self._tokens.components.PARTICLE_PARTICLE_ALT_COUNT, 'particle')

        colors = self._tokens.colors
        self.colors = {
            'bg': colors.BACKGROUND_PRIMARY,
            'bg_gradient': colors.BACKGROUND_SECONDARY,
            'overlay': colors.BACKGROUND_OVERLAY,
            'title': colors.TEXT_PRIMARY,
            'title_glow': colors.HUD_AMBER_BRIGHT,
            'selected': colors.HUD_AMBER,
            'selected_glow': colors.HUD_AMBER_BRIGHT,
            'unselected': colors.TEXT_MUTED,
            'hint': colors.TEXT_HINT,
            'particle': colors.PARTICLE_PRIMARY,
        }

        self._init_themed_colors()

    def _init_themed_colors(self) -> None:
        self.themed_colors = {
            'bg': SceneColors.BG_PRIMARY,
            'bg_gradient': SceneColors.BG_PANEL,
            'title': SceneColors.TEXT_PRIMARY,
            'title_glow': SceneColors.GOLD_GLOW,
            'selected': SceneColors.GOLD_PRIMARY,
            'selected_glow': SceneColors.GOLD_BRIGHT,
            'unselected': SceneColors.TEXT_DIM,
            'hint': SceneColors.TEXT_DIM,
            'particle': SceneColors.GOLD_PRIMARY,
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
        elif event.type == pygame.MOUSEMOTION:
            self.handle_mouse_motion(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.handle_mouse_click(event.pos):
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
        self.glow_offset = math.sin(self.animation_time * self._tokens.animation.GLOW_SPEED) * 8

        self._background_renderer._animation_time = self.animation_time
        self._background_renderer.update()

        self._particle_system._animation_time = self.animation_time
        self._particle_system.update(direction=-1)

    def render(self, surface: pygame.Surface) -> None:
        if self.use_themed_style:
            self._background_renderer.render_themed_style(surface, self.themed_colors)
            self._particle_system.render(surface, self.themed_colors['particle'])
        else:
            self._background_renderer.render(surface, self.colors)
            self._particle_system.render(surface, self.colors['particle'])

        width, height = surface.get_size()
        scale = ResponsiveHelper.get_scale_factor(width, height)

        title_y = height // 3 + self.glow_offset * 0.3
        if self.use_themed_style:
            self._draw_themed_title(surface, "已暂停", self.title_font, (width // 2, title_y))
        else:
            SceneRenderingUtils.draw_glow_text(surface, "已暂停", self.title_font,
                (width // 2, title_y), self.colors['title'], self.colors['title_glow'],
                glow_radius=4, glow_offset=1, alpha_divisor=100)

        if self.use_themed_style:
            self._draw_themed_decorations(surface, width, height)
        else:
            SceneRenderingUtils.draw_decorative_lines(
                surface, width // 2, height // 3,
                self.colors['particle'],
            )

        option_spacing = ResponsiveHelper.scale(self.base_option_spacing, scale)
        start_y = height // 2 + ResponsiveHelper.scale(20, scale)

        self.clear_option_rects()
        effective_index = self.get_effective_selected_index(self.selected_index)
        for i, option in enumerate(self.options):
            if self.use_themed_style:
                self._draw_themed_option_box(surface, option, start_y + i * option_spacing, i == effective_index, scale)
            else:
                box_width = ResponsiveHelper.scale(self.base_box_width, scale)
                box_height = ResponsiveHelper.scale(self.base_box_height, scale)
                SceneRenderingUtils.draw_option_box(
                    surface, option, self.option_font,
                    start_y + i * option_spacing, i == effective_index,
                    box_width, box_height, self._option_rects,
                    selected_bg_color=SceneColors.PANEL_OVERLAY_DARK,
                    selected_border_color=self.colors['selected'],
                    unselected_bg_color=SceneColors.PANEL_OVERLAY_LIGHT,
                    unselected_border_color=self.colors['unselected'],
                    selected_glow_color=self.colors['selected_glow'],
                    selected_text_color=self.colors['selected'],
                    unselected_text_color=self.colors['unselected'],
                )

        blink_interval = self._tokens.animation.BLINK_INTERVAL
        blink = (self.animation_time // blink_interval) % 2 == 0
        hint_text = "点击或回车确认" if blink else "               "
        hint_color = SceneColors.TEXT_DIM if self.use_themed_style else self.colors['hint']
        hint = self.hint_font.render(hint_text, True, hint_color)
        surface.blit(hint, hint.get_rect(center=(width // 2, height - ResponsiveHelper.scale(120, scale))))

        controls_color = SceneColors.TEXT_DIM if self.use_themed_style else (60, 60, 100)
        controls = self.desc_font.render("点击或 W/S 选择", True, controls_color)
        surface.blit(controls, controls.get_rect(center=(width // 2, height - ResponsiveHelper.scale(80, scale))))

        esc_hint = self.desc_font.render("ESC 继续游戏", True, controls_color)
        surface.blit(esc_hint, esc_hint.get_rect(center=(width // 2, height - ResponsiveHelper.scale(50, scale))))

    def _draw_themed_title(self, surface: pygame.Surface, text: str, font: pygame.font.Font, pos: tuple) -> None:
        """Draw title in military style with amber glow."""
        for blur, alpha, color in [(4, 20, SceneColors.GOLD_DIM), (2, 35, SceneColors.GOLD_PRIMARY)]:
            glow_surf = font.render(text, True, color)
            glow_surf.set_alpha(alpha)
            for offset_x in range(-blur, blur + 1, 2):
                for offset_y in range(-blur, blur + 1, 2):
                    if offset_x * offset_x + offset_y * offset_y <= blur * blur:
                        glow_rect = glow_surf.get_rect(center=(pos[0] + offset_x, pos[1] + offset_y))
                        surface.blit(glow_surf, glow_rect)

        title = font.render(text, True, SceneColors.GOLD_PRIMARY)
        surface.blit(title, title.get_rect(center=pos))

    def _draw_themed_decorations(self, surface: pygame.Surface, width: int, height: int) -> None:
        """Draw military style decorations."""
        center_x = width // 2

        # Corner brackets
        bracket_size = 20
        bracket_color = SceneColors.BORDER_DIM

        # Top bracket
        pygame.draw.lines(surface, bracket_color, False,
                        [(center_x - 100, height // 3 - 50), (center_x - 100, height // 3 - 50 - bracket_size), (center_x - 100 + bracket_size, height // 3 - 50 - bracket_size)], 2)
        pygame.draw.lines(surface, bracket_color, False,
                        [(center_x + 100, height // 3 - 50), (center_x + 100, height // 3 - 50 - bracket_size), (center_x + 100 - bracket_size, height // 3 - 50 - bracket_size)], 2)

        # Bottom bracket
        pygame.draw.lines(surface, bracket_color, False,
                        [(center_x - 100, height // 3 + 50), (center_x - 100, height // 3 + 50 + bracket_size), (center_x - 100 + bracket_size, height // 3 + 50 + bracket_size)], 2)
        pygame.draw.lines(surface, bracket_color, False,
                        [(center_x + 100, height // 3 + 50), (center_x + 100, height // 3 + 50 + bracket_size), (center_x + 100 - bracket_size, height // 3 + 50 + bracket_size)], 2)

    def _draw_themed_option_box(self, surface: pygame.Surface, text: str, y: int, is_selected: bool, scale: float = 1.0) -> None:
        """Draw option box in military style with chamfered corners."""
        width, height = surface.get_size()
        center_x = width // 2

        box_width = ResponsiveHelper.scale(self.base_box_width, scale)
        box_height = ResponsiveHelper.scale(self.base_box_height, scale)
        box_rect = pygame.Rect(center_x - box_width // 2, y - box_height // 2, box_width, box_height)
        self.append_option_rect(box_rect)

        if is_selected:
            # Draw glow
            draw_chamfered_panel(
                surface,
                box_rect.x - 4, box_rect.y - 4,
                box_rect.width + 8, box_rect.height + 8,
                SceneColors.BG_PANEL,
                SceneColors.GOLD_GLOW,
                SceneColors.GOLD_GLOW,
                10
            )

        # Draw chamfered box
        draw_chamfered_panel(
            surface,
            box_rect.x, box_rect.y,
            box_rect.width, box_rect.height,
            SceneColors.BG_PANEL if is_selected else SceneColors.BG_PANEL_LIGHT,
            SceneColors.GOLD_PRIMARY if is_selected else SceneColors.BORDER_DIM,
            None,
            8
        )

        arrow = ">> " if is_selected else "   "
        option_text = self.option_font.render(f"{arrow}{text}", True,
                                             SceneColors.GOLD_PRIMARY if is_selected else SceneColors.TEXT_DIM)
        text_rect = option_text.get_rect(center=(center_x, y))
        surface.blit(option_text, text_rect)

    def get_result(self) -> PauseAction:
        return self.result

    def is_paused(self) -> bool:
        return self.running
