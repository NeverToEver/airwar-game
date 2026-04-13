import pygame
from .scene import Scene


class PauseScene(Scene):
    def __init__(self):
        self.on_resume = None
        self.on_quit = None

    def enter(self, **kwargs) -> None:
        self.running = True
        self.selected_index = 0
        self.options = ['RESUME', 'MAIN MENU']
        self.animation_time = 0

        pygame.font.init()
        self.title_font = pygame.font.Font(None, 72)
        self.option_font = pygame.font.Font(None, 44)
        self.hint_font = pygame.font.Font(None, 28)

        self.colors = {
            'bg': (10, 10, 30, 200),
            'selected': (0, 255, 150),
            'unselected': (80, 80, 120),
            'text': (255, 255, 255),
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
            elif event.key == pygame.K_ESCAPE:
                self.running = False
                if self.on_resume:
                    self.on_resume()

    def _select_option(self) -> None:
        if self.selected_index == 0:
            self.running = False
            if self.on_resume:
                self.on_resume()
        else:
            self.running = False
            if self.on_quit:
                self.on_quit()

    def update(self, *args, **kwargs) -> None:
        self.animation_time += 1

    def render(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()

        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((10, 10, 30, 180))
        surface.blit(overlay, (0, 0))

        title = self.title_font.render("PAUSED", True, self.colors['text'])
        surface.blit(title, title.get_rect(center=(width // 2, height // 3)))

        start_y = height // 2
        for i, option in enumerate(self.options):
            is_selected = i == self.selected_index
            color = self.colors['selected'] if is_selected else self.colors['unselected']
            arrow = "> " if is_selected else "  "
            text = self.option_font.render(f"{arrow}{option}", True, color)
            surface.blit(text, text.get_rect(center=(width // 2, start_y + i * 60)))

        hint = self.hint_font.render("W/S or UP/DOWN to select, ENTER to confirm", True, (60, 60, 100))
        surface.blit(hint, hint.get_rect(center=(width // 2, start_y + 150)))

        esc_hint = self.hint_font.render("Press ESC to resume", True, (80, 80, 120))
        surface.blit(esc_hint, esc_hint.get_rect(center=(width // 2, height - 50)))

    def is_paused(self) -> bool:
        return self.running
