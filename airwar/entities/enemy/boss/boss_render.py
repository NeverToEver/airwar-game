"""Boss rendering helpers — sprite blit, trail, muzzle flash.

The previous implementation had 30+ lines of pygame.draw calls scattered
across ``Boss.update``. This module collects the rendering-related state
(_facing_angle, _muzzle_flash_*, _enrage_trail*) and exposes a single
:meth:`BossRenderer.draw` method.

Rendering touches no game logic; callers simply omit the surface when no
draw target is available.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from ...base import Vector2

if TYPE_CHECKING:
    from .boss import Boss


class BossRenderer:
    """Render-facing state and drawing for the boss."""

    def __init__(self, boss: Boss) -> None:
        self._boss = boss

    # ------------------------------------------------------------------
    # Facing / muzzle helpers
    # ------------------------------------------------------------------

    def face_target(self, target: tuple[float, float]) -> None:
        boss = self._boss
        dx = target[0] - boss.rect.centerx
        dy = target[1] - boss.rect.centery
        if dx == 0 and dy == 0:
            return
        boss._facing_angle = math.degrees(math.atan2(dy, dx))

    def facing_vector(self) -> Vector2:
        boss = self._boss
        radians = math.radians(boss._facing_angle)
        return Vector2(math.cos(radians), math.sin(radians))

    # ------------------------------------------------------------------
    # Trail recording
    # ------------------------------------------------------------------

    def record_enrage_trail(self) -> None:
        boss = self._boss
        boss._enrage_trail.append((boss.rect.centerx, boss.rect.centery))
        from . import ENRAGE_TRAIL_LENGTH

        max_trail = max(
            ENRAGE_TRAIL_LENGTH,
            int(max(boss.rect.width, boss.rect.height) * 3 / 40),
        )
        if len(boss._enrage_trail) > max_trail:
            boss._enrage_trail = boss._enrage_trail[-max_trail:]

    def clear_enrage_trail(self) -> None:
        boss = self._boss
        boss._enrage_trail.clear()
        boss._enrage_trail_ghost = None
        boss._enrage_trail_ghost_key = None
        boss._enrage_trail_render_ghost = None
        boss._enrage_trail_render_ghost_key = None

    # ------------------------------------------------------------------
    # Public draw
    # ------------------------------------------------------------------

    def draw(self, surface) -> None:
        """Draw the boss sprite to ``surface``.

        The trail / muzzle-flash effects are left to the
        :class:`game.rendering.boss_enrage_renderer.BossEnrageRenderer`
        because they read the same fields (``_enrage_trail``,
        ``_muzzle_flash_positions``) directly. Keeping the draw method
        narrow avoids duplicate pygame state.
        """
        boss = self._boss
        if boss._sprite:
            surface.blit(boss._sprite, boss.get_rect())


__all__ = ["BossRenderer"]
