"""Tests for spatial-hash query re-entrancy.

Bug: ``CollisionController._get_entities_in_cells`` shared one dedup set
(``_query_seen``) across all query generators, cleared on first ``next()``.
A nested query running while an outer generator was paused at a ``yield``
would clear the outer's dedup state, letting the outer re-yield an entity it
had already yielded — e.g. double splash damage in explosion loops. Each
query generator must own its dedup state.
"""

from types import SimpleNamespace

import pygame

from airwar.game.managers.collision_controller import CollisionController


def test_nested_query_does_not_corrupt_outer_dedup():
    controller = CollisionController()
    shared = SimpleNamespace(active=True)
    other = SimpleNamespace(active=True)
    cells = {
        (0, 0): [shared],
        (1, 0): [shared],  # same entity spans two cells
        (5, 5): [other],
    }
    outer_rect = pygame.Rect(0, 0, 150, 50)  # cells (0, 0) and (1, 0)
    inner_rect = pygame.Rect(500, 500, 50, 50)  # cell (5, 5)

    outer = controller._get_entities_in_cells(cells, outer_rect)
    first = next(outer)
    assert first is shared

    # A nested query runs to completion while the outer one is paused.
    assert list(controller._get_entities_in_cells(cells, inner_rect)) == [other]

    # The outer query must not re-yield the shared entity from its second cell.
    assert list(outer) == []


def test_query_dedups_entity_spanning_cells():
    controller = CollisionController()
    shared = SimpleNamespace(active=True)
    cells = {(0, 0): [shared], (1, 0): [shared]}
    rect = pygame.Rect(0, 0, 150, 50)

    assert list(controller._get_entities_in_cells(cells, rect)) == [shared]
