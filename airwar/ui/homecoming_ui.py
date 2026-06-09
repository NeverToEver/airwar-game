"""Homecoming UI -- return-to-base progress and cinematic overlay.

Coordinator that owns five phase renderers (one per cinematic phase) and
dispatches ``render_sequence`` to the active phase. Phase renderers live
under ``airwar.ui.homecoming`` and are self-contained; each one only knows
about its own phase.
"""

import math

import pygame

from airwar.config.design_tokens import SystemLayout
from airwar.ui.chamfered_panel import draw_chamfered_panel
from airwar.ui.homecoming import (
    PHASE_APPROACH,
    PHASE_BASE_LAUNCH,
    PHASE_BLACKOUT,
    PHASE_FTL_ESCAPE,
    PHASE_HANDOFF,
    PHASE_LANDING,
    PHASE_ORBITAL_STRIKE,
    PHASE_RETURN_BLACKOUT,
    PHASE_STATION_REVEAL,
    ApproachCameraRenderer,
    BlackoutTransitionRenderer,
    FtlAnimationRenderer,
    LandingHandoffRenderer,
    StationRevealRenderer,
)
from airwar.utils.fonts import get_cjk_font

__all__ = [
    "PHASE_APPROACH",
    "PHASE_BASE_LAUNCH",
    "PHASE_BLACKOUT",
    "PHASE_FTL_ESCAPE",
    "PHASE_HANDOFF",
    "PHASE_LANDING",
    "PHASE_ORBITAL_STRIKE",
    "PHASE_RETURN_BLACKOUT",
    "PHASE_STATION_REVEAL",
    "HomecomingUI",
]


