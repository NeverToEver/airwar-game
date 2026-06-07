"""FTL escape phase renderer -- player accelerates upward with particle trail."""

import pygame

from airwar.utils.sprites import draw_glow_circle, draw_player_ship


class FtlAnimationRenderer:
    """Renders the FTL escape cinematic and its exit-to-black transition."""

    FTL_EXIT_FLASH_ALPHA_MAX = 42

    def render(
        self,
        surface: pygame.Surface,
        sequence,
        player,
        progress: float,
    ) -> None:
        """Draw FTL escape phase onto ``surface``."""
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, int(185 * progress)))
        surface.blit(overlay, (0, 0))

        x, y = sequence.get_player_center()
        trail_length = int(160 + 620 * progress)
        trail = pygame.Surface((90, trail_length), pygame.SRCALPHA)
        for i in range(trail_length):
            t = i / max(1, trail_length - 1)
            alpha = int(235 * (1 - t) ** 2)
            width = int(7 + 36 * t)
            pygame.draw.line(
                trail,
                (238, 248, 255, alpha),
                (45 - width // 2, trail_length - i),
                (45 + width // 2, trail_length - i),
                max(1, width),
            )
        surface.blit(trail, (int(x - 45), int(y + player.rect.height // 2)))
        draw_glow_circle(surface, (int(x), int(y + player.rect.height // 2)), 15, (230, 246, 255), 34)
        draw_player_ship(surface, x, y, player.rect.width, player.rect.height)
        self.render_exit_transition(surface, progress)

    def render_exit_transition(self, surface: pygame.Surface, progress: float) -> None:
        """Draw FTL exit streaks/flash/blackout that lead into the next phase."""
        if progress < 0.72:
            return

        sw, sh = surface.get_size()
        t = min(1.0, (progress - 0.72) / 0.28)
        center_x = sw // 2

        streak_alpha = int(118 * max(0.0, 1.0 - t))
        if streak_alpha > 0:
            streaks = pygame.Surface((sw, sh), pygame.SRCALPHA)
            for index in range(17):
                offset = int((index - 8) * (28 + 46 * t))
                x = center_x + offset
                y = int(sh * (0.14 + ((index * 23) % 70) / 100))
                length = int(180 + 390 * t)
                width = max(1, int(5 - 3 * t))
                alpha = int(streak_alpha * (0.45 + 0.55 * (1 - abs(index - 8) / 8)))
                pygame.draw.line(streaks, (210, 238, 255, alpha), (x, y + length), (x, y - length), width)
            surface.blit(streaks, (0, 0))

        flash_strength = max(0.0, 1.0 - abs(t - 0.36) / 0.36)
        flash_alpha = int(self.FTL_EXIT_FLASH_ALPHA_MAX * flash_strength)
        if flash_alpha > 0:
            flash = pygame.Surface((sw, sh), pygame.SRCALPHA)
            flash.fill((126, 188, 214, flash_alpha))
            surface.blit(flash, (0, 0))

        black_t = max(0.0, (t - 0.50) / 0.50)
        black_alpha = int(255 * black_t**0.75)
        if black_alpha > 0:
            blackout = pygame.Surface((sw, sh), pygame.SRCALPHA)
            blackout.fill((0, 0, 0, black_alpha))
            surface.blit(blackout, (0, 0))
