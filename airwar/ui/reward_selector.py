"""Reward selector — buff selection interface at milestones.

Phase 4 W-alpha thin orchestrator. The class holds four components
(layout, click handler, animator, card renderer) and forwards every
public method to the appropriate component. State, rendering, and
input are delegated; this class is only the public API surface.

Public API (unchanged from pre-split):
    - ``show(options, callback, buff_levels=None, unlocked_buffs=None)``
    - ``hide()`` (replaceable — GameScene monkey-patches it)
    - ``update()``, ``render(surface)``, ``handle_input(event)``
    - ``visible`` attribute, plus ``options``, ``selected_index``,
      ``on_select``, ``buff_levels``, ``unlocked_buffs``,
      ``use_themed_style`` — public state read by MilestoneManager
      and the renderer.
"""

from collections.abc import Callable

import pygame

from airwar.config.design_tokens import SceneColors
from airwar.utils.mouse_interaction import MouseSelectableMixin

from .reward import (
    RewardAnimator,
    RewardCardRenderer,
    RewardClickHandler,
    RewardLayout,
)


class RewardSelector(MouseSelectableMixin):
    """Reward selector — thin orchestrator over 4 reward components."""

    def __init__(self):
        MouseSelectableMixin.__init__(self)
        self._animator = RewardAnimator()
        self._tokens = self._animator._tokens
        self._renderer = RewardCardRenderer(self)
        self._click_handler = RewardClickHandler(self)
        # Public state (read by MilestoneManager and GameScene directly).
        self.visible: bool = False
        self.selected_index: int = 0
        self.options: list[dict] = []
        self.on_select: Callable | None = None
        self.buff_levels: dict = {}
        self.unlocked_buffs: list = []
        self.use_themed_style: bool = True
        self._init_color_palettes()

    def _init_color_palettes(self) -> None:
        colors = self._tokens.colors
        self.colors = {
            "bg": colors.BACKGROUND_PRIMARY,
            "bg_gradient": colors.BACKGROUND_SECONDARY,
            "title": colors.TEXT_PRIMARY,
            "title_glow": colors.HUD_AMBER_BRIGHT,
            "selected": colors.HUD_AMBER,
            "selected_glow": colors.HUD_AMBER_BRIGHT,
            "unselected": colors.TEXT_MUTED,
            "desc_selected": (140, 200, 140),
            "desc_unselected": (80, 85, 120),
            "hint": colors.TEXT_HINT,
            "particle": colors.PARTICLE_PRIMARY,
            "panel": colors.BACKGROUND_PANEL,
            "panel_border": colors.PANEL_BORDER,
            "option_selected_bg": colors.BUTTON_SELECTED_BG,
            "option_unselected_bg": colors.BUTTON_UNSELECTED_BG,
            "upgraded": colors.BUTTON_SELECTED_GLOW,
            "upgraded_glow": colors.HUD_AMBER_BRIGHT,
            "new_buff": colors.SUCCESS,
            "upgraded_bg": colors.BUTTON_SELECTED_BG,
        }
        self.themed_colors = {
            "bg": SceneColors.BG_PRIMARY,
            "bg_gradient": SceneColors.BG_PANEL,
            "title": SceneColors.TEXT_PRIMARY,
            "title_glow": SceneColors.GOLD_GLOW,
            "selected": SceneColors.GOLD_PRIMARY,
            "selected_glow": SceneColors.GOLD_BRIGHT,
            "unselected": SceneColors.TEXT_DIM,
            "desc_selected": SceneColors.FOREST_GREEN,
            "desc_unselected": SceneColors.TEXT_DIM,
            "hint": SceneColors.TEXT_DIM,
            "particle": SceneColors.GOLD_PRIMARY,
            "panel": SceneColors.BG_PANEL,
            "panel_border": SceneColors.BORDER_GLOW,
            "option_selected_bg": SceneColors.BG_PANEL,
            "option_unselected_bg": SceneColors.BG_PANEL_LIGHT,
            "upgraded": SceneColors.GOLD_BRIGHT,
            "upgraded_glow": SceneColors.GOLD_GLOW,
            "new_buff": SceneColors.FOREST_GREEN,
            "upgraded_bg": SceneColors.BG_PANEL,
        }

    def show(self, options, callback, buff_levels=None, unlocked_buffs=None) -> None:
        self.visible = True
        self.options = options
        self.selected_index = 0
        self.on_select = callback
        self._animator.animation_time = 0
        self.buff_levels = buff_levels or {}
        self.unlocked_buffs = unlocked_buffs or []

    def hide(self) -> None:
        self.visible = False
        self.options = []

    def update(self) -> None:
        if not self.visible:
            return
        self._animator.tick()
        self._animator.update_stars()
        self._animator.update_particles()
        self._animator.update_nebula_clouds()

    def render(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return

        renderer = self._renderer
        if self.use_themed_style:
            renderer._draw_themed_background(surface)
        else:
            renderer._draw_gradient_background(surface)
        renderer._draw_stars(surface)
        renderer._draw_particles(surface)

        if self.use_themed_style:
            renderer._draw_themed_title(surface)
        else:
            renderer._draw_title(surface)
        if self.use_themed_style:
            renderer._draw_themed_panel(surface)
        else:
            renderer._draw_panel(surface)

        box_width = RewardLayout.calculate_option_box_width(
            surface,
            self.options,
            self.use_themed_style,
            renderer.option_font,
            renderer.hint_font,
            self.buff_levels,
            self.unlocked_buffs,
        )
        center_x, _panel_y, start_y = RewardLayout.option_section_anchor(
            surface,
            self._animator.glow_offset,
        )
        self.clear_option_rects()
        effective_index = self.get_effective_selected_index(self.selected_index)
        for i, option in enumerate(self.options):
            if self.use_themed_style:
                renderer._draw_themed_option_item(
                    surface,
                    option,
                    i,
                    center_x,
                    start_y,
                    i == effective_index,
                    box_width,
                )
            else:
                renderer._draw_option_item(
                    surface,
                    option,
                    i,
                    center_x,
                    start_y,
                    i == effective_index,
                    box_width,
                )
        renderer._draw_bottom_hint(surface)

    def handle_input(self, event: pygame.event.Event) -> None:
        self._click_handler.handle_input(event)

    def _confirm_selection(self) -> None:
        if self.on_select and self.options:
            self.on_select(self.options[self.selected_index])
        self.hide()
