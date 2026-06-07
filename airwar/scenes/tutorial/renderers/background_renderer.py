"""Background rendering for the tutorial scene.

Handles the starfield / gradient / panel base that lives behind every
other tutorial visual. The actual background is owned by
``GameRenderer.background_renderer``; this module only handles lazy
initialisation and the fallback solid fill.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from airwar.config.design_tokens import SceneColors

if TYPE_CHECKING:
    from airwar.scenes.tutorial_scene import TutorialScene


class BackgroundRenderer:
    """Draws the tutorial scene background.

    Lazily constructs a ``GameRenderer`` (with HUD disabled) the first
    time it sees a new surface size, then delegates the draw to its
    background sub-renderer. Falls back to a solid panel fill when no
    GameRenderer is available.
    """

    def __init__(self, scene: TutorialScene) -> None:
        self._scene = scene

    def render(self, surface: pygame.Surface) -> None:
        """Render the background layer onto ``surface``."""
        s = self._scene
        sw, sh = surface.get_width(), surface.get_height()
        if s._game_renderer is None:
            from airwar.game.rendering import GameRenderer

            s._game_renderer = GameRenderer(use_integrated_hud=False)
            s._game_renderer.init_background(sw, sh)
            s._background_size = (sw, sh)

        if s._background_size != (sw, sh):
            s._game_renderer.init_background(sw, sh)
            s._background_size = (sw, sh)

        background = s._game_renderer.background_renderer
        if background:
            background.update()
            background.draw(surface)
        else:
            surface.fill(SceneColors.BG_PRIMARY)
