from enum import Enum
from typing import Optional, Tuple


class ScreenAction(Enum):
    RETURN_TO_MENU = "return_to_menu"
    QUIT = "quit"


class GameOverScreen:
    def __init__(self, window):
        self._window = window
        self._running = False
        self._action: Optional[ScreenAction] = None

    def show(self, score: int, kills: int, username: Optional[str] = None,
             high_score: Optional[int] = None) -> ScreenAction:
        self._running = True
        self._action = None

        screen = self._window.get_surface()
        screen_width = self._window.get_width()
        screen_height = self._window.get_height()

        while self._running:
            quit_event, keydown, resize = self._window.process_events()
            if quit_event:
                self._action = ScreenAction.QUIT
                break

            if resize:
                screen_width, screen_height = resize

            for event in self._window.get_events():
                if event.type == self._get_event_type('QUIT'):
                    self._action = ScreenAction.QUIT
                    self._running = False
                elif event.type == self._get_event_type('VIDEORESIZE'):
                    screen_width, screen_height = event.w, event.h
                elif event.type == self._get_event_type('KEYDOWN'):
                    if event.key in (self._get_key('RETURN'), self._get_key('SPACE')):
                        self._action = ScreenAction.RETURN_TO_MENU
                        self._running = False
                    elif event.key == self._get_key('ESCAPE'):
                        self._action = ScreenAction.QUIT
                        self._running = False

            self._render_game_over(screen, score, kills, username, high_score,
                                   screen_width, screen_height)
            self._window.flip()
            self._window.tick(60)

        return self._action or ScreenAction.QUIT

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

        hint = font_small.render("ENTER to menu | ESC to quit", True, (100, 100, 150))
        surface.blit(hint, hint.get_rect(center=(screen_width // 2, int(500 * scale))))
