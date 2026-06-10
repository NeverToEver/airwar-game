"""Tutorial entity dataclasses — the leaf types shared by every tutorial
subsystem.

Why this module exists
----------------------
Before M-4, the dataclasses (``TutorialEnemy``, ``TutorialBullet``,
``TutorialExplosion``, ``TutorialBoss``) were defined in
``tutorial_scene.py``. That created a circular dependency: the
``airwar.scenes.tutorial`` subpackage (sim files, entity helpers,
renderers) needs these dataclasses, but ``tutorial_scene.py`` itself
imports the subpackage. The workaround was 13 method-level
``from airwar.scenes.tutorial_scene import ...`` calls that hid the
real cause and broke ``ruff``'s local-import rule.

M-4 lifts the dataclasses out into this leaf module. Both
``tutorial_scene.py`` (re-exports for backward compat) and every file
under ``airwar/scenes/tutorial/`` can now ``from .entities_core import
...`` at module level — no cycles, no local imports.

Adding a new tutorial entity dataclass
--------------------------------------
Add it here, NOT in ``tutorial_scene.py``. If a new file in
``airwar/scenes/tutorial/`` needs the type, it can import it at the top
of the file.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame


@dataclass
class TutorialEnemy:
    rect: pygame.Rect
    health: int
    max_health: int
    speed: float
    score_value: int
    kind: str = "target"
    active: bool = True
    phase: float = 0.0
    fire_timer: int = 0


@dataclass
class TutorialBullet:
    rect: pygame.Rect
    velocity: pygame.Vector2
    owner: str
    damage: int
    bullet_type: str = "single"
    active: bool = True


@dataclass
class TutorialExplosion:
    center: tuple[int, int]
    timer: int = 28
    duration: int = 28


@dataclass
class TutorialBoss:
    rect: pygame.Rect
    health: int
    max_health: int
    active: bool = True
    phase: float = 0.0
    fire_timer: int = 0
    enraged: bool = False


__all__ = [
    "TutorialBoss",
    "TutorialBullet",
    "TutorialEnemy",
    "TutorialExplosion",
]
