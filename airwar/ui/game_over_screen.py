from enum import Enum
from typing import Optional, Tuple
import pygame


class ScreenAction(Enum):
    RETURN_TO_MENU = "return_to_menu"
    QUIT = "quit"


class GameOverScreen:
    def __init__(self, window):
        self._window = window
        self._running = False
        self._action: Optional[ScreenAction] = None
        self._animation_time = 0
        self._button_hover_scale = {}
        self._button_click_animation = {}
        self._buttons = {}
        self._mouse_pos = (0, 0)

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

        scale = screen_width / 800
        font_large = pygame.font.Font(None, int(72 * scale))
        font_medium = pygame.font.Font(None, int(36 * scale))
        font_small = pygame.font.Font(None, int(28 * scale))
        font_button = pygame.font.Font(None, int(32 * scale))

        surface.fill((10, 10, 30))

        title = font_large.render("GAME OVER", True, (255, 80, 80))
        surface.blit(title, title.get_rect(center=(screen_width // 2, int(150 * scale))))

        score_text = font_medium.render(f"SCORE: {score}", True, (255, 255, 255))
        surface.blit(score_text, score_text.get_rect(center=(screen_width // 2, int(280 * scale))))

        kills_text = font_medium.render(f"KILLS: {kills}", True, (200, 200, 100))
        surface.blit(kills_text, kills_text.get_rect(center=(screen_width // 2, int(330 * scale))))

        if username and high_score is not None:
            hs_text = font_small.render(f"HIGH SCORE: {high_score}", True, (100, 255, 150))
            surface.blit(hs_text, hs_text.get_rect(center=(screen_width // 2, int(400 * scale))))

        self._render_button(surface, 'menu', "RETURN TO MAIN MENU", font_button, scale)
        self._render_button(surface, 'quit', "QUIT GAME", font_button, scale)

    def _render_button(self, surface, btn_key: str, text: str, font, scale: float):
        btn_rect = self._buttons[btn_key]
        is_hovered = btn_rect.collidepoint(self._mouse_pos)
        hover_scale = self._button_hover_scale[btn_key]
        click_scale = 1.0 - (self._button_click_animation[btn_key] * 0.08)

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
                base_color = (50, 200, 120)
                glow_color = (0, 255, 150)
                text_color = (255, 255, 255)
            else:
                base_color = (40, 160, 100)
                glow_color = (0, 200, 120)
                text_color = (220, 255, 230)
        else:
            if is_hovered:
                base_color = (200, 80, 80)
                glow_color = (255, 100, 100)
                text_color = (255, 255, 255)
            else:
                base_color = (160, 60, 60)
                glow_color = (200, 80, 80)
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
