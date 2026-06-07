"""Leaderboard overlay: top-level toggle, fetch, and panel render.

Wraps the existing ``LeaderboardView`` widget with show/hide state and a
custom close button so the welcome scene can mount it without owning the
view's lifecycle directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pygame

from airwar.config.design_tokens import SceneColors
from airwar.ui.leaderboard_view import LeaderboardView

if TYPE_CHECKING:
    pass


class LeaderboardOverlay:
    """Show/hide + render coordinator for the leaderboard panel."""

    def __init__(self, scene: Any) -> None:
        self._scene = scene
        self._view: LeaderboardView | None = None

    def open(self) -> None:
        self._scene.show_leaderboard = True

    def close(self) -> None:
        self._scene.show_leaderboard = False

    def render(self, surface: pygame.Surface, sw: int, sh: int) -> None:
        """Render the leaderboard panel and a close button on top."""
        SC = SceneColors
        scene = self._scene

        # Dim overlay
        dim = pygame.Surface((sw, sh), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 140))
        surface.blit(dim, (0, 0))

        if self._view is None:
            self._view = LeaderboardView(scene.db)
        self._view.render(surface, sw, sh)

        # Close button at top-right of the panel
        close_size = 36
        panel_w = LeaderboardView.PANEL_W
        panel_x = (sw - panel_w) // 2
        panel_y = (sh - LeaderboardView.PANEL_H) // 2
        close_rect = pygame.Rect(
            panel_x + panel_w - close_size - 12,
            panel_y + 12,
            close_size,
            close_size,
        )
        scene.register_button("leaderboard_close", close_rect)
        hover = scene.is_button_hovered("leaderboard_close")
        close_color = SC.GOLD_PRIMARY if hover else SC.TEXT_DIM
        x_surf = scene.title_font.render("×", True, close_color)
        surface.blit(x_surf, x_surf.get_rect(center=close_rect.center))
