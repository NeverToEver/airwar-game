"""Reward card renderer — all drawing for the reward selector.

Renders the background gradient, star/particle/nebula fields, panel,
title, bottom hint, and each option card (legacy + themed variants).
The renderer holds a back-reference to the orchestrator to read
animation/option state and append option rects for mouse hit-testing.
"""

import math

import pygame

from airwar.config.design_tokens import SceneColors, SystemUI
from airwar.utils.fonts import get_cjk_font
from airwar.utils.responsive import ResponsiveHelper  # noqa: F401  (responsive helpers may be reused)

from ..chamfered_panel import draw_chamfered_panel
from ..scene_rendering_utils import fit_text_to_width, wrap_text


class RewardCardRenderer:
    """Render the reward selector panel and its option cards.

    The renderer keeps a single ``_gradient_cache`` to avoid rebuilding
    the screen-sized background gradient every frame, matching the
    behavior of the original god class.
    """

    def __init__(self, selector):
        self._selector = selector
        self._gradient_cache: pygame.Surface | None = None
        self._gradient_cache_size: tuple = (0, 0)
        self._init_fonts()

    def _init_fonts(self) -> None:
        tokens = self._selector._tokens
        pygame.font.init()
        self.title_font = get_cjk_font(tokens.typography.SUBHEADING_SIZE)
        self.option_font = get_cjk_font(tokens.typography.BODY_SIZE)
        self.hint_font = get_cjk_font(tokens.typography.SMALL_SIZE)

    # ------------------------------------------------------------------
    # Background fields
    # ------------------------------------------------------------------

    def _draw_themed_background(self, surface: pygame.Surface) -> None:
        """Draw deep space gradient background."""
        width, height = surface.get_size()
        colors = self._selector._tokens.colors
        bg_primary = colors.BACKGROUND_PRIMARY
        bg_secondary = colors.BACKGROUND_SECONDARY
        for y in range(height):
            ratio = y / height
            r = int(bg_primary[0] * (1 - ratio) + bg_secondary[0] * ratio)
            g = int(bg_primary[1] * (1 - ratio) + bg_secondary[1] * ratio)
            b = int(bg_primary[2] * (1 - ratio) + bg_secondary[2] * ratio)
            pygame.draw.line(surface, (r, g, b), (0, y), (width, y))

    def _draw_gradient_background(self, surface: pygame.Surface) -> None:
        """Draw a cached vertical gradient using legacy colors."""
        width, height = surface.get_size()
        size = (width, height)
        colors = self._selector.colors
        if self._gradient_cache is None or self._gradient_cache_size != size:
            self._gradient_cache = pygame.Surface((width, height))
            for y in range(height):
                ratio = y / height
                r = int(colors["bg"][0] * (1 - ratio) + colors["bg_gradient"][0] * ratio)
                g = int(colors["bg"][1] * (1 - ratio) + colors["bg_gradient"][1] * ratio)
                b = int(colors["bg"][2] * (1 - ratio) + colors["bg_gradient"][2] * ratio)
                pygame.draw.line(self._gradient_cache, (r, g, b), (0, y), (width, y))
            self._gradient_cache_size = size
        surface.blit(self._gradient_cache, (0, 0))

    def _draw_stars(self, surface: pygame.Surface) -> None:
        """Render twinkling star field."""
        width, height = surface.get_size()
        animator = self._selector._animator
        for star in animator.stars:
            x = int(star["x"] * width)
            y = int(star["y"] * height)
            twinkle = math.sin(animator.animation_time * star["twinkle_speed"] + star["twinkle_offset"])
            brightness = int(star["brightness"] * (0.4 + 0.6 * twinkle))
            size = int(star["size"] * (0.7 + 0.3 * twinkle))
            if size >= 1:
                glow_size = size * 2
                glow_surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
                glow_r = max(0, min(255, brightness))
                glow_g = max(0, min(255, brightness + 20))
                glow_b = max(0, min(255, brightness + 40))
                pygame.draw.circle(glow_surf, (glow_r, glow_g, glow_b, 30), (glow_size, glow_size), glow_size)
                surface.blit(glow_surf, (x - glow_size, y - glow_size), special_flags=pygame.BLEND_RGBA_ADD)
                core_r = max(0, min(255, brightness))
                core_g = max(0, min(255, brightness + 30))
                core_b = max(0, min(255, brightness + 50))
                pygame.draw.circle(surface, (core_r, core_g, core_b), (x, y), size)

    def _draw_particles(self, surface: pygame.Surface) -> None:
        """Render pulsing ambient particles."""
        width, height = surface.get_size()
        animator = self._selector._animator
        particle_color = self._selector._tokens.colors.PARTICLE_PRIMARY
        for p in animator.particles:
            x = int(p["x"] * width)
            y = int(p["y"] * height)
            pulse = math.sin(animator.animation_time * p["pulse_speed"] + p["pulse_offset"])
            alpha = int(p["alpha"] * (0.5 + 0.5 * pulse))
            size = int(p["size"] * (0.6 + 0.4 * pulse))
            particle_surf = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
            for i in range(size * 2, 0, -2):
                layer_alpha = int(alpha * (size * 2 - i) / (size * 2) * 0.5)
                pygame.draw.circle(particle_surf, (*particle_color, layer_alpha), (size * 2, size * 2), i)
            surface.blit(particle_surf, (x - size * 2, y - size * 2), special_flags=pygame.BLEND_RGBA_ADD)

    # ------------------------------------------------------------------
    # Title / panel / hint
    # ------------------------------------------------------------------

    def _draw_themed_title(self, surface: pygame.Surface) -> None:
        """Draw title in military style with multi-pass amber glow."""
        width, _height = surface.get_size()
        glow_offset = self._selector._animator.glow_offset
        title_y = 130 + glow_offset * 0.5
        title_text = "选择奖励"

        for blur, alpha, color in [(3, 15, SceneColors.GOLD_DIM), (2, 25, SceneColors.GOLD_PRIMARY)]:
            glow_surf = self.title_font.render(title_text, True, color)
            glow_surf.set_alpha(alpha)
            for offset_x in range(-blur, blur + 1, 2):
                for offset_y in range(-blur, blur + 1, 2):
                    if offset_x * offset_x + offset_y * offset_y <= blur * blur:
                        glow_rect = glow_surf.get_rect(center=(width // 2 + offset_x, title_y + offset_y))
                        surface.blit(glow_surf, glow_rect)

        title = self.title_font.render(title_text, True, SceneColors.GOLD_PRIMARY)
        surface.blit(title, title.get_rect(center=(width // 2, title_y)))

    def _draw_glow_text(
        self,
        surface: pygame.Surface,
        text: str,
        font: pygame.font.Font,
        pos: tuple,
        color: tuple,
        glow_color: tuple,
        glow_radius: int = 2,
    ) -> None:
        """Draw text with a simple stacked-down glow."""
        for i in range(glow_radius, 0, -1):
            alpha = int(100 / i)
            glow_surf = font.render(text, True, glow_color)
            glow_surf.set_alpha(alpha)
            glow_rect = glow_surf.get_rect(center=(pos[0], pos[1] + i))
            surface.blit(glow_surf, glow_rect)

        main_text = font.render(text, True, color)
        surface.blit(main_text, main_text.get_rect(center=pos))

    def _draw_title(self, surface: pygame.Surface) -> None:
        """Draw the legacy title with a stacked glow."""
        width, _height = surface.get_size()
        glow_offset = self._selector._animator.glow_offset
        title_y = 130 + glow_offset * 0.5
        colors = self._selector.colors
        self._draw_glow_text(
            surface,
            "选择奖励",
            self.title_font,
            (width // 2, title_y),
            colors["title"],
            colors["title_glow"],
            3,
        )

    def _draw_themed_panel(self, surface: pygame.Surface) -> None:
        """Draw panel in military style with chamfered corners."""
        width, height = surface.get_size()
        from .reward_layout import RewardLayout

        box_width = RewardLayout.calculate_option_box_width(
            surface,
            self._selector.options,
            True,
            self.option_font,
            self.hint_font,
            self._selector.buff_levels,
            self._selector.unlocked_buffs,
        )
        panel_width = RewardLayout.calculate_panel_width(surface, box_width)
        glow_offset = self._selector._animator.glow_offset
        panel_x = width // 2 - panel_width // 2
        panel_y = height // 2 - 340 // 2 + glow_offset * 0.3

        draw_chamfered_panel(
            surface,
            panel_x,
            panel_y,
            panel_width,
            340,
            SceneColors.BG_PANEL,
            SceneColors.BORDER_GLOW,
            SceneColors.GOLD_GLOW,
            SystemUI.CHAMFER_DEPTH,
        )

    def _draw_panel(self, surface: pygame.Surface) -> None:
        """Draw the legacy panel: solid fill + soft outer glow + border."""
        width, height = surface.get_size()
        glow_offset = self._selector._animator.glow_offset
        panel_width = 480
        panel_height = 320
        panel_x = width // 2 - panel_width // 2
        panel_y = height // 2 - panel_height // 2 + glow_offset * 0.3

        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        colors = self._selector.colors

        for i in range(3, 0, -1):
            expand = i * 4
            glow_surf = pygame.Surface((panel_width + expand * 2, panel_height + expand * 2), pygame.SRCALPHA)
            alpha = max(5, 20 // i)
            pygame.draw.rect(glow_surf, (*colors["title_glow"], alpha), glow_surf.get_rect(), border_radius=18)
            surface.blit(glow_surf, (panel_x - expand, panel_y - expand))

        pygame.draw.rect(surface, colors["panel"], panel_rect, border_radius=15)

        border_surf = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        pygame.draw.rect(
            border_surf, (*colors["panel_border"], 120), border_surf.get_rect(), width=2, border_radius=15
        )
        surface.blit(border_surf, panel_rect.topleft)

    def _draw_bottom_hint(self, surface: pygame.Surface) -> None:
        """Draw the blinking bottom hint (W/S to choose, Enter to confirm)."""
        width, height = surface.get_size()
        animator = self._selector._animator
        if self._selector.use_themed_style:
            hint_color = SceneColors.TEXT_DIM if animator.animation_time // 25 % 2 == 0 else SceneColors.TEXT_PRIMARY
        else:
            hint_color = (90, 100, 140) if animator.animation_time // 25 % 2 == 0 else (120, 130, 170)
        hint = self.hint_font.render("W/S 选择, 回车确认", True, hint_color)
        surface.blit(hint, hint.get_rect(center=(width // 2, height - 50)))

    # ------------------------------------------------------------------
    # Option cards
    # ------------------------------------------------------------------

    def _draw_option_item(
        self,
        surface: pygame.Surface,
        option: dict,
        index: int,
        center_x: int,
        start_y: int,
        is_selected: bool,
        box_width: int,
    ) -> None:
        """Render a single option card in the legacy (rounded-rect) style."""
        from .reward_layout import RewardLayout

        selector = self._selector
        colors = selector.colors
        box_rect = RewardLayout.option_rect(center_x, start_y, index, box_width)
        selector.append_option_rect(box_rect)

        buff_name = option["name"]
        level = selector.buff_levels.get(buff_name, 0)
        is_upgraded = buff_name in selector.unlocked_buffs and level > 0

        if is_upgraded:
            glow_color = colors["upgraded_glow"]
            bg_color = colors["upgraded_bg"]
            border_color = colors["upgraded"]
        elif is_selected:
            glow_color = colors["selected_glow"]
            bg_color = colors["option_selected_bg"]
            border_color = colors["selected"]
        else:
            glow_color = colors["title_glow"]
            bg_color = colors["option_unselected_bg"]
            border_color = colors["unselected"]

        if is_selected or is_upgraded:
            for i in range(4, 0, -1):
                expand = i * 3
                glow_rect = box_rect.inflate(expand * 2, expand * 2)
                glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (*glow_color, 30 // i), glow_surf.get_rect(), border_radius=10)
                surface.blit(glow_surf, glow_rect)

        pygame.draw.rect(surface, bg_color, box_rect, border_radius=10)
        border_surf = pygame.Surface((box_width, 84), pygame.SRCALPHA)
        alpha = 200 if is_selected or is_upgraded else 70
        width = 2 if is_selected or is_upgraded else 1
        pygame.draw.rect(border_surf, (*border_color, alpha), border_surf.get_rect(), width=width, border_radius=10)
        surface.blit(border_surf, box_rect.topleft)

        arrow = ">" if is_selected else " "
        if is_upgraded:
            name_text = f"{arrow} {buff_name} [Lv.{level}]"
            text_color = colors["upgraded"] if is_selected else colors["unselected"]
        else:
            name_text = f"{arrow} {buff_name}"
            text_color = colors["selected"] if is_selected else colors["unselected"]

        text = fit_text_to_width(self.option_font, name_text, text_color, box_width - 50)
        text_rect = text.get_rect(topleft=(box_rect.x + 25, box_rect.y + 10))
        surface.blit(text, text_rect)

        desc_color = colors["desc_selected"] if is_selected else colors["desc_unselected"]
        desc_y = box_rect.y + 52
        for line in wrap_text(option["desc"], self.hint_font, box_width - 70, max_lines=2):
            desc = self.hint_font.render(line, True, desc_color)
            surface.blit(desc, desc.get_rect(topleft=(box_rect.x + 35, desc_y)))
            desc_y += 22

    def _draw_themed_option_item(
        self,
        surface: pygame.Surface,
        option: dict,
        index: int,
        center_x: int,
        start_y: int,
        is_selected: bool,
        box_width: int,
    ) -> None:
        """Render a single option card in the military (chamfered) style."""
        from .reward_layout import RewardLayout

        selector = self._selector
        box_rect = RewardLayout.option_rect(center_x, start_y, index, box_width)
        selector.append_option_rect(box_rect)

        buff_name = option["name"]
        level = selector.buff_levels.get(buff_name, 0)
        is_upgraded = buff_name in selector.unlocked_buffs and level > 0

        glow_color = SceneColors.GOLD_GLOW if is_upgraded or is_selected else None

        if glow_color:
            draw_chamfered_panel(
                surface,
                box_rect.x - 3,
                box_rect.y - 3,
                box_width + 6,
                84 + 6,
                SceneColors.BG_PANEL,
                glow_color,
                glow_color,
                10,
            )

        if is_upgraded:
            bg_color = SceneColors.BG_PANEL
            border_color = SceneColors.GOLD_BRIGHT
        elif is_selected:
            bg_color = SceneColors.BG_PANEL
            border_color = SceneColors.GOLD_PRIMARY
        else:
            bg_color = SceneColors.BG_PANEL_LIGHT
            border_color = SceneColors.BORDER_DIM

        draw_chamfered_panel(surface, box_rect.x, box_rect.y, box_width, 84, bg_color, border_color, None, 8)

        arrow = ">" if is_selected else " "
        if is_upgraded:
            name_text = f"{arrow} {buff_name} [Lv.{level}]"
            text_color = SceneColors.GOLD_BRIGHT if is_selected else SceneColors.TEXT_DIM
        else:
            name_text = f"{arrow} {buff_name}"
            text_color = SceneColors.GOLD_PRIMARY if is_selected else SceneColors.TEXT_DIM

        text = fit_text_to_width(self.option_font, name_text, text_color, box_width - 50)
        text_rect = text.get_rect(topleft=(box_rect.x + 25, box_rect.y + 10))
        surface.blit(text, text_rect)

        desc_color = SceneColors.FOREST_GREEN if is_selected else SceneColors.TEXT_DIM
        desc_y = box_rect.y + 52
        for line in wrap_text(option["desc"], self.hint_font, box_width - 70, max_lines=2):
            desc = self.hint_font.render(line, True, desc_color)
            surface.blit(desc, desc.get_rect(topleft=(box_rect.x + 35, desc_y)))
            desc_y += 22
