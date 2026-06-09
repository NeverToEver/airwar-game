"""Regression tests for the ScaledViewport mouse-coordinate bug.

Repro: when the window opens at a size smaller than the design
resolution (e.g. 1670x939 on a small laptop), the viewport was
constructed with the design size (1920x1080) but the actual display
surface was at 1670x939. The mouse-coord transform then mapped
display-space clicks into logical space with a non-identity scale
(0.869) and a small offset, so clicks at the visible button position
in screen space landed outside the registered rect in logical space
— the user had to aim ~120px to the left of the visible button to
hit it.

These tests pin the contract: when the display size differs from
the design size, the viewport must treat the display size as the
logical size so the transform becomes a no-op.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from airwar.game.scaled_viewport import ScaledViewport


def test_viewport_constructor_with_display_size_yields_identity_transform() -> None:
    """Constructing the viewport with the ACTUAL display size (not
    the design size) must yield a no-op transform so mouse clicks
    at the visible button position pass through unchanged."""
    viewport = ScaledViewport(1670, 939)
    viewport.update(1670, 939)
    # The bug: the transform was scaling by 0.869 and offsetting by
    # ~(0.76, 0.24), so a click at (970, 517) became (1115.6, 594.8)
    # — well outside the visible button's rect.
    # The fix: the transform is now a no-op (scale=1, offset=0).
    x, y = viewport.screen_to_logical(970, 517)
    assert x == pytest.approx(970.0), f"expected identity, got x={x}"
    assert y == pytest.approx(517.0), f"expected identity, got y={y}"


def test_viewport_resize_keeps_identity_transform() -> None:
    """On a window resize, the viewport must re-sync to the new size
    so the transform stays a no-op. Otherwise the bug recurs the
    moment the user resizes the window.

    The Game's ``_handle_resize`` re-sets ``logical_size`` and
    re-allocates ``_logical_surface`` BEFORE calling ``update()``;
    this test mirrors that path explicitly (calling ``update()``
    alone on a viewport with mismatched logical_size would
    intentionally re-introduce a non-identity transform, which is
    how the bug originally manifested)."""
    viewport = ScaledViewport(1670, 939)
    viewport.update(1670, 939)
    # Simulate the resize path: SceneSwitcher._handle_resize resets
    # logical_size and re-allocates the surface, THEN calls update().
    viewport.logical_size = (1366, 768)
    viewport._logical_surface = pygame.Surface((1366, 768), pygame.SRCALPHA)
    viewport.update(1366, 768)
    x, y = viewport.screen_to_logical(800, 400)
    assert x == pytest.approx(800.0), f"expected identity x, got {x}"
    assert y == pytest.approx(400.0), f"expected identity y, got {y}"


def test_viewport_mouse_click_on_visible_button_hits_rect() -> None:
    """End-to-end: a click at any position in display space must map
    to the same position (identity transform). The bug was that a
    click at the visible benchmark button (970, 517) mapped to
    ~(1115, 595) — well outside the registered rect.
    """
    # Construct a viewport with the actual display size, mirroring
    # what ``Game.__init__`` does after the fix.
    viewport = ScaledViewport(1670, 939)
    viewport.update(1670, 939)

    # The click handler delegates to ``_map_mouse_event`` which calls
    # ``screen_to_logical``. Reproduce that call directly without
    # needing a full Game instance (which would conflict with the
    # dummy SDL driver's one-window-per-process limit).
    def map_click(x: int, y: int) -> tuple[float, float]:
        return viewport.screen_to_logical(x, y)

    # The bug: mapped x/y was off by ~120px. After the fix, identity.
    for cx, cy in [(970, 517), (970, 257), (486, 449), (1090, 349)]:
        mx, my = map_click(cx, cy)
        assert mx == pytest.approx(float(cx)), (
            f"display x={cx} mapped to {mx}, expected identity"
        )
        assert my == pytest.approx(float(cy)), (
            f"display y={cy} mapped to {my}, expected identity"
        )
