import pygame
from .scene import Scene


class PauseScene(Scene):
    def enter(self, **kwargs) -> None:
        self.running = True
        self.options = ['RESUME', 'MAIN MENU', 'QUIT']
        self.selected_index = 0
        self.paused = True
        self.on_resume = None
        self.on_quit = None

        pygame.font.init()
        self.title_font = pygame.font.Font(None, 80)
        self.option_font = pygame.font.Font(None, 48)
        self.hint_font = pygame.font.Font(None, 28)

        self.colors = {
            'bg': (5, 5, 20, 200),
            'title': (255, 255, 255),
            'selected': (0, 255, 150),
            'unselected': (100, 100, 140),
            'hint': (70, 70, 110),
        }

    def exit(self) -> None:
        pass

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.paused = False
                self.running = False
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.selected_index = (self.selected_index - 1) % len(self.options)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected_index = (self.selected_index + 1) % len(self.options)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._select_option()

    def _select_option(self) -> None:
        if self.selected_index == 0:
            self.paused = False
            self.running = False
            if self.on_resume:
                self.on_resume()
        elif self.selected_index == 1:
            self.paused = False
            self.running = False
            if self.on_quit:
                self.on_quit()
        elif self.selected_index == 2:
            self.paused = False
            self.running = False
            import sys
            sys.exit(0)

    def update(self, *args, **kwargs) -> None:
        pass

    def render(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()

        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill(self.colors['bg'])
        surface.blit(overlay, (0, 0))

        title = self.title_font.render("PAUSED", True, self.colors['title'])
        title_rect = title.get_rect(center=(width // 2, height // 3))
        surface.blit(title, title_rect)

        option_spacing = 80
        start_y = height // 2
        for i, option in enumerate(self.options):
            y = start_y + i * option_spacing
            color = self.colors['selected'] if i == self.selected_index else self.colors['unselected']

            if i == self.selected_index:
                glow_surf = self.option_font.render(f">> {option}", True, color)
                glow_surf.set_alpha(100)
                glow_rect = glow_surf.get_rect(center=(width // 2, y))
                glow_rect.y -= 2
                surface.blit(glow_surf, glow_rect)

            text = self.option_font.render(f">> {option}" if i == self.selected_index else f"   {option}", True, color)
            text_rect = text.get_rect(center=(width // 2, y))
            surface.blit(text, text_rect)

        hint = self.hint_font.render("W/S to select  |  ESC to resume", True, self.colors['hint'])
        surface.blit(hint, hint.get_rect(center=(width // 2, height - 80)))

    def is_paused(self) -> bool:
        return self.paused
