"""Entity-update helpers extracted from :mod:`tutorial_scene`.

Per-frame entity updates (bullets, enemies, boss, collisions,
cleanup, effects). Pure functions taking the scene as the first
argument. The scene keeps thin wrapper methods so the existing
private test API (e.g. ``scene._update_bullets``,
``scene._handle_collisions``) is preserved.
"""

from __future__ import annotations

import math

import pygame

from airwar.config import get_screen_height, get_screen_width


def spawn_training_targets(scene) -> None:
    """Spawn the three training targets used by the movement/aim stage."""
    sw = get_screen_width()
    y = max(230, int(get_screen_height() * 0.30))
    for index, x_ratio in enumerate((0.28, 0.50, 0.72)):
        rect = pygame.Rect(0, 0, scene.ENEMY_SIZE, scene.ENEMY_SIZE)
        rect.center = (int(sw * x_ratio), y + (index % 2) * 56)
        scene._enemies.append(
            _make_enemy(
                rect=rect,
                health=34,
                speed=0.25,
                score_value=75,
                kind="target",
                phase=index * 1.7,
            )
        )
        scene._stage_spawned += 1


def spawn_easy_enemy_wave(scene, *, initial: bool) -> None:
    """Spawn a 1-enemy wave (or a 3-enemy initial wave) for combat basics."""
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
            _make_enemy(
                rect=rect,
                health=44,
                speed=0.65,
                score_value=110,
                kind="enemy",
                phase=scene._stage_spawned * 1.2,
                fire_timer=40 + lane * 15,
            )
        )
        scene._stage_spawned += 1


def spawn_homecoming_enemy_wave(scene) -> None:
    """Spawn the homecoming-stage enemy wave (4 staggered lanes)."""
    sw = get_screen_width()
    for index, lane in enumerate((0, 1, 3, 4)):
        rect = pygame.Rect(0, 0, scene.ENEMY_SIZE, scene.ENEMY_SIZE)
        rect.center = (
            int(sw * (0.18 + lane * 0.16)),
            214 + (index % 2) * 66,
        )
        scene._enemies.append(
            _make_enemy(
                rect=rect,
                health=44,
                speed=0.55,
                score_value=110,
                kind="enemy",
                phase=index * 1.2,
                fire_timer=45 + index * 18,
            )
        )
    scene._stage_spawned = len(scene._enemies)


