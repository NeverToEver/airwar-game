"""Simulated player for the tutorial scene.

Phase 4 Wave α: extracted from :mod:`airwar.scenes.tutorial_scene`
to slim the god class. The simulator owns the simulated player
rectangle, energy/health state, boost/dash timers, and per-frame
update logic. The :class:`airwar.scenes.tutorial_scene.TutorialScene`
keeps a 1-line forwarder to a single :class:`TutorialPlayer` instance
and exposes its attributes as scene attributes so existing tests
and the renderer (which read ``scene._player``, ``scene._player_health``,
etc.) keep working unchanged.
"""

from __future__ import annotations

import pygame

from airwar.config import get_screen_height, get_screen_width


class TutorialPlayer:
    """Simulated player for the tutorial scene.

    Wraps the simulated player rectangle, health/energy bars, and
    the boost/dash timers. Reads and writes state directly on the
    scene so the rest of the tutorial code (renderer, aim assist,
    collision handler) can keep using ``scene._player``,
    ``scene._player_health``, etc.
    """

    def __init__(self, scene) -> None:
        self._scene = scene
        self._rect: pygame.Rect | None = None

    def initialise(self) -> None:
        """Build the rect at the bottom-center spawn point."""
        scene = self._scene
        scene._player = pygame.Rect(
            get_screen_width() // 2 - scene.PLAYER_W // 2,
            get_screen_height() - 126,
            scene.PLAYER_W,
            scene.PLAYER_H,
        )
        scene._player_health = 100
        scene._player_max_health = 100
        scene._player_energy = scene.ENERGY_MAX
        scene._player_hit_cooldown = 0
        scene._dash_frames = 0
        scene._dash_velocity = pygame.Vector2(0, 0)
        scene._fire_timer = 0

    def reset_to_spawn(self) -> None:
        """Recentre the player and refill energy/dash (used by ``_load_stage``)."""
        scene = self._scene
        sw = get_screen_width()
        sh = get_screen_height()
        scene._player.center = (sw // 2, sh - 112)
        scene._player_health = scene._player_max_health
        scene._player_energy = scene.ENERGY_MAX
        scene._dash_frames = 0
        scene._dash_velocity.update(0, 0)

    def update(self) -> None:
        """One frame: dash ticks OR movement + energy, then fire."""
        scene = self._scene
        if scene._dash_frames > 0:
            scene._player.x += int(scene._dash_velocity.x)
            scene._player.y += int(scene._dash_velocity.y)
            scene._dash_frames -= 1
        else:
            direction = scene._movement_direction()
            speed = scene.PLAYER_SPEED
            if scene._boost_held() and scene._player_energy > 0:
                speed *= scene.BOOST_MULT
                scene._player_energy = max(0, scene._player_energy - scene.ENERGY_DRAIN)
            else:
                scene._player_energy = min(scene.ENERGY_MAX, scene._player_energy + scene.ENERGY_RECOVER)
            scene._player.x += int(direction.x * speed)
            scene._player.y += int(direction.y * speed)

        sw = get_screen_width()
        sh = get_screen_height()
        scene._player.clamp_ip(pygame.Rect(0, 128, sw, sh - 128))
        scene._update_player_fire()

    def fire(self) -> None:
        """Spawn two wing-muzzle bullets aimed at ``_aim_pos``."""
        scene = self._scene
        scene._fire_timer -= 1
        if scene._fire_timer > 0:
            return
        scene._fire_timer = scene.FIRE_INTERVAL

        from airwar.scenes.tutorial_scene import TutorialBullet  # local import: avoid cycle

        aim_direction = pygame.Vector2(
            scene._aim_pos[0] - scene._player.centerx,
            scene._aim_pos[1] - scene._player.centery,
        )
        aim_direction = pygame.Vector2(0, -1) if aim_direction.length_squared() <= 1 else aim_direction.normalize()
        right = pygame.Vector2(-aim_direction.y, aim_direction.x)
        forward = aim_direction

        for offset_x in scene.WING_MUZZLE_X_OFFSETS:
            muzzle = pygame.Vector2(scene._player.center) + right * offset_x + forward * abs(scene.WING_MUZZLE_Y_OFFSET)
            bullet_rect = pygame.Rect(0, 0, 10, 18)
            bullet_rect.center = (round(muzzle.x), round(muzzle.y))
            scene._bullets.append(
                TutorialBullet(
                    rect=bullet_rect,
                    velocity=aim_direction * 13.0,
                    owner="player",
                    damage=scene.PLAYER_BULLET_DAMAGE,
                )
            )


__all__ = ["TutorialPlayer"]
