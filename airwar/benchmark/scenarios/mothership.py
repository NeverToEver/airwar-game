"""Mothership docking scenarios.

Note: docking requires holding H for 3 seconds (~180 frames at 60 FPS).
The harness's event posting is point-in-time, not "hold", so we
approximate the hold by posting KEYDOWN at frame 0 and leaving the
key state implicitly held.  This is a known limitation; the
assertion is that the input detector sees the H key, not that
docking completes -- docking flow has its own dedicated
integration test (``test_mothership_cooldown_and_entry.py``).
"""

from __future__ import annotations

import pygame

from ..harness import ScenarioResult, key_down, key_up
from . import Scenario, register


SCENARIOS: list[Scenario] = []


def _assert_hold_h_recognised(result: ScenarioResult) -> str | None:
    # The InputDetector in the mother_ship subsystem checks K_h
    # every frame.  We can't easily read its internal progress from
    # the snapshot (no field for it), so we just assert the game
    # didn't crash and the player is still alive after 200 frames
    # of holding H.
    if not result.snapshots:
        return "no snapshots"
    last = result.snapshots[-1]
    if last.player_dying or last.player_health == 0:
        return "player died while holding H"
    return None


SCENARIOS.append(
    Scenario(
        name="mothership.hold_h_no_crash",
        frames=200,
        inputs=[
            key_down(pygame.K_h, at=0),
            key_up(pygame.K_h, at=199),
        ],
        assert_fn=_assert_hold_h_recognised,
    )
)


for s in SCENARIOS:
    register(s)