def spawn_boss(scene) -> None:
    """Spawn the simplified tutorial boss at the top of the screen."""
    from airwar.scenes.tutorial_scene import TutorialBoss

    sw = get_screen_width()
    rect = pygame.Rect(0, 0, scene.BOSS_W, scene.BOSS_H)
    rect.center = (sw // 2, 246)
    scene._boss = TutorialBoss(rect=rect, health=280, max_health=280)


def spawn_enemy_bullet(scene, center: tuple[int, int], *, damage: int) -> None:
    """Spawn an enemy bullet aimed at the player."""
    from airwar.scenes.tutorial_scene import TutorialBullet

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


def mothership_destroy_nearest_enemy(scene) -> None:
    """Mothership volley: deal 50 dmg to the closest active enemy."""
    from airwar.scenes.tutorial_scene import TutorialExplosion

    active_enemies = [enemy for enemy in scene._enemies if enemy.active]
    if not active_enemies:
        return

    if scene._mothership:
        origin = scene._mothership.get_docking_position()
    else:
        origin = (get_screen_width() // 2, int(get_screen_height() * 0.32))

    target = min(
        active_enemies,
        key=lambda enemy: (
            (enemy.rect.centerx - origin[0]) * (enemy.rect.centerx - origin[0])
            + (enemy.rect.centery - origin[1]) * (enemy.rect.centery - origin[1])
        ),
    )
    target.health -= 50
    if target.health <= 0:
        target.active = False
        scene._score += target.score_value
        scene._kills += 1
        scene._tutorial_explosions.append(TutorialExplosion(target.rect.center))


def update_bullets(scene) -> None:
    """Move every active bullet; deactivate on out-of-bounds."""
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


def update_tutorial_effects(scene) -> None:
    """Tick explosion timers and drop expired explosions."""
    for explosion in scene._tutorial_explosions:
        explosion.timer -= 1
    scene._tutorial_explosions[:] = [
        explosion for explosion in scene._tutorial_explosions if explosion.timer > 0
    ]


def update_enemies(scene) -> None:
    """Drift enemies in their sine pattern; fire on cooldown."""
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
                spawn_enemy_bullet(scene, enemy.rect.center, damage=6)


def update_boss(scene) -> None:
    """Animate the boss (sway + enrage threshold) and fire its spread."""
    from airwar.scenes.tutorial_scene import TutorialBullet

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


def handle_collisions(scene) -> None:
    """Resolve player bullets vs enemies/boss and enemy bullets vs player."""
    for bullet in scene._bullets:
        if not bullet.active:
            continue
        for enemy in scene._enemies:
            if not enemy.active or not bullet.rect.colliderect(enemy.rect):
                continue
            bullet.active = False
            enemy.health -= bullet.damage
            if enemy.health <= 0:
                enemy.active = False
                scene._score += enemy.score_value
                scene._kills += 1
                scene._stage_progress = min(
                    scene._stage.objective_count, scene._stage_progress + 1
                )
            break

        boss = scene._boss
        if (
            bullet.active
            and boss is not None
            and boss.active
            and bullet.rect.colliderect(boss.rect)
        ):
            bullet.active = False
            boss.health -= bullet.damage
            if boss.health <= 0:
                boss.active = False
                scene._score += 500
                scene._kills += 1
                scene._boss = None
                scene._escape_timer = scene.ESCAPE_FRAMES

    vulnerable = scene._stage.id in ("combat_basics", "boss_encounter")
    if not vulnerable:
        return

    for bullet in scene._enemy_bullets:
        if not bullet.active or not bullet.rect.colliderect(scene._player):
            continue
        bullet.active = False
        damage_player(scene, bullet.damage)

    for enemy in scene._enemies:
        if enemy.active and enemy.rect.colliderect(scene._player):
            damage_player(scene, 8)


def damage_player(scene, damage: int) -> None:
    """Apply damage to the player if the hit cooldown has elapsed."""
    if scene._player_hit_cooldown > 0:
        return
    scene._player_hit_cooldown = scene.PLAYER_HIT_COOLDOWN
    scene._player_health = max(20, scene._player_health - damage)


def cleanup_entities(scene) -> None:
    """Drop inactive bullets/enemies from the active lists."""
    scene._bullets[:] = [bullet for bullet in scene._bullets if bullet.active]
    scene._enemy_bullets[:] = [
        bullet for bullet in scene._enemy_bullets if bullet.active
    ]
    scene._enemies[:] = [enemy for enemy in scene._enemies if enemy.active]


# -- Internal helpers ------------------------------------------------

def _make_enemy(
    *,
    rect: pygame.Rect,
    health: int,
    speed: float,
    score_value: int,
    kind: str,
    phase: float,
    fire_timer: int = 0,
):
    """Local factory so the module doesn't pull tutorial_scene at import time."""
    from airwar.scenes.tutorial_scene import TutorialEnemy

    return TutorialEnemy(
        rect=rect,
        health=health,
        max_health=health,
        speed=speed,
        score_value=score_value,
        kind=kind,
        phase=phase,
        fire_timer=fire_timer,
    )


__all__ = [
    "cleanup_entities",
    "damage_player",
    "handle_collisions",
    "mothership_destroy_nearest_enemy",
    "spawn_boss",
    "spawn_easy_enemy_wave",
    "spawn_enemy_bullet",
    "spawn_homecoming_enemy_wave",
    "spawn_training_targets",
    "update_boss",
    "update_bullets",
    "update_enemies",
    "update_tutorial_effects",
]
