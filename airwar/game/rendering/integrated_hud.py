"""Integrated HUD — unified heads-up display combining all UI elements."""
import pygame
from airwar.utils.fonts import get_cjk_font
from typing import List
from airwar.config.design_tokens import get_design_tokens
from airwar.ui.discrete_battery import DiscreteBatteryIndicator


class IntegratedHUD:
    """Integrated HUD — unified heads-up display combining all HUD elements."""
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
        self._label_cache = {}
        self._fonts: dict = {}
        self._arrow_cache = None
        self._hint_cache = None
        self._battery_collapsed: DiscreteBatteryIndicator = None
        self._battery_expanded: DiscreteBatteryIndicator = None

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

        self.bg_color = (*colors.BACKGROUND_PANEL, 230)
        self.border_color = (*colors.PANEL_BORDER, 180)

    def _get_font(self, size):
        """Return a cached font object for the given size."""
        if size not in self._fonts:
            self._fonts[size] = get_cjk_font(size)
        return self._fonts[size]

    def _cached_label(self, font_size, text, color):
        """Return a pre-rendered label surface, caching on first call."""
        key = (font_size, text, color)
        if key not in self._label_cache:
            self._label_cache[key] = self._get_font(font_size).render(text, True, color)
        return self._label_cache[key]

    def update_scroll(self, buff_count: int = 0):
        if not self._is_expanded or buff_count <= self._buff_visible_count:
            self._buff_scroll_offset = 0.0
            return

        self._buff_scroll_offset += self._buff_scroll_speed
        if self._buff_scroll_offset >= buff_count:
            self._buff_scroll_offset = 0.0

    def update_health_tank(self, health: int, max_health: int) -> None:
        if self._battery_collapsed:
            self._battery_collapsed.set_health(health, max_health)
        if self._battery_expanded:
            self._battery_expanded.set_health(health, max_health)

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
        initial_coefficient: float = None,
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
            self._render_collapsed_health(
                surface, player_health, player_max_health, colors, panel_x, panel_y, panel_height
            )
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

    def _render_collapsed_health(self, surface, health, max_health, colors,
                                  panel_x, panel_y, panel_height):
        cw = self._current_width
        inner_h = panel_height - self.padding * 2
        if self._battery_collapsed is None:
            bw = min(36, cw - 10)
            bh = inner_h // 3
            self._battery_collapsed = DiscreteBatteryIndicator(
                width=bw, height=bh, num_segments=30, orientation='vertical')

        battery = self._battery_collapsed
        bw = battery._w
        tx = panel_x + (cw - bw) // 2
        ty = panel_y + panel_height - self.padding - battery._h - 30
        battery.render(surface, tx, ty)

        border_rect = pygame.Rect(tx, ty, bw, battery._h)
        pygame.draw.rect(surface, (*colors.PANEL_BORDER, 140),
                         border_rect, width=1, border_radius=4)

    def _render_collapsed_mothership_ring(self, surface, status, colors, panel_x, panel_y, panel_height):
        """Draw a circular cooldown ring in collapsed mode, styled like the health indicator."""
        cx = panel_x + self._current_width // 2
        # Position the ring below the health battery
        ring_radius = min(28, (self._current_width - 8) // 2)
        ring_y = panel_y + panel_height - self.padding - 12
        ring_thickness = 5

        progress = status.get('cooldown_progress', 0.0)
        is_cooldown = status.get('is_in_cooldown', False)
        cooldown_remaining = status.get('cooldown_remaining', 0.0)

        # Background ring
        pygame.draw.circle(surface, (*colors.BACKGROUND_SECONDARY, 160),
                           (cx, ring_y), ring_radius, ring_thickness)

        if is_cooldown and progress < 1.0:
            # Draw cooldown progress arc (amber)
            import math
            cooldown_color = (160, 120, 50)
            steps = max(4, int(progress * 32))
            for i in range(steps):
                angle = -math.pi / 2 + (i / 32.0) * 2 * math.pi
                px = cx + int(math.cos(angle) * (ring_radius - ring_thickness // 2))
                py = ring_y + int(math.sin(angle) * (ring_radius - ring_thickness // 2))
                alpha = 120 + int(80 * (i / max(steps, 1)))
                glow_surf = pygame.Surface((6, 6), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (*cooldown_color, alpha), (3, 3), 3)
                surface.blit(glow_surf, (px - 3, py - 3))
            # Remaining seconds in center
            secs = int(cooldown_remaining)
            label = self._cached_label(max(12, self.label_font_size - 8),
                                       str(secs), colors.TEXT_MUTED)
            surface.blit(label, label.get_rect(center=(cx, ring_y)))
        else:
            # Ready — green circle
            ready_color = (80, 200, 100) if not is_cooldown else (160, 185, 80)
            pygame.draw.circle(surface, (*ready_color, 180),
                               (cx, ring_y), ring_radius - ring_thickness + 1, ring_thickness)
            label = self._cached_label(max(12, self.label_font_size - 8),
                                       "OK", ready_color)
            surface.blit(label, label.get_rect(center=(cx, ring_y)))

    def _render_mothership_module(self, surface, status, colors, panel_x, y):
        """Draw mothership status bar in expanded mode."""
        inner_width = self._current_width - self.padding * 2
        bar_width = inner_width - 20
        bar_height = self.progress_bar_height

        state = status.get('state')
        import enum
        state_name = state.value if hasattr(state, 'value') else str(state)

        label = self._cached_label(self.label_font_size - 2, "母舰", colors.TEXT_MUTED)
        surface.blit(label, (panel_x + self.padding, y))

        y += 22
        bar_rect = pygame.Rect(panel_x + self.padding, y, bar_width, bar_height)
        pygame.draw.rect(surface, (*colors.BACKGROUND_SECONDARY, 180), bar_rect, border_radius=4)

        from airwar.game.mother_ship.mother_ship_state import MotherShipState
        if state == MotherShipState.PRESSING:
            fill_color = (60, 160, 220)
            progress = status.get('hold_progress', 0.0)
            fill_text = "按住"
        elif state == MotherShipState.ENTERING:
            fill_color = (60, 160, 220)
            progress = 0.5
            fill_text = "进入"
        elif state == MotherShipState.DOCKING:
            fill_color = (80, 180, 110)
            progress = 0.7
            fill_text = "停靠"
        elif state == MotherShipState.DOCKED:
            fill_color = (80, 180, 110)
            progress = status.get('stay_progress', 0.0)
            secs = int(status.get('stay_remaining', 0))
            fill_text = f"{secs}秒"
        elif state == MotherShipState.UNDOCKING:
            fill_color = (160, 120, 50)
            progress = 0.5
            fill_text = "脱离"
        elif status.get('is_in_cooldown'):
            fill_color = (160, 120, 50)
            progress = status.get('cooldown_progress', 0.0)
            secs = int(status.get('cooldown_remaining', 0))
            fill_text = f"{secs}秒"
        else:
            fill_color = (80, 120, 160)
            progress = 0.0
            fill_text = "就绪"

        if progress > 0:
            fill_width = int(bar_width * min(progress, 1.0))
            if fill_width > 0:
                fill_rect = pygame.Rect(panel_x + self.padding, y, fill_width, bar_height)
                pygame.draw.rect(surface, (*fill_color, 200), fill_rect, border_radius=4)

        status_label = self._cached_label(max(11, self.label_font_size - 10),
                                          fill_text, colors.TEXT_MUTED)
        surface.blit(status_label, (panel_x + self.padding + bar_width + 6, y - 1))

        return y + bar_height + self.gap

    def _render_expand_indicator(self, surface, panel_x, panel_y, panel_height, colors):
        components = self._tokens.components
        indicator_x = panel_x + self._current_width - 20
        indicator_y = panel_y + panel_height // 2

        if self._arrow_cache is None:
            arrow_font = self._get_font(components.HUD_EXPAND_ARROW_SIZE)
            self._arrow_cache = arrow_font.render(">", True, colors.TEXT_MUTED)
        arrow_text = self._arrow_cache
        arrow_rect = arrow_text.get_rect(center=(indicator_x + 10, indicator_y))
        surface.blit(arrow_text, arrow_rect)

        if self._hint_cache is None:
            hint_font = self._get_font(components.HUD_EXPAND_HINT_SIZE)
            self._hint_cache = hint_font.render("[L]", True, colors.TEXT_HINT)
        hint_text = self._hint_cache
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

        label = self._cached_label(self.label_font_size, "分数", colors.TEXT_MUTED)
        surface.blit(label, (content_x, y))

        value_font = self._get_font(self.value_font_size)
        value = value_font.render(f"{score:,}", True, colors.TEXT_PRIMARY)
        surface.blit(value, (content_x, y + 22))

        return y + self.module_height + self.gap

    def _render_coefficient_module(self, surface, current, initial, colors, x, y):
        components = self._tokens.components
        content_x = x + self.padding
        
        label = self._cached_label(self.label_font_size, "系数", colors.TEXT_MUTED)
        surface.blit(label, (content_x, y))

        delta = current - initial
        if delta > 0:
            coeff_color = colors.WARNING
        elif delta < 0:
            coeff_color = colors.SUCCESS
        else:
            coeff_color = colors.TEXT_PRIMARY

        value_font = self._get_font(self.value_font_size)
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
        
        label = self._cached_label(self.label_font_size, "模式", colors.TEXT_MUTED)
        surface.blit(label, (content_x, y))

        diff_colors = {
            'easy': colors.SUCCESS,
            'medium': colors.PROGRESS_COLOR,
            'hard': colors.WARNING
        }
        diff_color = diff_colors.get(difficulty.lower(), colors.TEXT_PRIMARY)

        value_font = self._get_font(self.value_font_size)
        value = value_font.render(difficulty.upper(), True, diff_color)
        surface.blit(value, (content_x, y + 22))

        return y + self.module_height + self.gap

    def _render_progress_module(self, surface, progress, colors, x, y):
        content_x = x + self.padding
        
        label = self._cached_label(self.label_font_size, "进度", colors.TEXT_MUTED)
        surface.blit(label, (content_x, y))

        value_font = self._get_font(self.value_font_size)
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

        label = self._cached_label(self.label_font_size, "HP", colors.TEXT_MUTED)
        surface.blit(label, (content_x, y))

        health_ratio = health / max_health if max_health > 0 else 0
        health_color = colors.HEALTH_NORMAL if health_ratio > 0.3 else colors.HEALTH_DANGER

        value_font = self._get_font(self.value_font_size)
        value = value_font.render(f"{health}/{max_health}", True, health_color)
        surface.blit(value, (content_x, y + 22))

        bar_width = self.panel_width - self.padding * 2 - 4
        bar_height = 24
        bar_x = content_x
        bar_y = y + 46

        # 深色圆角背景条 — 与 progress bar 风格一致
        pygame.draw.rect(
            surface,
            (*colors.BACKGROUND_SECONDARY, 180),
            (bar_x, bar_y, bar_width, bar_height),
            border_radius=7
        )
        # 细边框 — 暗示总血量范围
        pygame.draw.rect(
            surface,
            (*colors.PANEL_BORDER, 150),
            (bar_x, bar_y, bar_width, bar_height),
            width=1, border_radius=7
        )

        if self._battery_expanded is None:
            self._battery_expanded = DiscreteBatteryIndicator(
                width=bar_width - 2, height=bar_height, num_segments=30,
                orientation='horizontal')
        self._battery_expanded.render(surface, bar_x + 1, bar_y)

        return y + self.module_height + self.gap + 10

    def _render_kills_module(self, surface, kills, colors, x, y):
        content_x = x + self.padding

        label = self._cached_label(self.label_font_size, "击杀", colors.TEXT_MUTED)
        surface.blit(label, (content_x, y))

        value_font = self._get_font(self.value_font_size)
        value = value_font.render(f"{kills}", True, colors.TEXT_PRIMARY)
        surface.blit(value, (content_x, y + 22))

        return y + self.module_height + self.gap

    def _render_boss_module(self, surface, boss_kills, colors, x, y):
        content_x = x + self.padding
        
        label = self._cached_label(self.label_font_size, "BOSS", colors.TEXT_MUTED)
        surface.blit(label, (content_x, y))

        value_font = self._get_font(self.value_font_size)
        value = value_font.render(f"{boss_kills}", True, colors.WARNING)
        surface.blit(value, (content_x, y + 22))

        return y + self.module_height + self.gap

    def _render_buffs_module(self, surface, buffs, get_buff_color, colors, panel_x, start_y):
        components = self._tokens.components
        content_x = panel_x + self.padding
        
        label = self._cached_label(self.label_font_size, "增益", colors.TEXT_MUTED)
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

            buff_font = self._get_font(self.buff_font_size)
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
            more_font = self._get_font(self.more_font_size)
            total_buffs = len(buffs)
            more_text = more_font.render(f"共{total_buffs}个", True, colors.TEXT_MUTED)
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

