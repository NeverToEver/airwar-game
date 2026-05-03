"""HUD renderer — score, health bar, boss HP, buff stats panel."""
import math
from typing import List
import pygame
from airwar.utils.fonts import get_cjk_font
from ...ui.buff_stats_panel import BuffStatsPanel, AttackModePanel
from ...ui.chamfered_panel import draw_chamfered_panel
from ...ui.segmented_bar import BossHealthBar
from ...config.design_tokens import get_design_tokens, SystemColors, SystemUI
from ..constants import GAME_CONSTANTS
from ...utils.sprites import draw_ripple


class HUDLayout:
    """HUD layout constants — positions for score, health, kills, boss info."""
    SCORE_POS = (15, 15)
    PROGRESS_POS = (15, 45)
    DIFFICULTY_OFFSET_X = -110
    DIFFICULTY_Y = 15
    HEALTH_OFFSET_X = -170
    HEALTH_Y = 45
    KILLS_OFFSET_X = -130
    KILLS_Y = 75
    BOSS_OFFSET_X = -130
    BOSS_Y = 100
    HEALTH_DANGER_RATIO = 0.3
    HEALTH_NORMAL = (100, 255, 150)
    HEALTH_DANGER = (255, 80, 80)
    SCORE_COLOR = (255, 255, 255)
    PROGRESS_COLOR = (200, 200, 100)
    KILLS_COLOR = (180, 180, 180)
    BOSS_COLOR = (255, 100, 100)


