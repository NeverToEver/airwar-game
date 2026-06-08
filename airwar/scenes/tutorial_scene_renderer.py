"""Thin orchestrator that dispatches tutorial rendering to 4 sub-renderers.

Phase 4 Wave α split (see ``docs/logic-clarity/08-deep-godclass-split-plan.md``
section 2.8). The real drawing work lives in :mod:`airwar.scenes.tutorial.renderers`;
this module just keeps the public + private API of ``TutorialSceneRenderer``
stable (1-line forwarders) so callers and tests are untouched.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from airwar.scenes.tutorial.renderers import (
    BackgroundRenderer,
    EffectRenderer,
    EntityRenderer,
    UIRenderer,
)

if TYPE_CHECKING:
    from airwar.scenes.tutorial_scene import TutorialScene


class TutorialSceneRenderer:
    """Renders all visual elements for TutorialScene.

    Pure renderer: reads scene state, draws to a surface, never mutates
    the scene. The 25 private ``_render_*`` / ``_draw_*`` helpers are
    kept as 1-line forwarders to the four sub-renderers below.
    """

    def __init__(self, scene: TutorialScene) -> None:
        self._scene = scene
        self._background = BackgroundRenderer(scene)
        self._effects = EffectRenderer(scene)
        self._entities = EntityRenderer(scene, self._effects)
        self._ui = UIRenderer(scene)

    def render(self, surface: pygame.Surface) -> None:
        """Full render pass — delegates to sub-renderers in order."""
        s = self._scene
        s.clear_buttons()
        self._render_background(surface)

        if s._is_summary_stage():
            self._render_summary(surface)
        else:
            if s._is_base_console_active():
                self._render_base_talent_console(surface)
                self._render_fade(surface)
                return
            self._render_world(surface)
            self._render_stage_overlay(surface)
            self._render_status_bar(surface)
            if s._stage.id == "homecoming_base" and s._base_sub_phase == "depart":
                self._render_homecoming_depart_transition(surface)

        self._render_skip_button(surface)
        self._render_fade(surface)
        self._render_stage_title_card(surface)

    # -- Background / world / stage-prop dispatch ------------------------

    def _render_background(self, surface):
        self._background.render(surface)

    def _render_world(self, surface):
        s = self._scene
        self._render_stage_props(surface)
        if s._stage.id == "homecoming_base" and s._base_sub_phase != "combat":
            return
        self._entities.render_world(surface)

    def _render_stage_props(self, surface):
        s = self._scene
        if s._stage.id == "mothership_docking":
            self._render_mothership_components(surface)
            self._render_tutorial_explosions(surface)
        elif s._stage.id == "boost_phase_dash":
            self._render_boost_gate(surface)
        elif s._stage.id == "boss_encounter" and s._boss is None and s._escape_timer > 0:
            self._render_escape_countdown(surface)

    # -- Entity layer ----------------------------------------------------

    def _render_player(self, surface):
        self._entities.render_player(surface)

    def _draw_entity_health_bar(self, surface, rect, ratio):
        self._entities._draw_entity_health_bar(surface, rect, ratio)

    def _draw_boss_health(self, surface, boss):
        self._entities._draw_boss_health(surface, boss)

    # -- UI panels (overlay / status / summary / cards / buttons) --------

    def _render_stage_overlay(self, surface):
        self._ui.render_stage_overlay(surface)

    def _render_status_bar(self, surface):
        self._ui.render_status_bar(surface)

    def _render_health_battery(self, surface):
        self._ui.render_health_battery(surface)

    def _render_summary(self, surface):
        self._ui.render_summary(surface)

    def _render_stage_title_card(self, surface):
        self._ui.render_stage_title_card(surface)

    def _render_skip_button(self, surface):
        self._ui.render_skip_button(surface)

    def _render_base_talent_console(self, surface):
        self._ui.render_base_talent_console(surface)

    def _render_homecoming_depart_transition(self, surface):
        self._ui.render_homecoming_depart_transition(surface)

    def _render_escape_countdown(self, surface):
        self._ui.render_escape_countdown(surface)

    def _render_boost_gate(self, surface):
        self._ui.render_boost_gate(surface)

    # -- Stage prop: mothership + ammo + warning -------------------------

    def _render_mothership_components(self, surface):
        self._ui.render_mothership_components(surface)

    # -- Effects (explosions / fade / boss enrage) -----------------------

    def _render_tutorial_explosions(self, surface):
        self._effects.render_tutorial_explosions(surface)

    def _render_fade(self, surface):
        self._effects.render_fade(surface)

    def _render_boss_enrage_aura(self, surface, boss):
        self._effects.render_boss_enrage_aura(surface, boss)

    def _render_boss_enrage_warning(self, surface, boss):
        self._effects.render_boss_enrage_warning(surface, boss)

    # -- Internal helpers (kept for any external/test callers) ----------

    def _draw_bar(self, surface, rect, ratio, fill_color):
        self._ui._draw_bar(surface, rect, ratio, fill_color)

    def _current_stage_instructions(self):
        return self._ui._current_stage_instructions()

    def _objective_counter_text(self):
        return self._ui._objective_counter_text()

    def _stage_hold_ratio(self):
        return self._ui._stage_hold_ratio()
