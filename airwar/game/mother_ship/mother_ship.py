"""Mothership entity — thin coordinator over Motion + Renderer.

Phase 5-γ split: the 580-line monolith is now a facade with 12
1-line public forwarders + 3 backward-compat shims for test
access. All visual logic lives in :class:`MotherShipRenderer`;
all state-and-motion logic lives in :class:`MotherShipMotion`.
"""

import pygame

from airwar.game.mother_ship.mother_ship_motion import MotherShipMotion
from airwar.game.mother_ship.mother_ship_renderer import MotherShipRenderer


class MotherShip:
    """Mothership entity — facade over :class:`MotherShipMotion` and :class:`MotherShipRenderer`.

    Public surface (unchanged from the pre-split version):

    - :meth:`show` / :meth:`hide` / :meth:`is_visible`
    - :meth:`set_position`
    - :meth:`show_phantom` / :meth:`hide_phantom`
    - :meth:`set_player_input`
    - :meth:`activate_flyaway` / :meth:`deactivate_flyaway` / :meth:`is_flyaway_mode`
    - :meth:`get_docking_position`
    - :meth:`update_animation` (kept for any future callers; primary
      use is from :meth:`render`)
    - :meth:`update` — per-frame motion integrator
    - :meth:`render` — visual z-order pipeline

    Test-reachable private members (3 shims preserved):
    - :attr:`_phantom_started_at` (read-only property)
    - :meth:`_get_phantom_reveal` (forwarder)
    - :meth:`_render_phantom` (forwarder)
    """

    def __init__(self, screen_width: int, screen_height: int):
        self._motion = MotherShipMotion(screen_width, screen_height)
        # Renderer takes ``self`` for self-injection (reads motion
        # state via ``self._mother_ship._motion.<attr>``). This is
        # the same pattern as the Phase 5-β boss split.
        self._renderer = MotherShipRenderer(self)

    # ── Public API (1-line forwarders) ────────────────────────────────────

    def show(self) -> None:
        self._motion.show()

    def hide(self) -> None:
        self._motion.hide()

    def is_visible(self) -> bool:
        return self._motion.is_visible()

    def set_position(self, x: int, y: int) -> None:
        self._motion.set_position(x, y)

    def show_phantom(self) -> None:
        self._motion.show_phantom()

    def hide_phantom(self) -> None:
        self._motion.hide_phantom()

    def set_player_input(self, x: int, y: int) -> None:
        self._motion.set_player_input(x, y)

    def activate_flyaway(self) -> None:
        self._motion.activate_flyaway()

    def deactivate_flyaway(self) -> None:
        self._motion.deactivate_flyaway()

    def is_flyaway_mode(self) -> bool:
        return self._motion.is_flyaway_mode()

    def get_docking_position(self) -> tuple:
        return self._motion.get_docking_position()

    def update_animation(self) -> None:
        """Per-frame pulse calc. Kept as a public forwarder; the
        renderer's :meth:`render` calls this internally on the
        motion before drawing.
        """
        self._motion.update_animation()

    def update(self) -> None:
        self._motion.update()

    def render(self, surface: pygame.Surface) -> None:
        self._renderer.render(surface)

    # ── Test shims (Phase 5-γ backward compat) ────────────────────────────

    @property
    def _phantom_visible(self) -> bool:
        """Backward-compat shim: tests read ``mother_ship._phantom_visible``.

        See :attr:`MotherShipMotion._phantom_visible` for the real
        state; the test in ``test_tutorial_scene_mechanics.py``
        (lines 74, 85) asserts on this flag directly.
        """
        return self._motion._phantom_visible

    @property
    def _phantom_started_at(self) -> int:
        """Backward-compat shim: tests read ``mother_ship._phantom_started_at``.

        See :attr:`MotherShipMotion._phantom_started_at` for the real
        state; the test in
        ``test_mothership_cooldown_and_entry.py:176`` calls
        ``show_phantom()`` and then reads this attribute to assert
        the phantom timer was reset.
        """
        return self._motion._phantom_started_at

    def _get_phantom_reveal(self, now_ms: int | None = None) -> float:
        """Backward-compat forwarder (test-reachable at lines 178-180)."""
        return self._renderer._get_phantom_reveal(now_ms)

    def _render_phantom(self, surface: pygame.Surface) -> None:
        """Backward-compat forwarder (test-reachable at line 189)."""
        self._renderer._render_phantom(surface)
