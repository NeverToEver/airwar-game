import pygame


class DifficultyIndicator:
    def __init__(self, difficulty_manager: 'DifficultyManager'):
        self._manager = difficulty_manager
        self._show_details = False

    def toggle_details(self) -> None:
        self._show_details = not self._show_details

    def set_show_details(self, show: bool) -> None:
        self._show_details = show

    def is_showing_details(self) -> bool:
        return self._show_details

    def render(self, surface: pygame.Surface) -> None:
        params = self._manager.get_current_params()

        bar_width = 200
        bar_height = 20
        bar_x = surface.get_width() - bar_width - 20
        bar_y = 60

        pygame.draw.rect(surface, (50, 50, 80), (bar_x, bar_y, bar_width, bar_height))

        max_mult = self._manager.MAX_MULTIPLIER_GLOBAL
        fill_width = int(bar_width * min(params['multiplier'] / max_mult, 1.0))

        color = self._get_difficulty_color(params['multiplier'])
        pygame.draw.rect(surface, color, (bar_x, bar_y, fill_width, bar_height))

        font = pygame.font.Font(None, 24)
        text = f"DMG: {params['multiplier']:.1f}x"
        text_surf = font.render(text, True, (255, 255, 255))
        surface.blit(text_surf, (bar_x, bar_y - 25))

        if self._show_details:
            self._render_details(surface, params, bar_x, bar_y + bar_height + 10)

    def _get_difficulty_color(self, multiplier: float) -> tuple:
        if multiplier < 2.0:
            return (100, 255, 100)
        elif multiplier < 4.0:
            return (255, 255, 100)
        elif multiplier < 6.0:
            return (255, 150, 50)
        else:
            return (255, 50, 50)

    def _render_details(self, surface, params: dict, x: int, y: int) -> None:
        font = pygame.font.Font(None, 18)
        lines = [
            f"Boss Kills: {params['boss_kills']}",
            f"Speed: {params['speed']:.1f}",
            f"Fire Rate: {params['fire_rate']}",
            f"Aggression: {params['aggression']:.2f}",
            f"Spawn: {params['spawn_rate']}",
            f"Complexity: {params['complexity']}",
        ]

        for i, line in enumerate(lines):
            text_surf = font.render(line, True, (200, 200, 200))
            surface.blit(text_surf, (x, y + i * 18))
