"""Homecoming / base tutorial stage (id ``homecoming_base``).

Two-phase flow driven by ``scene._base_sub_phase``:

1. ``combat`` -- the player must hold B for ``HOME_HOLD_FRAMES``
   frames. Once full the scene starts a fade-out and queues a
   transition to the base interior.
2. ``base`` -- the base talent console takes over input. Picking
   "Continue" sets the sub-phase to ``depart`` and starts the
   ``DEPART_FRAMES`` countdown.

This stage is also responsible for the ``_advance_after_delay``
countdown when the scene marks the stage complete (per the legacy
coordinator).
"""

from __future__ import annotations

import pygame

from .base import BaseStage

HOMECOMING_STAGE_ID = "homecoming_base"


class HomecomingBaseStage(BaseStage):
    """Per-frame homecoming + base sub-stage logic."""

    stage_id: str = HOMECOMING_STAGE_ID

    def update(self) -> None:
        scene = self._scene
        if scene._base_sub_phase == "combat":
            self._update_combat(scene)
        elif scene._base_sub_phase == "depart":
            scene._depart_timer = max(0, scene._depart_timer - 1)

        if scene._stage_completed:
            scene._advance_after_delay()

    @staticmethod
    def _update_combat(scene) -> None:
        if pygame.K_b in scene._keys_down:
            scene._hold_b_frames = min(scene.HOME_HOLD_FRAMES, scene._hold_b_frames + 1)
        else:
            scene._hold_b_frames = max(0, scene._hold_b_frames - 3)

        if scene._hold_b_frames >= scene.HOME_HOLD_FRAMES:
            scene._pending_base_sub_phase = "base"
            scene._fade_phase = "out"
            scene._fade_alpha = 0


__all__ = ["HOMECOMING_STAGE_ID", "HomecomingBaseStage"]
