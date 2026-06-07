"""Simulated enemy helpers for the tutorial scene.

Phase 4 Wave α: extracted from :mod:`airwar.scenes.tutorial_scene`
to slim the god class. Owns the per-frame enemy drift (sine
pattern), the firing-on-cooldown logic, and the three spawn-wave
factories used by ``_load_stage`` (training targets, easy wave,
homecoming wave). The :class:`airwar.scenes.tutorial_scene.TutorialScene`
keeps 1-line forwarders to a single :class:`TutorialEnemySim` instance.
"""

from __future__ import annotations

import math

import pygame

from airwar.config import get_screen_height, get_screen_width


class TutorialEnemySim:
    """Per-frame enemy drift + spawn factories.

    The :class:`~airwar.scenes.tutorial_scene.TutorialEnemy`
    dataclass itself stays defined alongside the scene (where the
    collision code reads it). This simulator only writes into the
    scene's ``_enemies`` list and ticks them.
    """

    def __init__(self, scene) -> None:
        self._scene = scene

    def spawn_training_targets(self) -> None:
        """Spawn the three training targets used by the movement/aim stage."""
        from airwar.scenes.tutorial_scene import TutorialEnemy  # avoid cycle

        scene = self._scene
        sw = get_screen_width()
        y = max(230, int(get_screen_height() * 0.30))
        for index, x_ratio in enumerate((0.28, 0.50, 0.72)):
            rect = pygame.Rect(0, 0, scene.ENEMY_SIZE, scene.ENEMY_SIZE)
            rect.center = (int(sw * x_ratio), y + (index % 2) * 56)
            scene._enemies.append(
                TutorialEnemy(
                    rect=rect,
                    health=34,
                    max_health=34,
                    speed=0.25,
                    score_value=75,
                    kind="target",
                    phase=index * 1.7,
                )
            )
            scene._stage_spawned += 1

    def spawn_easy_enemy_wave(self, *, initial: bool) -> None:
        """Spawn a 1-enemy wave (or a 3-enemy initial wave) for combat basics."""
        from airwar.scenes.tutorial_scene import TutorialEnemy  # avoid cycle

        scene = self._scene
        spawn_slots = 3 if initial else 1
        sw = get_screen_width()
        for _ in range(spawn_slots):
            if scene._stage_spawned >= scene._stage.objective_count:
                return
            lane = scene._stage_spawned % 5
            rect = pygame.Rect(0, 0, scene.ENEMY_SIZE, scene.ENEMY_SIZE)
            rect.center = (
                int(sw * (0.18 + lane * 0.16)),
                220 + (lane % 2) * 62,
            )
            scene._enemies.append(
                TutorialEnemy(
                    rect=rect,
                    health=44,
                    max_health=44,
                    speed=0.65,
                    score_value=110,
                    kind="enemy",
                    phase=scene._stage_spawned * 1.2,
                    fire_timer=40 + lane * 15,
                )
            )
            scene._stage_spawned += 1

    def spawn_homecoming_enemy_wave(self) -> None:
        """Spawn the homecoming-stage enemy wave (4 staggered lanes)."""
        from airwar.scenes.tutorial_scene import TutorialEnemy  # avoid cycle

        scene = self._scene
        for index, lane in enumerate((0, 1, 3, 4)):
            rect = pygame.Rect(0, 0, scene.ENEMY_SIZE, scene.ENEMY_SIZE)
            rect.center = (
                int(get_screen_width() * (0.18 + lane * 0.16)),
                214 + (index % 2) * 66,
            )
            scene._enemies.append(
                TutorialEnemy(
                    rect=rect,
                    health=44,
                    max_health=44,
                    speed=0.55,
                    score_value=110,
                    kind="enemy",
                    phase=index * 1.2,
                    fire_timer=45 + index * 18,
                )
            )
        scene._stage_spawned = len(scene._enemies)

    def update(self) -> None:
        """Drift enemies in their sine pattern; fire on cooldown."""
        scene = self._scene
        for enemy in scene._enemies:
            if not enemy.active:
                continue
            enemy.phase += 0.035
            enemy.rect.x += int(math.sin(enemy.phase) * enemy.speed)
            if enemy.kind == "enemy":
                enemy.rect.y += int(math.sin(enemy.phase * 0.7) * 0.55)
                enemy.fire_timer -= 1
                if enemy.fire_timer <= 0:
                    enemy.fire_timer = 92
                    scene._spawn_enemy_bullet(enemy.rect.center, damage=6)


__all__ = ["TutorialEnemySim"]
