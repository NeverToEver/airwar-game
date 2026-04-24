import pygame
from typing import List, Dict, Any
from airwar.config.design_tokens import get_design_tokens


class IntegratedHUD:
    def __init__(self):
        self._tokens = get_design_tokens()
        self._setup_layout()
        self._is_expanded = False
        self._current_width = int(self.panel_width * self._tokens.components.HUD_PANEL_COLLAPSED_RATIO)
        self._buff_scroll_offset = 0.0
        self._buff_scroll_speed = self._tokens.components.BUFF_SCROLL_SPEED
        self._buff_visible_count = self._tokens.components.BUFF_SCROLL_VISIBLE_COUNT
        self._panel_bg_cache = {}
        self._bar_bg_cache = {}

    def _setup_layout(self):
        colors = self._tokens.colors
        components = self._tokens.components

        self.panel_width = components.HUD_PANEL_WIDTH
        self.padding = components.HUD_PANEL_PADDING
        self.module_height = components.HUD_PANEL_MODULE_HEIGHT
        self.gap = components.HUD_PANEL_GAP
        self.corner_radius = components.HUD_PANEL_CORNER_RADIUS

        self.label_font_size = components.HUD_LABEL_FONT_SIZE
        self.value_font_size = components.HUD_VALUE_FONT_SIZE
        self.buff_font_size = components.HUD_BUFF_FONT_SIZE
        self.more_font_size = components.HUD_MORE_FONT_SIZE
        self.progress_bar_height = components.HUD_PROGRESS_BAR_HEIGHT
        self.health_bar_height = components.HUD_HEALTH_BAR_HEIGHT

        self.bg_color = (*colors.BACKGROUND_PANEL, 230)
        self.border_color = (*colors.PANEL_BORDER, 180)

    def update_scroll(self, buff_count: int = 0):
        if not self._is_expanded or buff_count <= self._buff_visible_count:
            self._buff_scroll_offset = 0.0
            return
        
        self._buff_scroll_offset += self._buff_scroll_speed
        if self._buff_scroll_offset >= buff_count:
            self._buff_scroll_offset = 0.0

    def toggle(self):
        self._is_expanded = not self._is_expanded
        if self._is_expanded:
            self._current_width = self.panel_width
        else:
            self._current_width = int(self.panel_width * self._tokens.components.HUD_PANEL_COLLAPSED_RATIO)
        self._panel_bg_cache.clear()

    def is_expanded(self) -> bool:
        return self._is_expanded

    def render(
        self,
        surface: pygame.Surface,
        score: int,
        difficulty: str,
        player_health: int,
        player_max_health: int,
        kills: int,
        next_progress: int,
        boss_kills: int = 0,
        unlocked_buffs: List[str] = None,
        get_buff_color=None,
        current_coefficient: float = None,
        initial_coefficient: float = None
    ):
        colors = self._tokens.colors
        width = surface.get_width()
        height = surface.get_height()

        panel_x = width - self._current_width - self.padding
        panel_y = self.padding
        panel_height = height - self.padding * 2
        
        current_y = panel_y + self.padding

        panel_rect = pygame.Rect(panel_x, panel_y, self._current_width, panel_height)
        self._render_panel_background(surface, panel_rect, colors)

        current_y = self._render_score_module(surface, score, colors, panel_x, current_y)

        if self._is_expanded:
            if current_coefficient is not None and initial_coefficient is not None:
                current_y = self._render_coefficient_module(
                    surface, current_coefficient, initial_coefficient, colors, panel_x, current_y
                )

            current_y = self._render_difficulty_module(surface, difficulty, colors, panel_x, current_y)

            current_y = self._render_progress_module(surface, next_progress, colors, panel_x, current_y)

            current_y = self._render_health_module(
                surface, player_health, player_max_health, colors, panel_x, current_y
            )

            current_y = self._render_kills_module(surface, kills, colors, panel_x, current_y)

            if boss_kills > 0:
                current_y = self._render_boss_module(surface, boss_kills, colors, panel_x, current_y)

            if unlocked_buffs and get_buff_color:
                current_y = self._render_buffs_module(
                    surface, unlocked_buffs, get_buff_color, colors, panel_x, current_y
                )
        else:
            self._render_expand_indicator(surface, panel_x, panel_y, panel_height, colors)

    def _render_panel_background(self, surface, rect, colors):
        cache_key = (rect.width, rect.height, self._is_expanded)
        if cache_key not in self._panel_bg_cache:
            overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(
                overlay,
                (*colors.BACKGROUND_PANEL, 235),
                overlay.get_rect(),
                border_radius=self.corner_radius
            )
            border_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(
                border_surf,
                (*colors.PANEL_BORDER, 200),
                border_surf.get_rect(),
                width=2,
                border_radius=self.corner_radius
            )
            self._panel_bg_cache[cache_key] = (overlay, border_surf)
        overlay, border_surf = self._panel_bg_cache[cache_key]
        surface.blit(overlay, rect.topleft)
        surface.blit(border_surf, rect.topleft)

    def _render_expand_indicator(self, surface, panel_x, panel_y, panel_height, colors):
        components = self._tokens.components
        indicator_x = panel_x + self._current_width - 20
        indicator_y = panel_y + panel_height // 2
        
        arrow_font = pygame.font.Font(None, components.HUD_EXPAND_ARROW_SIZE)
        arrow_text = arrow_font.render(">", True, colors.TEXT_MUTED)
        arrow_rect = arrow_text.get_rect(center=(indicator_x + 10, indicator_y))
        surface.blit(arrow_text, arrow_rect)

        hint_font = pygame.font.Font(None, components.HUD_EXPAND_HINT_SIZE)
        hint_text = hint_font.render("[L]", True, colors.TEXT_HINT)
        hint_rect = hint_text.get_rect(center=(indicator_x + 10, indicator_y + 20))
        surface.blit(hint_text, hint_rect)

    def _render_bar_background(self, surface, rect, colors):
        cache_key = (rect.width, rect.height)
        if cache_key not in self._bar_bg_cache:
            overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(
                overlay,
                (*colors.BACKGROUND_PANEL, 230),
                overlay.get_rect(),
                border_radius=self.corner_radius
            )
            border_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(
                border_surf,
                (*colors.PANEL_BORDER, 200),
                border_surf.get_rect(),
                width=2,
                border_radius=self.corner_radius
            )
            line_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.line(
                line_surf,
                (*colors.PANEL_BORDER, 120),
                (30, rect.height - 10),
                (rect.width - 30, rect.height - 10),
                width=2
            )
            self._bar_bg_cache[cache_key] = (overlay, border_surf, line_surf)
        overlay, border_surf, line_surf = self._bar_bg_cache[cache_key]
        surface.blit(overlay, rect.topleft)
        surface.blit(border_surf, rect.topleft)
        surface.blit(line_surf, rect.topleft)

    def _render_score_module(self, surface, score, colors, x, y):
        content_x = x + self.padding
        
        label_font = pygame.font.Font(None, self.label_font_size)
        label = label_font.render("SCORE", True, colors.TEXT_MUTED)
        surface.blit(label, (content_x, y))

        value_font = pygame.font.Font(None, self.value_font_size)
        value = value_font.render(f"{score:,}", True, colors.TEXT_PRIMARY)
        surface.blit(value, (content_x, y + 22))

        return y + self.module_height + self.gap

    def _render_coefficient_module(self, surface, current, initial, colors, x, y):
        components = self._tokens.components
        content_x = x + self.padding
        
        label_font = pygame.font.Font(None, self.label_font_size)
        label = label_font.render("COEFF", True, colors.TEXT_MUTED)
        surface.blit(label, (content_x, y))

        delta = current - initial
        if delta > 0:
            coeff_color = colors.WARNING
        elif delta < 0:
            coeff_color = colors.SUCCESS
        else:
            coeff_color = colors.TEXT_PRIMARY

        value_font = pygame.font.Font(None, self.value_font_size)
        value_text = f"{current:.1f}"
        value = value_font.render(value_text, True, coeff_color)
        surface.blit(value, (content_x, y + 22))

        bar_width = self.panel_width - self.padding * 2 - 20
        bar_height = components.HUD_COEFFICIENT_BAR_HEIGHT
        bar_x = content_x
        bar_y = y + 46

        max_mult = components.COEFFICIENT_MAX_MULTIPLIER
        pygame.draw.rect(
            surface,
            (*colors.BACKGROUND_SECONDARY, 180),
            (bar_x, bar_y, bar_width, bar_height),
            border_radius=6
        )

        fill_ratio = min(current / max_mult, 1.0)
        fill_width = int(bar_width * fill_ratio)
        if fill_width > 0:
            pygame.draw.rect(
                surface,
                coeff_color,
                (bar_x, bar_y, fill_width, bar_height),
                border_radius=6
            )

        return y + self.module_height + self.gap + 10

    def _render_difficulty_module(self, surface, difficulty, colors, x, y):
        content_x = x + self.padding
        
        label_font = pygame.font.Font(None, self.label_font_size)
        label = label_font.render("MODE", True, colors.TEXT_MUTED)
        surface.blit(label, (content_x, y))

        diff_colors = {
            'easy': colors.SUCCESS,
            'medium': colors.PROGRESS_COLOR,
            'hard': colors.WARNING
        }
        diff_color = diff_colors.get(difficulty.lower(), colors.TEXT_PRIMARY)

        value_font = pygame.font.Font(None, self.value_font_size)
        value = value_font.render(difficulty.upper(), True, diff_color)
        surface.blit(value, (content_x, y + 22))

        return y + self.module_height + self.gap

    def _render_progress_module(self, surface, progress, colors, x, y):
        content_x = x + self.padding
        
        label_font = pygame.font.Font(None, self.label_font_size)
        label = label_font.render("PROGRESS", True, colors.TEXT_MUTED)
        surface.blit(label, (content_x, y))

        value_font = pygame.font.Font(None, self.value_font_size)
        value = value_font.render(f"{progress}%", True, colors.PROGRESS_COLOR)
        surface.blit(value, (content_x, y + 22))

        bar_width = self.panel_width - self.padding * 2 - 20
        bar_height = self.progress_bar_height
        bar_x = content_x
        bar_y = y + 46

        pygame.draw.rect(
            surface,
            (*colors.BACKGROUND_SECONDARY, 180),
            (bar_x, bar_y, bar_width, bar_height),
            border_radius=6
        )

        fill_width = int(bar_width * progress / 100)
        if fill_width > 0:
            pygame.draw.rect(
                surface,
                colors.PROGRESS_COLOR,
                (bar_x, bar_y, fill_width, bar_height),
                border_radius=6
            )

        return y + self.module_height + self.gap + 10

    def _render_health_module(self, surface, health, max_health, colors, x, y):
        content_x = x + self.padding
        
        label_font = pygame.font.Font(None, self.label_font_size)
        label = label_font.render("HP", True, colors.TEXT_MUTED)
        surface.blit(label, (content_x, y))

        health_ratio = health / max_health if max_health > 0 else 0
        health_color = colors.HEALTH_NORMAL if health_ratio > 0.3 else colors.HEALTH_DANGER

        value_font = pygame.font.Font(None, self.value_font_size)
        value = value_font.render(f"{health}/{max_health}", True, health_color)
        surface.blit(value, (content_x, y + 22))

        bar_width = self.panel_width - self.padding * 2 - 20
        bar_height = self.health_bar_height
        bar_x = content_x
        bar_y = y + 46

        pygame.draw.rect(
            surface,
            (*colors.BACKGROUND_SECONDARY, 180),
            (bar_x, bar_y, bar_width, bar_height),
            border_radius=8
        )

        fill_width = int(bar_width * health_ratio)
        if fill_width > 0:
            pygame.draw.rect(
                surface,
                health_color,
                (bar_x, bar_y, fill_width, bar_height),
                border_radius=8
            )

            highlight_surf = pygame.Surface((fill_width - 4, 3), pygame.SRCALPHA)
            pygame.draw.rect(
                highlight_surf,
                (*colors.TEXT_PRIMARY, 60),
                highlight_surf.get_rect(),
                border_radius=2
            )
            surface.blit(highlight_surf, (bar_x + 2, bar_y + 3))

        return y + self.module_height + self.gap + 10

    def _render_kills_module(self, surface, kills, colors, x, y):
        content_x = x + self.padding
        
        label_font = pygame.font.Font(None, self.label_font_size)
        label = label_font.render("KILLS", True, colors.TEXT_MUTED)
        surface.blit(label, (content_x, y))

        value_font = pygame.font.Font(None, self.value_font_size)
        value = value_font.render(f"{kills}", True, colors.TEXT_PRIMARY)
        surface.blit(value, (content_x, y + 22))

        return y + self.module_height + self.gap

    def _render_boss_module(self, surface, boss_kills, colors, x, y):
        content_x = x + self.padding
        
        label_font = pygame.font.Font(None, self.label_font_size)
        label = label_font.render("BOSS", True, colors.TEXT_MUTED)
        surface.blit(label, (content_x, y))

        value_font = pygame.font.Font(None, self.value_font_size)
        value = value_font.render(f"{boss_kills}", True, colors.WARNING)
        surface.blit(value, (content_x, y + 22))

        return y + self.module_height + self.gap

    def _render_buffs_module(self, surface, buffs, get_buff_color, colors, panel_x, start_y):
        components = self._tokens.components
        content_x = panel_x + self.padding
        
        label_font = pygame.font.Font(None, self.label_font_size)
        label = label_font.render("BUFFS", True, colors.TEXT_MUTED)
        surface.blit(label, (content_x, start_y))

        current_y = start_y + 26

        if not buffs:
            return current_y + 24

        should_scroll = len(buffs) > self._buff_visible_count and self._is_expanded
        visible_buffs = buffs[:self._buff_visible_count] if not should_scroll else self._get_visible_buffs(buffs)

        for idx, buff in enumerate(visible_buffs):
            buff_color = get_buff_color(buff)

            brightness = (buff_color[0] * 299 + buff_color[1] * 587 + buff_color[2] * 114) / 1000
            if brightness > components.BUFF_CONTRAST_THRESHOLD_HIGH:
                text_color = components.BUFF_TEXT_DARK
            elif brightness > components.BUFF_CONTRAST_THRESHOLD_MED:
                text_color = components.BUFF_HIGH_CONTRAST_COLORS[0]
            else:
                text_color = components.BUFF_TEXT_LIGHT

            buff_font = pygame.font.Font(None, self.buff_font_size)
            buff_text = buff_font.render(buff[:8].upper(), True, text_color)

            buff_width = self.panel_width - self.padding * 2 - 20
            padding = 6
            buff_height = buff_text.get_height() + padding * 2

            bg_rect = pygame.Rect(
                content_x,
                current_y,
                buff_width,
                buff_height
            )

            darker_bg = tuple(max(0, c - 60) for c in buff_color)
            pygame.draw.rect(
                surface,
                (*darker_bg, 220),
                bg_rect,
                border_radius=6
            )
            pygame.draw.rect(
                surface,
                buff_color,
                bg_rect,
                width=2,
                border_radius=6
            )

            text_rect = buff_text.get_rect(center=(bg_rect.centerx, bg_rect.centery))
            surface.blit(buff_text, text_rect.topleft)

            current_y += buff_height + 8

        if should_scroll:
            more_font = pygame.font.Font(None, self.more_font_size)
            total_buffs = len(buffs)
            more_text = more_font.render(f"{total_buffs} total", True, colors.TEXT_MUTED)
            surface.blit(more_text, (content_x, current_y + 4))

        return current_y + 24

    def _get_visible_buffs(self, buffs):
        if not buffs or not self._is_expanded:
            return buffs[:self._buff_visible_count]

        total_buffs = len(buffs)
        start_idx = int(self._buff_scroll_offset) % total_buffs
        
        visible = []
        for i in range(self._buff_visible_count):
            idx = (start_idx + i) % total_buffs
            visible.append(buffs[idx])
        
        return visible