class HUDRenderer:
    """HUD renderer — score, health bar, boss HP, buff stats, notifications.
    
        Renders all heads-up display elements including military-style and
        original-style boss health bars.
    
        Attributes:
            hud_font: Primary font for HUD text elements.
            _buff_stats_panel: BuffStatsPanel for active buff display.
        """
    def __init__(self):
        pygame.font.init()
        self._tokens = get_design_tokens()
        tokens = self._tokens

        self.hud_font = get_cjk_font(tokens.typography.HUD_SIZE)
        self.buff_font = get_cjk_font(tokens.typography.TINY_SIZE)
        self.notif_font = get_cjk_font(tokens.typography.CAPTION_SIZE)
        self._boss_small_font = get_cjk_font(tokens.typography.SMALL_SIZE)
        self._boss_label_font = get_cjk_font(SystemUI.MILITARY_LABEL_SIZE)
        self._boss_warning_font = get_cjk_font(SystemUI.MILITARY_SMALL_SIZE)
        self._boss_timer_font = get_cjk_font(32)
        self._boss_hurry_font = get_cjk_font(30)
        self._buff_stats_panel = BuffStatsPanel()
        self._attack_mode_panel = AttackModePanel()
        self._text_cache: dict = {}

    def _render_value(self, font, text, color, cache_key: str):
        entry = self._text_cache.get(cache_key)
        if entry is not None and entry[0] == text:
            return entry[1]
        surf = font.render(text, True, color)
        self._text_cache[cache_key] = (text, surf)
        return surf

    def render_hud(self, surface: pygame.Surface, score: int, difficulty: str,
                  player_health: int, player_max_health: int, kills: int,
                  next_progress: int, boss_kills: int = 0) -> None:
        score_text = self.hud_font.render(f"分数: {score}", True, HUDLayout.SCORE_COLOR)
        surface.blit(score_text, HUDLayout.SCORE_POS)

        progress_text = self.hud_font.render(f"目标: {next_progress}%", True, HUDLayout.PROGRESS_COLOR)
        surface.blit(progress_text, HUDLayout.PROGRESS_POS)

        diff_text = self.hud_font.render(f"{difficulty.upper()}", True, HUDLayout.PROGRESS_COLOR)
        surface.blit(diff_text, (surface.get_width() + HUDLayout.DIFFICULTY_OFFSET_X, HUDLayout.DIFFICULTY_Y))

        health_color = HUDLayout.HEALTH_NORMAL
        if player_health < player_max_health * HUDLayout.HEALTH_DANGER_RATIO:
            health_color = HUDLayout.HEALTH_DANGER
        health_text = self.hud_font.render(f"生命: {player_health}/{player_max_health}", True, health_color)
        surface.blit(health_text, (surface.get_width() + HUDLayout.HEALTH_OFFSET_X, HUDLayout.HEALTH_Y))

        kills_text = self.hud_font.render(f"击杀: {kills}", True, HUDLayout.KILLS_COLOR)
        surface.blit(kills_text, (surface.get_width() + HUDLayout.KILLS_OFFSET_X, HUDLayout.KILLS_Y))

        boss_text = self.hud_font.render(f"BOSS: {boss_kills}", True, HUDLayout.BOSS_COLOR)
        surface.blit(boss_text, (surface.get_width() + HUDLayout.BOSS_OFFSET_X, HUDLayout.BOSS_Y))

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
            colors = self._tokens.colors
            alpha = min(255, timer * 4)
            color = colors.INFO if alpha > GAME_CONSTANTS.TIMING.NOTIFICATION_ALPHA_THRESHOLD else (150, 255, 200)
            text = self.notif_font.render(notification, True, color)
            text.set_alpha(alpha)
            x = surface.get_width() // 2 - text.get_width() // 2
            y = 100
            surface.blit(text, (x, y))

    def render_boss_health_bar(self, surface: pygame.Surface, boss, use_themed_style: bool = True) -> None:
        if not boss:
            return

        if use_themed_style:
            self.render_boss_health_bar_themed(surface, boss)
        else:
            self._render_boss_health_bar_original(surface, boss)

    def _render_boss_health_bar_original(self, surface: pygame.Surface, boss) -> None:
        """Original boss health bar rendering"""
        colors = self._tokens.colors
        components = self._tokens.components

        bar_width = components.HEALTH_BAR_WIDTH
        bar_height = components.HEALTH_BAR_HEIGHT
        x = (surface.get_width() - bar_width) // 2
        y = 15

        pygame.draw.rect(surface, (40, 40, 60), (x - 3, y - 3, bar_width + 6, bar_height + 6), border_radius=8)
        pygame.draw.rect(surface, (55, 55, 75), (x, y, bar_width, bar_height), border_radius=6)

        health_ratio = boss.health / boss.max_health
        bar_color = colors.BOSS_HEALTH_HIGH if health_ratio > 0.5 else colors.BOSS_HEALTH_MED if health_ratio > 0.25 else colors.BOSS_HEALTH_LOW
        pygame.draw.rect(surface, bar_color, (x, y, int(bar_width * health_ratio), bar_height), border_radius=6)

        font = self._boss_small_font
        boss_text = font.render("BOSS", True, colors.TEXT_PRIMARY)
        text_rect = boss_text.get_rect(center=(x + bar_width // 2, y + bar_height // 2))
        surface.blit(boss_text, text_rect)

        # Timer panel below the health bar
        time_remaining = boss.get_time_remaining()
        progress = boss.get_survival_progress()
        self._render_boss_timer(surface, x, y + bar_height + 4, bar_width,
                                time_remaining, progress)

    def _render_boss_timer(self, surface, x, y, bar_width, time_remaining, progress):
        """Render boss escape timer in a styled panel below the health bar."""
        timer_panel_h = 36
        timer_panel = pygame.Rect(x, y, bar_width, timer_panel_h)

        # Panel background
        pygame.draw.rect(surface, (12, 16, 24, 190), timer_panel, border_radius=6)
        pygame.draw.rect(surface, (55, 90, 130, 70), timer_panel, width=1, border_radius=6)

        # Timer color transitions from steel-blue (safe) to amber to red (urgent)
        if progress < 0.5:
            t = 0.0
        elif progress < 0.75:
            t = (progress - 0.5) / 0.25
        else:
            t = 1.0
        r = int(120 + 135 * t)
        g = int(185 - 100 * t)
        b = int(210 - 130 * t)
        timer_color = (r, g, b)

        secs = int(time_remaining)
        timer_text = self._render_value(self._boss_timer_font, f"{secs}s", timer_color, "boss_timer")
        timer_rect = timer_text.get_rect(center=timer_panel.center)
        surface.blit(timer_text, timer_rect)

        # HURRY warning — pulsing red above the timer panel when urgent
        if progress > 0.7:
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.008)) * 0.4 + 0.6
            alpha = int(200 * pulse)
            hurry_text = self._boss_hurry_font.render("逃跑中!", True,
                                                       (220, 70, 55))
            hurry_text.set_alpha(alpha)
            hurry_rect = hurry_text.get_rect(midtop=(x + bar_width // 2, y + timer_panel_h + 6))
            surface.blit(hurry_text, hurry_rect)

    def render_boss_health_bar_themed(self, surface: pygame.Surface, boss) -> None:
        """Themed-style boss health bar rendering"""
        components = self._tokens.components
        bar_width = components.HEALTH_BAR_WIDTH
        bar_height = components.HEALTH_BAR_HEIGHT
        x = (surface.get_width() - bar_width) // 2
        y = 15

        health_ratio = boss.health / boss.max_health

        # Draw chamfered panel background
        draw_chamfered_panel(
            surface, x - 4, y - 4, bar_width + 8, bar_height + 8,
            SystemColors.BG_PANEL,
            SystemColors.BORDER_GLOW,
            SystemColors.AMBER_GLOW,
            chamfer_depth=8
        )

        # Draw segmented progress bar
        boss_bar = BossHealthBar(bar_width, bar_height)
        font = self._boss_label_font

        # Determine boss name
        boss_name = getattr(boss, 'name', 'BOSS') if boss else 'BOSS'

        # Get phase info if available
        current_phase = getattr(boss, 'phase', 1)
        total_phases = getattr(boss, 'total_phases', 3)

        boss_bar.render(
            surface, x, y,
            boss.health, boss.max_health,
            boss_name=boss_name,
            current_phase=current_phase,
            total_phases=total_phases,
            font=font
        )

        # Time remaining — styled panel below the bar
        time_remaining = boss.get_time_remaining()
        progress = boss.get_survival_progress()
        self._render_boss_timer(surface, x, y + bar_height + 4, bar_width,
                                time_remaining, progress)

    def render_ripples(self, surface: pygame.Surface, ripples: List[dict]) -> None:
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
        except (AttributeError, TypeError) as e:
            pass
        except Exception as e:
            import logging
            logging.warning(f"Failed to render buff stats panel: {e}")

    def render_attack_mode_panel(
        self,
        surface: pygame.Surface,
        reward_system
    ) -> None:
        if not reward_system:
            return

        try:
            self._attack_mode_panel.render(
                surface,
                reward_system,
                surface.get_width(),
                surface.get_height()
            )
        except (AttributeError, TypeError) as e:
            pass
        except Exception as e:
            import logging
            logging.warning(f"Failed to render attack mode panel: {e}")
