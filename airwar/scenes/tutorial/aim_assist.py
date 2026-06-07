"""Aim-assist helpers extracted from :mod:`tutorial_scene`.

The aim assist subsumes the per-frame smoothing of the raw mouse
position, target resolution (snap / release / direction-cone), and
distance math. Pure functions taking the scene as the first argument
so they can read/write scene state directly. The scene keeps thin
wrapper methods so the existing private test API
(``scene._update_aim_assist``, ``scene._resolve_aim_assist_target``,
``scene._aim_assist_candidates``, etc.) is preserved.
"""

from __future__ import annotations

import math


def update_aim_assist(scene) -> None:
    """One frame of aim assist: smooth, resolve target, write ``_aim_pos``."""
    update_smoothed_raw_aim_position(scene)
    target = resolve_aim_assist_target(scene)
    scene._aim_pos = target.rect.center if target is not None else scene._smoothed_raw_aim_position


def update_smoothed_raw_aim_position(scene) -> None:
    """Exponentially blend the smoothed aim toward the raw mouse position."""
    sx, sy = scene._smoothed_raw_aim_position
    rx, ry = scene._raw_aim_position
    dx = rx - sx
    dy = ry - sy
    if dx * dx + dy * dy <= scene.AIM_INPUT_SNAP_DISTANCE * scene.AIM_INPUT_SNAP_DISTANCE:
        scene._smoothed_raw_aim_position = scene._raw_aim_position
        return
    scene._smoothed_raw_aim_position = (
        sx + dx * scene.AIM_INPUT_DELAY_BLEND,
        sy + dy * scene.AIM_INPUT_DELAY_BLEND,
    )


def resolve_aim_assist_target(scene):
    """Pick the active enemy/boss the auto-aim should snap to (or None)."""
    if scene._stage.id not in ("movement_aiming", "combat_basics", "boss_encounter"):
        scene._aim_assist_target = None
        return None

    raw_x, raw_y = scene._smoothed_raw_aim_position
    candidates = aim_assist_candidates(scene)
    if not candidates:
        scene._aim_assist_target = None
        return None

    movement = raw_aim_movement(scene)
    movement_len_sq = movement[0] * movement[0] + movement[1] * movement[1]
    if movement_len_sq >= scene.AIM_ASSIST_RELEASE_DISTANCE * scene.AIM_ASSIST_RELEASE_DISTANCE:
        scene._aim_assist_target = None
        scene._aim_assist_release_timer = scene.AIM_ASSIST_RELEASE_FRAMES
        return None

    if scene._aim_assist_release_timer > 0:
        scene._aim_assist_release_timer -= 1
        scene._aim_assist_target = None
        return None

    if movement_len_sq >= scene.AIM_ASSIST_SWITCH_DISTANCE * scene.AIM_ASSIST_SWITCH_DISTANCE:
        directional_target = target_in_movement_direction(scene, candidates, movement)
        if directional_target is not None:
            scene._aim_assist_target = directional_target
            return directional_target
        if scene._aim_assist_target in candidates:
            return scene._aim_assist_target

    if scene._aim_assist_target in candidates and is_aim_assist_locked(scene, scene._aim_assist_target, raw_x, raw_y):
        return scene._aim_assist_target

    for target in candidates:
        if target.rect.collidepoint(raw_x, raw_y):
            scene._aim_assist_target = target
            return target

    target = min(
        candidates,
        key=lambda candidate: distance_sq_to_target(candidate, raw_x, raw_y),
    )
    scene._aim_assist_target = target
    return target


def aim_assist_candidates(scene) -> list:
    """Active enemies plus the active boss, in stable order."""
    targets = [enemy for enemy in scene._enemies if enemy.active]
    if scene._boss is not None and scene._boss.active:
        targets.append(scene._boss)
    return targets


def is_aim_assist_locked(scene, target, raw_x: float, raw_y: float) -> bool:
    """Whether the smoothed cursor is still considered locked on ``target``."""
    if not target.active:
        return False
    if target.rect.collidepoint(raw_x, raw_y):
        return True
    return distance_sq_to_target(target, raw_x, raw_y) <= (
        scene.AIM_ASSIST_RELEASE_DISTANCE * scene.AIM_ASSIST_RELEASE_DISTANCE
    )


def raw_aim_movement(scene) -> tuple[float, float]:
    """Mouse delta between this frame and the previous one."""
    return (
        scene._raw_aim_position[0] - scene._previous_raw_aim_position[0],
        scene._raw_aim_position[1] - scene._previous_raw_aim_position[1],
    )


def target_in_movement_direction(scene, candidates, movement):
    """Best target in the direction the mouse just moved (cone-gated)."""
    origin = scene._aim_assist_target.rect.center if scene._aim_assist_target in candidates else scene._raw_aim_position
    movement_len = math.hypot(movement[0], movement[1])
    if movement_len <= 0:
        return None

    move_x = movement[0] / movement_len
    move_y = movement[1] / movement_len
    best_target = None
    best_score = 0.0
    for target in candidates:
        if target is scene._aim_assist_target:
            continue
        tx = target.rect.centerx - origin[0]
        ty = target.rect.centery - origin[1]
        distance = math.hypot(tx, ty)
        if distance <= 0:
            continue
        dot = (tx / distance) * move_x + (ty / distance) * move_y
        if dot > best_score and dot >= scene.AIM_ASSIST_DIRECTION_CONE_DOT:
            best_score = dot
            best_target = target
    return best_target


def distance_sq_to_target(target, raw_x: float, raw_y: float) -> float:
    """Squared distance from a cursor point to a target's center."""
    dx = raw_x - target.rect.centerx
    dy = raw_y - target.rect.centery
    return dx * dx + dy * dy


__all__ = [
    "aim_assist_candidates",
    "distance_sq_to_target",
    "is_aim_assist_locked",
    "raw_aim_movement",
    "resolve_aim_assist_target",
    "target_in_movement_direction",
    "update_aim_assist",
    "update_smoothed_raw_aim_position",
]
