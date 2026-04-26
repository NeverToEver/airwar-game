"""Game over screen — post-death options and score display."""
from enum import Enum
from typing import Optional, Tuple
import pygame
from airwar.config.design_tokens import get_design_tokens, SceneColors, SystemUI
from airwar.ui.chamfered_panel import draw_chamfered_panel


class ScreenAction(Enum):
    """Screen action enum — user choices on the game over screen."""
    RETURN_TO_MENU = "return_to_menu"
    QUIT = "quit"


class GameOverScreen:
    """Game over screen — post-death UI with score display and action buttons."""
    def __init__(self, window):
        self._window = window
        self._running = False
        self._action: Optional[ScreenAction] = None
        self._animation_time = 0
        self._button_hover_scale = {}
        self._button_click_animation = {}
        self._buttons = {}
        self._mouse_pos = (0, 0)
        self._tokens = get_design_tokens()
        self._use_themed_style = True

    def show(self, score: int, kills: int, username: Optional[str] = None,
             high_score: Optional[int] = None) -> ScreenAction:
        self._running = True
        self._action = None
        self._animation_time = 0
        self._button_hover_scale = {}
        self._button_click_animation = {}
        self._mouse_pos = (0, 0)

        screen = self._window.get_surface()
        screen_width = self._window.get_width()
        screen_height = self._window.get_height()

        self._init_buttons(screen_width, screen_height)

        while self._running:
            quit_event, keydown, resize = self._window.process_events()
            if quit_event:
                self._action = ScreenAction.QUIT
                break

            if resize:
                screen_width, screen_height = resize
                self._init_buttons(screen_width, screen_height)

            for event in self._window.get_events():
                if event.type == pygame.QUIT:
                    self._action = ScreenAction.QUIT
                    self._running = False
                elif event.type == pygame.VIDEORESIZE:
                    screen_width, screen_height = event.w, event.h
                    self._init_buttons(screen_width, screen_height)
                elif event.type == pygame.MOUSEMOTION:
                    self._mouse_pos = event.pos
                    self._update_button_hover_states()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self._handle_button_click(event.pos)
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self._action = ScreenAction.RETURN_TO_MENU
                        self._running = False
                    elif event.key == pygame.K_ESCAPE:
                        self._action = ScreenAction.QUIT
                        self._running = False

            self._animation_time += 1
            self._update_click_animations()
            self._render_game_over(screen, score, kills, username, high_score,
                                   screen_width, screen_height)
            self._window.flip()
            self._window.tick(60)

        return self._action or ScreenAction.QUIT

    def _init_buttons(self, screen_width: int, screen_height: int):
        scale = screen_width / 800
        button_width = int(280 * scale)
        button_height = int(60 * scale)
        center_x = screen_width // 2
        menu_button_y = int(480 * scale)
        quit_button_y = int(560 * scale)

        self._buttons = {
            'menu': pygame.Rect(center_x - button_width // 2, menu_button_y, button_width, button_height),
            'quit': pygame.Rect(center_x - button_width // 2, quit_button_y, button_width, button_height)
        }

        for btn_key in self._buttons:
            if btn_key not in self._button_hover_scale:
                self._button_hover_scale[btn_key] = 1.0
            if btn_key not in self._button_click_animation:
                self._button_click_animation[btn_key] = 0.0

    def _update_button_hover_states(self):
        for btn_key, btn_rect in self._buttons.items():
            if btn_rect.collidepoint(self._mouse_pos):
                target_scale = 1.05
            else:
                target_scale = 1.0

            current_scale = self._button_hover_scale[btn_key]
            self._button_hover_scale[btn_key] = current_scale + (target_scale - current_scale) * 0.15

    def _update_click_animations(self):
        for btn_key in self._button_click_animation:
            if self._button_click_animation[btn_key] > 0:
                self._button_click_animation[btn_key] *= 0.85
                if self._button_click_animation[btn_key] < 0.01:
                    self._button_click_animation[btn_key] = 0

    def _handle_button_click(self, pos: tuple):
        for btn_key, btn_rect in self._buttons.items():
            if btn_rect.collidepoint(pos):
                self._button_click_animation[btn_key] = 1.0

                if btn_key == 'menu':
                    self._action = ScreenAction.RETURN_TO_MENU
                    self._running = False
                elif btn_key == 'quit':
                    self._action = ScreenAction.QUIT
                    self._running = False
                break

    def _get_event_type(self, name: str):
        import pygame
        return getattr(pygame, name, None)

    def _get_key(self, name: str):
        import pygame
        return getattr(pygame, f'K_{name}', None)

    def _render_game_over(self, surface, score: int, kills: int,
                         username: Optional[str], high_score: Optional[int],
                         screen_width: int, screen_height: int) -> None:
        import pygame
        pygame.font.init()

        tokens = self._tokens

        scale = screen_width / 800
        font_large = pygame.font.Font(None, int(tokens.typography.HEADING_SIZE * scale))
        font_medium = pygame.font.Font(None, int(tokens.typography.BODY_SIZE * scale))
        font_small = pygame.font.Font(None, int(tokens.typography.CAPTION_SIZE * scale))
        font_button = pygame.font.Font(None, int(tokens.typography.SMALL_SIZE * scale))

        if self._use_themed_style:
            # Military style background
            surface.fill(SceneColors.BG_PRIMARY)

            # Draw grid overlay
            spacing = SystemUI.GRID_SPACING
            grid_color = (*SceneColors.GOLD_PRIMARY[:3], SystemUI.GRID_ALPHA)
            for x in range(0, screen_width, spacing):
                pygame.draw.line(surface, grid_color, (x, 0), (x, screen_height))
            for y in range(0, screen_height, spacing):
                pygame.draw.line(surface, grid_color, (0, y), (screen_width, y))

            # Military style title with glow
            title_text = "GAME OVER"
            for blur, alpha, color in [(4, 20, SceneColors.DANGER_RED_DIM), (2, 35, SceneColors.DANGER_RED)]:
                glow_surf = font_large.render(title_text, True, color)
                glow_surf.set_alpha(alpha)
                for offset_x in range(-blur, blur + 1, 2):
                    for offset_y in range(-blur, blur + 1, 2):
                        if offset_x * offset_x + offset_y * offset_y <= blur * blur:
                            glow_rect = glow_surf.get_rect(center=(screen_width // 2 + offset_x, int(150 * scale) + offset_y))
                            surface.blit(glow_surf, glow_rect)

            title = font_large.render(title_text, True, SceneColors.DANGER_RED)
            surface.blit(title, title.get_rect(center=(screen_width // 2, int(150 * scale))))

            # Military style stats
            score_text = font_medium.render(f"SCORE: {score:,}", True, SceneColors.GOLD_PRIMARY)
            surface.blit(score_text, score_text.get_rect(center=(screen_width // 2, int(280 * scale))))

            kills_text = font_medium.render(f"KILLS: {kills}", True, SceneColors.TEXT_PRIMARY)
            surface.blit(kills_text, kills_text.get_rect(center=(screen_width // 2, int(330 * scale))))

            if username and high_score is not None:
                hs_text = font_small.render(f"HIGH SCORE: {high_score}", True, SceneColors.FOREST_GREEN)
                surface.blit(hs_text, hs_text.get_rect(center=(screen_width // 2, int(400 * scale))))

            self._render_themed_button(surface, 'menu', "RETURN TO MAIN MENU", font_button, scale)
            self._render_themed_button(surface, 'quit', "QUIT GAME", font_button, scale)
        else:
            # Original style
            colors = tokens.colors
            surface.fill(colors.BACKGROUND_PRIMARY)

            title = font_large.render("GAME OVER", True, colors.HEALTH_DANGER)
            surface.blit(title, title.get_rect(center=(screen_width // 2, int(150 * scale))))

            score_text = font_medium.render(f"SCORE: {score}", True, colors.TEXT_PRIMARY)
            surface.blit(score_text, score_text.get_rect(center=(screen_width // 2, int(280 * scale))))

            kills_text = font_medium.render(f"KILLS: {kills}", True, colors.PROGRESS_COLOR)
            surface.blit(kills_text, kills_text.get_rect(center=(screen_width // 2, int(330 * scale))))

            if username and high_score is not None:
                hs_text = font_small.render(f"HIGH SCORE: {high_score}", True, colors.SUCCESS)
                surface.blit(hs_text, hs_text.get_rect(center=(screen_width // 2, int(400 * scale))))

            self._render_button(surface, 'menu', "RETURN TO MAIN MENU", font_button, scale)
            self._render_button(surface, 'quit', "QUIT GAME", font_button, scale)

    def _render_button(self, surface, btn_key: str, text: str, font, scale: float):
        colors = self._tokens.colors
        btn_rect = self._buttons[btn_key]
        is_hovered = btn_rect.collidepoint(self._mouse_pos)
        hover_scale = self._button_hover_scale[btn_key]
        click_scale = 1.0 - (self._button_click_animation[btn_key] * self._tokens.animation.CLICK_SCALE_FACTOR)

        final_scale = hover_scale * click_scale
        scaled_width = int(btn_rect.width * final_scale)
        scaled_height = int(btn_rect.height * final_scale)

        center_x, center_y = btn_rect.centerx, btn_rect.centery
        scaled_rect = pygame.Rect(
            center_x - scaled_width // 2,
            center_y - scaled_height // 2,
            scaled_width,
            scaled_height
        )

        if btn_key == 'menu':
            if is_hovered:
                base_color = colors.BUTTON_SELECTED_PRIMARY
                glow_color = colors.BUTTON_SELECTED_GLOW
                text_color = colors.BUTTON_SELECTED_TEXT
            else:
                base_color = colors.BUTTON_UNSELECTED_PRIMARY
                glow_color = colors.BUTTON_UNSELECTED_GLOW
                text_color = colors.BUTTON_UNSELECTED_TEXT
        else:
            if is_hovered:
                base_color = colors.DANGER_BUTTON_SELECTED_PRIMARY
                glow_color = colors.DANGER_BUTTON_SELECTED_GLOW
                text_color = colors.BUTTON_SELECTED_TEXT
            else:
                base_color = colors.DANGER_BUTTON_UNSELECTED_PRIMARY
                glow_color = colors.DANGER_BUTTON_UNSELECTED_GLOW
                text_color = (255, 220, 220)

        if is_hovered or self._button_click_animation[btn_key] > 0:
            for i in range(4, 0, -1):
                expand = i * 4
                glow_rect = scaled_rect.inflate(expand * 2, expand * 2)
                alpha = max(5, 40 // i)
                glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (*glow_color, alpha),
                               glow_surf.get_rect(), border_radius=12)
                surface.blit(glow_surf, glow_rect)

        pygame.draw.rect(surface, base_color, scaled_rect, border_radius=10)

        border_surf = pygame.Surface((scaled_rect.width, scaled_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(border_surf, (*glow_color, 180),
                        border_surf.get_rect(), width=2, border_radius=10)
        surface.blit(border_surf, scaled_rect.topleft)

        text_surf = font.render(text, True, text_color)
        text_rect = text_surf.get_rect(center=scaled_rect.center)
        surface.blit(text_surf, text_rect)

    def _render_themed_button(self, surface, btn_key: str, text: str, font, scale: float):
        """Render button in military style with chamfered corners."""
        btn_rect = self._buttons[btn_key]
        is_hovered = btn_rect.collidepoint(self._mouse_pos)
        hover_scale = self._button_hover_scale[btn_key]
        click_scale = 1.0 - (self._button_click_animation[btn_key] * self._tokens.animation.CLICK_SCALE_FACTOR)

        final_scale = hover_scale * click_scale
        scaled_width = int(btn_rect.width * final_scale)
        scaled_height = int(btn_rect.height * final_scale)

        center_x, center_y = btn_rect.centerx, btn_rect.centery
        scaled_rect = pygame.Rect(
            center_x - scaled_width // 2,
            center_y - scaled_height // 2,
            scaled_width,
            scaled_height
        )

        if btn_key == 'menu':
            if is_hovered:
                base_color = SceneColors.FOREST_GREEN
                border_color = SceneColors.GOLD_PRIMARY
                text_color = SceneColors.TEXT_BRIGHT
            else:
                base_color = SceneColors.BG_PANEL_LIGHT
                border_color = SceneColors.BORDER_DIM
                text_color = SceneColors.TEXT_PRIMARY
        else:
            if is_hovered:
                base_color = SceneColors.DANGER_RED_DIM
                border_color = SceneColors.DANGER_RED
                text_color = SceneColors.TEXT_BRIGHT
            else:
                base_color = SceneColors.BG_PANEL_LIGHT
                border_color = SceneColors.BORDER_DIM
                text_color = SceneColors.TEXT_PRIMARY

        # Draw glow for hovered
        if is_hovered or self._button_click_animation[btn_key] > 0:
            draw_chamfered_panel(
                surface,
                scaled_rect.x - 4, scaled_rect.y - 4,
                scaled_rect.width + 8, scaled_rect.height + 8,
                SceneColors.BG_PANEL,
                SceneColors.GOLD_GLOW if btn_key == 'menu' else SceneColors.DANGER_RED,
                SceneColors.GOLD_GLOW if btn_key == 'menu' else SceneColors.DANGER_RED,
                10
            )

        # Draw chamfered button
        draw_chamfered_panel(
            surface,
            scaled_rect.x, scaled_rect.y,
            scaled_rect.width, scaled_rect.height,
            base_color,
            border_color,
            None,
            8
        )

        text_surf = font.render(text, True, text_color)
        text_rect = text_surf.get_rect(center=scaled_rect.center)
        surface.blit(text_surf, text_rect)