class HomecomingUI:
    """Renders hold progress and the return-to-base cinematic."""

    FTL_EXIT_FLASH_ALPHA_MAX = 42
    LAUNCH_CORRIDOR_PULSE_CYCLES = 1.5
    LAUNCH_CORRIDOR_LINE_ALPHA_BASE = 92
    LAUNCH_CORRIDOR_LINE_ALPHA_RANGE = 24
    LAUNCH_CORRIDOR_RING_ALPHA_RATIO_BASE = 0.72
    LAUNCH_CORRIDOR_RING_ALPHA_RATIO_RANGE = 0.18

    def __init__(self, screen_width: int, screen_height: int):
        # screen_height is intentionally unused (kept for signature compatibility
        # with existing tests / call sites that pass it). See STRUCTURE.md.
        del screen_height
        self._screen_width = screen_width
        self._visible = False
        self._progress = 0.0
        self._animation_time = 0
        self._bar_width = SystemLayout.HOMECOMING_BAR_W
        self._bar_height = SystemLayout.HOMECOMING_BAR_H
        self._font = get_cjk_font(18)
        self._small_font = get_cjk_font(15)

        self._ftl = FtlAnimationRenderer()
        self._blackout = BlackoutTransitionRenderer()
        self._station = StationRevealRenderer()
        self._approach = ApproachCameraRenderer()
        self._landing = LandingHandoffRenderer()

    def show(self) -> None:
        self._visible = True

    def hide(self) -> None:
        self._visible = False
        self._progress = 0.0

    def update_progress(self, progress: float) -> None:
        self._progress = max(0.0, min(1.0, progress))
        self._animation_time += 1

    def render_progress(self, surface: pygame.Surface) -> None:
        if not self._visible or self._progress <= 0:
            return

        center_x = self._screen_width // 2
        center_y = SystemLayout.HOMECOMING_BAR_Y
        bar_x = center_x - self._bar_width // 2
        bar_y = center_y - self._bar_height // 2
        pulse = 0.5 + 0.5 * math.sin(self._animation_time * 0.18)

        label = self._font.render("返航引擎预热", True, (220, 235, 255))
        hint = self._small_font.render("按住 B 启动基地返航", True, (142, 165, 190))
        surface.blit(label, label.get_rect(center=(center_x, center_y - SystemLayout.HOMECOMING_LABEL_OFFSET)))
        surface.blit(hint, hint.get_rect(center=(center_x, center_y + SystemLayout.HOMECOMING_HINT_OFFSET)))

        draw_chamfered_panel(
            surface,
            bar_x,
            bar_y,
            self._bar_width,
            self._bar_height,
            (12, 20, 34),
            (90, 130, 170),
            None,
            5,
        )

        fill_width = int((self._bar_width - SystemLayout.HOMECOMING_BAR_INSET_X) * self._progress)
        if fill_width <= 0:
            return

        fill = pygame.Surface((fill_width, self._bar_height - SystemLayout.HOMECOMING_BAR_INSET_Y), pygame.SRCALPHA)
        color = (210, 236, 255, 195 + int(45 * pulse))
        pygame.draw.rect(fill, color, fill.get_rect(), border_radius=4)
        surface.blit(fill, (bar_x + 2, bar_y + 2))

    def render_sequence(self, surface: pygame.Surface, sequence, player) -> None:
        if not sequence.is_active() and not sequence.is_complete():
            return

        phase = self._phase_key(sequence.phase)
        progress = sequence.get_phase_progress()

        if phase == PHASE_FTL_ESCAPE:
            self._ftl.render(surface, sequence, player, progress)
            return

        if phase in (PHASE_BLACKOUT, PHASE_RETURN_BLACKOUT):
            self._blackout.render(surface, phase, progress)
            return

        if phase == PHASE_ORBITAL_STRIKE:
            self._approach.render_orbital_strike(surface, sequence, progress)
            return

        self._station.render(surface, phase, progress, sequence)

        if phase == PHASE_BASE_LAUNCH:
            self._approach.render_launch_corridor(surface, sequence, progress)
            self._approach.render_launch_player(surface, sequence, player, progress)

        if phase in (PHASE_APPROACH, PHASE_LANDING, PHASE_HANDOFF):
            if phase == PHASE_APPROACH:
                self._approach.render_approach(surface, sequence, player, progress)
            else:
                if phase == PHASE_HANDOFF:
                    self._landing.render_docking_corridor(surface, sequence, progress)
                self._landing.render_landing_player(surface, sequence, player, progress, phase)

        if phase == PHASE_HANDOFF:
            self._landing.render_handoff(surface, progress)

        self._landing.render_fade_overlay(surface, phase, progress)

    # ---- backward-compat forwarders ------------------------------------------
    # Phase renderers now own the actual logic; these methods stay so that
    # existing call sites (and tests) that reference them by name continue
    # to work.

    @staticmethod
    def _phase_key(phase) -> str:
        return getattr(phase, "value", str(phase))

    def _render_ftl_escape(self, surface, sequence, player, progress):
        self._ftl.render(surface, sequence, player, progress)

    def _render_ftl_exit_transition(self, surface, progress):
        self._ftl.render_exit_transition(surface, progress)

    def _render_blackout_bridge(self, surface, progress):
        self._blackout._render_blackout_bridge(surface, progress)

    def _render_return_blackout(self, surface, progress):
        self._blackout._render_return_blackout(surface, progress)

    def _render_orbital_strike(self, surface, sequence, progress):
        self._approach.render_orbital_strike(surface, sequence, progress)

    def _render_deep_space(self, surface, phase, progress):
        self._station._render_deep_space(surface, phase, progress)

    def _render_asteroid_belt(self, surface, phase, progress):
        self._station._render_asteroid_belt(surface, phase, progress)

    def _render_space_station(self, surface, phase, progress, sequence):
        self._station._render_space_station(surface, phase, progress, sequence)

    def _asteroid_points(self, x, y, size, seed):
        return self._station._asteroid_points(x, y, size, seed)

    def _render_landing_player(self, surface, sequence, player, progress):
        phase = self._phase_key(sequence.phase)
        self._landing.render_landing_player(surface, sequence, player, progress, phase)

    def _render_launch_corridor(self, surface, sequence, progress):
        self._approach.render_launch_corridor(surface, sequence, progress)

    def _render_launch_player(self, surface, sequence, player, progress):
        self._approach.render_launch_player(surface, sequence, player, progress)

    def _render_docking_corridor(self, surface, sequence, progress):
        self._landing.render_docking_corridor(surface, sequence, progress)

    def _render_handoff(self, surface, progress):
        self._landing.render_handoff(surface, progress)

    def _render_fade_overlay(self, surface, phase, progress):
        self._landing.render_fade_overlay(surface, phase, progress)
