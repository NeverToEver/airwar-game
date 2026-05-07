"""Aim assist targeting and delayed raw input smoothing."""

import math

import pygame

from airwar.config import get_screen_height, get_screen_width


class AimAssistSystem:
    AIM_ASSIST_BREAK_DISTANCE = 38.0
    AIM_ASSIST_SWITCH_DISTANCE = 90.0
    AIM_ASSIST_RELEASE_DISTANCE = 230.0
    AIM_ASSIST_DIRECTION_CONE_DOT = 0.42
    AIM_INPUT_DELAY_BLEND = 0.28
    AIM_INPUT_SNAP_DISTANCE = 10.0

    def __init__(self) -> None:
        self._aim_position = (0.0, 0.0)
        self._raw_aim_position = (0.0, 0.0)
        self._previous_raw_aim_position = (0.0, 0.0)
        self._smoothed_raw_aim_position = (0.0, 0.0)
        self._aim_input_initialized = False
        self._aim_assist_target = None
        self._spawn_controller = None

    def set_raw_aim_position(self, position: tuple[int, int]) -> None:
        x = max(0, min(float(position[0]), float(get_screen_width())))
        y = max(0, min(float(position[1]), float(get_screen_height())))
        if not self._aim_input_initialized:
            self._aim_input_initialized = True
            self._previous_raw_aim_position = (x, y)
            self._raw_aim_position = (x, y)
            self._smoothed_raw_aim_position = (x, y)
            self._aim_position = (x, y)
            return
        self._previous_raw_aim_position = self._raw_aim_position
        self._raw_aim_position = (x, y)
        self._aim_position = self._smoothed_raw_aim_position

    def update(self, spawn_controller, mouse_pos) -> tuple[float, float]:
        self.set_raw_aim_position(mouse_pos)
        return self.update_aim_assist(spawn_controller)

    def update_aim_assist(self, spawn_controller=None) -> tuple[float, float]:
        if spawn_controller is not None:
            self._spawn_controller = spawn_controller
        self._update_smoothed_raw_aim_position()
        target = self._resolve_aim_assist_target()
        if target is None:
            self._aim_position = self._smoothed_raw_aim_position
            return self._aim_position

        target_rect = self._target_rect(target)
        self._aim_position = target_rect.center
        return self._aim_position

    def get_aim_position(self) -> tuple[float, float]:
        return self._aim_position

    def _resolve_aim_assist_target(self):
        raw_x, raw_y = self._smoothed_raw_aim_position
        candidates = self._aim_assist_candidates()
        if not candidates:
            self._aim_assist_target = None
            return None

        movement = self._raw_aim_movement()
        movement_len_sq = movement[0] * movement[0] + movement[1] * movement[1]

        if movement_len_sq >= self.AIM_ASSIST_SWITCH_DISTANCE * self.AIM_ASSIST_SWITCH_DISTANCE:
            directional_target = self._target_in_movement_direction(candidates, movement)
            if directional_target is not None:
                self._aim_assist_target = directional_target
                return directional_target
            if movement_len_sq >= self.AIM_ASSIST_RELEASE_DISTANCE * self.AIM_ASSIST_RELEASE_DISTANCE:
                self._aim_assist_target = None
                return None
            if self._aim_assist_target and getattr(self._aim_assist_target, 'active', False):
                return self._aim_assist_target

        if self._aim_assist_target and self._is_aim_assist_locked(self._aim_assist_target, raw_x, raw_y):
            return self._aim_assist_target

        for target in candidates:
            if self._is_raw_aim_inside_target(target, raw_x, raw_y):
                self._aim_assist_target = target
                return target

        target = self._nearest_aim_assist_target(candidates, raw_x, raw_y)
        self._aim_assist_target = target
        return target

    def _update_smoothed_raw_aim_position(self) -> None:
        sx, sy = self._smoothed_raw_aim_position
        rx, ry = self._raw_aim_position
        dx = rx - sx
        dy = ry - sy
        if dx * dx + dy * dy <= self.AIM_INPUT_SNAP_DISTANCE * self.AIM_INPUT_SNAP_DISTANCE:
            self._smoothed_raw_aim_position = self._raw_aim_position
            return
        self._smoothed_raw_aim_position = (
            sx + dx * self.AIM_INPUT_DELAY_BLEND,
            sy + dy * self.AIM_INPUT_DELAY_BLEND,
        )

    def _aim_assist_candidates(self) -> list:
        if not self._spawn_controller:
            return []
        targets = [enemy for enemy in self._spawn_controller.enemies if getattr(enemy, 'active', False)]
        boss = self._spawn_controller.boss
        if boss and getattr(boss, 'active', False):
            targets.append(boss)
        return targets

    def _is_raw_aim_inside_target(self, target, raw_x: float, raw_y: float) -> bool:
        return self._target_rect(target).collidepoint(raw_x, raw_y)

    def _is_aim_assist_locked(self, target, raw_x: float, raw_y: float) -> bool:
        if not getattr(target, 'active', False):
            return False
        rect = self._target_rect(target)
        if rect.collidepoint(raw_x, raw_y):
            return True
        dx = raw_x - rect.centerx
        dy = raw_y - rect.centery
        return (dx * dx + dy * dy) <= self.AIM_ASSIST_RELEASE_DISTANCE * self.AIM_ASSIST_RELEASE_DISTANCE

    def _raw_aim_movement(self) -> tuple[float, float]:
        return (
            self._raw_aim_position[0] - self._previous_raw_aim_position[0],
            self._raw_aim_position[1] - self._previous_raw_aim_position[1],
        )

    def _nearest_aim_assist_target(self, candidates: list, raw_x: float, raw_y: float):
        return min(
            candidates,
            key=lambda target: self._distance_sq_to_target(target, raw_x, raw_y),
            default=None,
        )

    def _target_in_movement_direction(self, candidates: list, movement: tuple[float, float]):
        if self._aim_assist_target:
            origin = self._target_rect(self._aim_assist_target).center
        else:
            origin = self._raw_aim_position

        mx, my = movement
        movement_len = math.hypot(mx, my)
        if movement_len <= 0:
            return None
        move_x = mx / movement_len
        move_y = my / movement_len

        best_target = None
        best_score = 0.0
        for target in candidates:
            if target is self._aim_assist_target:
                continue
            rect = self._target_rect(target)
            tx = rect.centerx - origin[0]
            ty = rect.centery - origin[1]
            distance = math.hypot(tx, ty)
            if distance <= 0:
                continue
            dot = (tx / distance) * move_x + (ty / distance) * move_y
            if dot > best_score and dot >= self.AIM_ASSIST_DIRECTION_CONE_DOT:
                best_score = dot
                best_target = target
        return best_target

    def _distance_sq_to_target(self, target, raw_x: float, raw_y: float) -> float:
        rect = self._target_rect(target)
        dx = raw_x - rect.centerx
        dy = raw_y - rect.centery
        return dx * dx + dy * dy

    def _target_rect(self, target) -> pygame.Rect:
        rect = target.get_hitbox() if hasattr(target, 'get_hitbox') else target.rect
        if isinstance(rect, pygame.Rect):
            return rect
        if hasattr(target, 'get_hitbox'):
            rect = target.get_hitbox()
        return pygame.Rect(rect.x, rect.y, rect.width, rect.height)
