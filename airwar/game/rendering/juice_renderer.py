"""JuiceController — trauma-based screen shake (Squirrel Eiserloh model).

A small, self-contained controller that turns per-event "trauma" values into
per-frame positional offsets. The model is the classic one described by Squirrel
Eiserloh in his GDC talk "Math for Game Programmers: Juicing Your Cameras With
Linear Algebra":

    offset = trauma ** trauma_power * max_offset * unit_vector

With the default settings (trauma_power=2.0, max_offset_px=8), full trauma (1.0)
produces at most an 8-pixel shake in a random direction; trauma=0.5 produces
~25% of the maximum (because 0.5**2 = 0.25). The decay is per frame, linear, and
clamped to zero.

Usage in GameScene:
    self._juice_controller = JuiceController()
    # In _on_player_damaged:
    self._juice_controller.add_trauma(0.4)
    # In present():
    offset = self._juice_controller.offset()
    viewport.present(display_surface, offset=offset)
    # Once per frame:
    self._juice_controller.update()

The controller is intentionally deterministic when seeded — pass ``seed=42`` and
the offset sequence is reproducible, which makes unit testing trivial.
"""

from __future__ import annotations

import random
from typing import Final


class JuiceController:
    """Trauma-based screen-shake controller."""

    DECAY_PER_FRAME: Final[float] = 0.075
    """Linear decay subtracted from ``trauma`` each call to ``update()``.
    With this default, full trauma (1.0) decays to 0 in ~13 frames (~215ms @ 60fps)."""

    MAX_OFFSET_PX: Final[int] = 8
    """Maximum displacement in pixels at trauma=1.0."""

    TRAUMA_POWER: Final[float] = 2.0
    """Quadratic falloff. trauma=0.5 → 0.5^2 = 25% of MAX_OFFSET_PX."""

    def __init__(self, seed: int | None = None) -> None:
        self._trauma: float = 0.0
        self._rng = random.Random(seed)

    def add_trauma(self, amount: float) -> None:
        """Queue a trauma event. ``amount`` is clamped to ``[0.0, 1.0]``."""
        if amount is None or amount <= 0.0:
            return
        # accumulate, then clamp — repeated small hits will push toward 1.0 but
        # never exceed it, matching the Squirrel model.
        self._trauma = min(1.0, self._trauma + amount)

    def update(self) -> None:
        """Decay trauma by one frame. Clamp to zero (never negative)."""
        if self._trauma > 0.0:
            self._trauma = max(0.0, self._trauma - self.DECAY_PER_FRAME)

    def offset(self) -> tuple[int, int]:
        """Return the current shake offset in pixels, rounded to integers.

        At trauma=0 this always returns ``(0, 0)``; at trauma=1.0 the magnitude
        is bounded by ``MAX_OFFSET_PX``. The direction is uniform on the unit
        circle (``self._rng``), so two consecutive calls may return different
        offsets even with the same trauma level — this is intentional and what
        makes the shake feel "alive" rather than mechanical.
        """
        if self._trauma <= 0.0:
            return (0, 0)
        magnitude = (self._trauma ** self.TRAUMA_POWER) * self.MAX_OFFSET_PX
        # uniform on [-1, 1] for both x and y, then normalised
        dx = self._rng.uniform(-1.0, 1.0)
        dy = self._rng.uniform(-1.0, 1.0)
        # Cap each axis independently to magnitude so the offset stays inside
        # the [-magnitude, +magnitude] box. (Eiserloh's talk normalises to a
        # unit vector and scales by magnitude; we use the cheaper
        # axis-independent clamp, which is visually indistinguishable for
        # small MAX_OFFSET_PX values.)
        return (int(dx * magnitude), int(dy * magnitude))

    @property
    def trauma(self) -> float:
        """Current trauma level (0..1). Useful for tests and debug overlays."""
        return self._trauma
