from typing import Optional, List
import pygame
from airwar.ui.buff_stats_panel import BuffStatsPanel


class HUDRenderer:
    def __init__(self):
        pygame.font.init()
        self.hud_font = pygame.font.Font(None, 26)
        self.buff_font = pygame.font.Font(None, 20)
        self.notif_font = pygame.font.Font(None, 32)
        self._buff_stats_panel = BuffStatsPanel()

    def render_hud(self, surface: pygame.Surface, score: int, difficulty: str,
                  player_health: int, player_max_health: int, kills: int,
                  next_threshold: float, cycle_count: int, max_cycles: int,
                  boss_kills: int = 0) -> None:
        score_text = self.hud_font.render(f"SCORE: {score}", True, (255, 255, 255))
        surface.blit(score_text, (15, 15))

        progress = min(100, int(score / next_threshold * 100)) if next_threshold > 0 else 0
        progress_text = self.hud_font.render(f"NEXT: {progress}%", True, (200, 200, 100))
        surface.blit(progress_text, (15, 45))

        cycle_text = self.hud_font.render(f"CYCLE: {cycle_count}/{max_cycles}", True, (150, 150, 200))
        surface.blit(cycle_text, (15, 75))

        diff_text = self.hud_font.render(f"{difficulty.upper()}", True, (200, 200, 100))
        surface.blit(diff_text, (surface.get_width() - 110, 15))

        health_color = (100, 255, 150)
        if player_health < player_max_health * 0.3:
            health_color = (255, 80, 80)
        health_text = self.hud_font.render(f"HP: {player_health}/{player_max_health}", True, health_color)
        surface.blit(health_text, (surface.get_width() - 160, 45))

        kills_text = self.hud_font.render(f"KILLS: {kills}", True, (180, 180, 180))
        surface.blit(kills_text, (surface.get_width() - 120, 75))

        boss_text = self.hud_font.render(f"BOSS: {boss_kills}", True, (255, 100, 100))
        surface.blit(boss_text, (surface.get_width() - 120, 100))

    def render_buffs(self, surface: pygame.Surface, unlocked_buffs: List[str],
                     get_buff_color) -> None:
        if not unlocked_buffs:
            return

        x = 15
        y = surface.get_height() - 50
        shown = set()

        pygame.draw.rect(surface, (20, 20, 40), (x - 8, y - 8, 180, 36), border_radius=8)

        for buff in reversed(list(unlocked_buffs)[:8]):
            if buff in shown:
                continue
            shown.add(buff)

            color = get_buff_color(buff)
            text = self.buff_font.render(buff[:4].upper(), True, color)
            rect = text.get_rect(x=x, y=y)
            pygame.draw.rect(surface, color, rect, 1, border_radius=4)
            surface.blit(text, (x + 4, y + 4))
            x += text.get_width() + 14

            if x > 200:
                break

    def render_notification(self, surface: pygame.Surface, notification: str,
                           timer: int) -> None:
        if timer > 0 and notification:
            alpha = min(255, timer * 4)
            color = (0, 255, 150) if alpha > 150 else (150, 255, 200)
            text = self.notif_font.render(notification, True, color)
            text.set_alpha(alpha)
            x = surface.get_width() // 2 - text.get_width() // 2
            y = 100
            surface.blit(text, (x, y))

    def render_boss_health_bar(self, surface: pygame.Surface, boss) -> None:
        if not boss:
            return

        bar_width = 400
        bar_height = 28
        x = (surface.get_width() - bar_width) // 2
        y = 15

        pygame.draw.rect(surface, (40, 40, 60), (x - 3, y - 3, bar_width + 6, bar_height + 6), border_radius=8)
        pygame.draw.rect(surface, (55, 55, 75), (x, y, bar_width, bar_height), border_radius=6)

        health_ratio = boss.health / boss.max_health
        bar_color = (150, 50, 200) if health_ratio > 0.5 else (180, 100, 50) if health_ratio > 0.25 else (200, 50, 50)
        pygame.draw.rect(surface, bar_color, (x, y, int(bar_width * health_ratio), bar_height), border_radius=6)

        font = pygame.font.Font(None, 24)
        boss_text = font.render("BOSS", True, (255, 255, 255))
        text_rect = boss_text.get_rect(center=(x + bar_width // 2, y + bar_height // 2))
        surface.blit(boss_text, text_rect)

        time_remaining = boss.get_time_remaining()
        time_text = font.render(f"{time_remaining:.1f}s", True, (255, 220, 100))
        time_rect = time_text.get_rect(right=x + bar_width - 8, centery=y + bar_height // 2)
        surface.blit(time_text, time_rect)

        progress = boss.get_survival_progress()
        if progress > 0.7:
            warning_text = font.render("HURRY!", True, (255, 100, 100))
            warning_rect = warning_text.get_rect(left=x + 8, centery=y + bar_height // 2)
            surface.blit(warning_text, warning_rect)

    def render_ripples(self, surface: pygame.Surface, ripples: List[dict]) -> None:
        from airwar.utils.sprites import draw_ripple
        for ripple in ripples:
            pulse = ripple.get('pulse', 0)
            draw_ripple(surface, ripple['x'], ripple['y'], ripple['radius'], ripple['alpha'], pulse)

    def render_buff_stats_panel(
        self,
        surface: pygame.Surface,
        reward_system,
        player
    ) -> None:
        if not reward_system or not player:
            return

        try:
            self._buff_stats_panel.render(
                surface,
                reward_system,
                player,
                surface.get_width(),
                surface.get_height()
            )
        except Exception:
            return
