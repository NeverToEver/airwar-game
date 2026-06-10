"""Simulated boss for the tutorial scene.

Phase 4 Wave α: extracted from :mod:`airwar.scenes.tutorial_scene`
to slim the god class. The boss simulator owns the per-frame
horizontal-sway movement, the 30% enrage threshold, and the spread
attack pattern. The :class:`airwar.scenes.tutorial_scene.TutorialScene`
keeps a 1-line forwarder to a single :class:`TutorialBoss` instance.
"""

from __future__ import annotations

import math

import pygame

from airwar.config import get_screen_width
from airwar.scenes.tutorial.entities_core import TutorialBoss as _BossDataclass
from airwar.scenes.tutorial.entities_core import TutorialBullet


class TutorialBoss:
    """Simulated boss for the tutorial scene.

    The tutorial boss is a thin top-of-screen target: it sways
    horizontally, then drops down to 30% HP and starts firing
    a 5-bullet spread. When it dies, the scene sets ``scene._boss``
    back to ``None`` and arms ``scene._escape_timer``.

    Both the boss dataclass and the bullet dataclass are imported from
    the leaf :mod:`airwar.scenes.tutorial.entities_core` module (M-4)
    so this file no longer needs method-level local imports to dodge
    the ``tutorial_scene`` cycle.
    """

    def __init__(self, scene) -> None:
        self._scene = scene

    def spawn(self) -> None:
        """Build the boss rect at the top of the screen."""
        scene = self._scene
        rect = pygame.Rect(0, 0, scene.BOSS_W, scene.BOSS_H)
        rect.center = (get_screen_width() // 2, 246)
        scene._boss = _BossDataclass(rect=rect, health=280, max_health=280)

    def update(self) -> None:
        """Animate the boss (sway + enrage threshold) and fire its spread."""
        scene = self._scene
        boss = scene._boss
        if boss is None or not boss.active:
            return

        boss.phase += 0.028
        center_x = get_screen_width() // 2 + int(math.sin(boss.phase) * 170)
        boss.rect.centerx = center_x
        boss.enraged = boss.health <= boss.max_health * scene.BOSS_ENRAGE_THRESHOLD
        boss.fire_timer -= 1
        fire_interval = 22 if boss.enraged else 62
        if boss.fire_timer <= 0:
            boss.fire_timer = fire_interval
            spread = (-0.42, -0.20, 0.0, 0.20, 0.42) if boss.enraged else (-0.16, 0.16)
            for offset in spread:
                direction = pygame.Vector2(offset, 1).normalize()
                scene._enemy_bullets.append(
                    TutorialBullet(
                        rect=pygame.Rect(boss.rect.centerx - 6, boss.rect.bottom - 4, 12, 16),
                        velocity=direction * (6.2 if boss.enraged else 4.4),
                        owner="enemy",
                        damage=9 if boss.enraged else 6,
                        bullet_type="laser" if boss.enraged else "single",
                    )
                )


__all__ = ["TutorialBoss"]
