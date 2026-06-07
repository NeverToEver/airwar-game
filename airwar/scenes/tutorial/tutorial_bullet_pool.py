"""Bullet pool helpers for the tutorial scene.

Phase 4 Wave α: extracted from :mod:`airwar.scenes.tutorial_scene`
to slim the god class. The bullet pool owns the ``_bullets`` and
``_enemy_bullets`` lists on the scene, the bounds-based ticking
loop, and the enemy bullet spawn helper used by both enemies and
the boss spread. The :class:`airwar.scenes.tutorial_scene.TutorialScene`
keeps thin 1-line forwarders.
"""

from __future__ import annotations

import pygame

from airwar.config import get_screen_height, get_screen_width


class TutorialBulletPool:
    """Per-frame bullet tick + enemy bullet spawn helper.

    The :class:`~airwar.scenes.tutorial_scene.TutorialBullet`
    dataclass itself stays defined alongside the scene (where the
    collision code can read it) -- this pool only manages the
    per-frame movement and the spawn helper that points enemy
    bullets at the player.
    """

    def __init__(self, scene) -> None:
        self._scene = scene

    def update(self) -> None:
        """Move every active bullet; deactivate on out-of-bounds."""
        scene = self._scene
        sw = get_screen_width()
        sh = get_screen_height()
        bounds = pygame.Rect(-120, -120, sw + 240, sh + 240)
        for bullet in scene._bullets + scene._enemy_bullets:
            if not bullet.active:
                continue
            bullet.rect.x += int(bullet.velocity.x)
            bullet.rect.y += int(bullet.velocity.y)
            if not bounds.colliderect(bullet.rect):
                bullet.active = False

    def spawn_enemy_bullet(self, center: tuple[int, int], *, damage: int) -> None:
        """Spawn an enemy bullet aimed at the player."""
        from airwar.scenes.tutorial_scene import TutorialBullet  # avoid cycle

        scene = self._scene
        direction = pygame.Vector2(
            scene._player.centerx - center[0],
            scene._player.centery - center[1],
        )
        direction = (
            pygame.Vector2(0, 1)
            if direction.length_squared() <= 1
            else direction.normalize()
        )
        rect = pygame.Rect(0, 0, 10, 14)
        rect.center = center
        scene._enemy_bullets.append(
            TutorialBullet(
                rect=rect,
                velocity=direction * 4.2,
                owner="enemy",
                damage=damage,
            )
        )


__all__ = ["TutorialBulletPool"]
