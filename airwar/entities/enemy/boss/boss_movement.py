"""Boss movement component.

Encapsulates the four-phase patrol movement (``PATROL -> SWEEP -> HOVER
-> CHASE``), aim-dash, enrage orbit, enrage release hold, and enrage
return. The :class:`Boss` class delegates to :class:`BossMovement` and
exposes no movement logic of its own.

Interface:
    movement.tick_entry(boss, slow_factor) -> bool
        Move the boss downward during entrance animation. Returns True
        when the entrance completes.
    movement.tick_active(boss, player_pos, slow_factor) -> None
        Run the four-phase patrol + clamp to arena.
    movement.tick_aim_dash(boss) -> None
        Advance the aim-dash by one frame. Idempotent if no dash is in
        progress.
    movement.tick_enrage_transition(boss) -> None
    movement.tick_enrage_active(boss) -> None
    movement.tick_enrage_release_hold(boss) -> None
    movement.tick_enrage_return(boss) -> None
    movement.select_next_target(boss, player_pos) -> None
    movement.start_aim_dash(boss, player_pos) -> bool
    movement.start_enrage_return(boss) -> None
    movement.clamped_arena_position(boss, x, y) -> tuple[float, float]
"""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

from airwar.config import get_screen_height, get_screen_width

if TYPE_CHECKING:
    from .boss import Boss


# P1-4: Module-level constants kept as literals (backward compat with
# the ``Boss`` class attributes and other importers). The canonical
# source of truth is ``GAME_CONSTANTS.BOSS_TUNING`` in
# :mod:`airwar.game.constants`; the values below mirror it. Keep in
# sync if you tune the boss movement.
DEFAULT_PHASE_DURATION: int = 120
ENTRY_SPEED: float = 2
ESCAPE_DRIFT: float = 0.5
LERP_FACTOR: float = 0.025
MIN_Y: int = 50
CENTER_OFFSET: int = 60
AIM_DASH_DISTANCE: int = 220
AIM_DASH_PHASE_BONUS: int = 35
AIM_DASH_MAX_DISTANCE_RATIO: float = 0.58
AIM_DASH_DURATION: int = 10


class BossMovement:
    """Movement controller for the boss.

    Holds the per-phase movement state (``_move_phase``, target X/Y,
    aim-dash progress) and exposes a small set of ``tick_*`` methods
    that the ``Boss`` class invokes in the appropriate order.
    """

    def __init__(self, boss: Boss) -> None:
        self._boss = boss

    # ------------------------------------------------------------------
    # Constants accessors (return the class-level value when needed)
    # ------------------------------------------------------------------

    @staticmethod
    def default_phase_duration() -> int:
        return DEFAULT_PHASE_DURATION

    # ------------------------------------------------------------------
    # Entry
    # ------------------------------------------------------------------

    def tick_entry(self, slow_factor: float) -> bool:
        """Advance the entrance animation. Returns True if just completed."""
        boss = self._boss
        boss.rect.y += ENTRY_SPEED * slow_factor
        if boss.rect.y >= boss.target_y:
            boss.rect.y = boss.target_y
            return True
        return False

    # ------------------------------------------------------------------
    # Four-phase patrol
    # ------------------------------------------------------------------

    def select_next_target(self, player_pos: tuple[int, int] | None) -> None:
        """Pick the next movement target based on the cycling phase."""
        boss = self._boss
        screen_w = get_screen_width()
        screen_h = get_screen_height()
        margin = 50
        x_min = margin + 60
        x_max = screen_w - boss.rect.width - margin - 60
        y_min = 60
        y_max = screen_h // 2

        phase = boss._move_phase % 4
        boss._move_phase += 1

        if phase == 0:
            # PATROL: opposite horizontal side with vertical drift
            if boss.rect.centerx < screen_w // 2:
                boss._target_x = x_max
            else:
                boss._target_x = x_min
            boss._target_y = random.randint(y_min, y_max)
        elif phase == 1:
            # SWEEP: diagonal to a random zone
            boss._target_x = random.randint(x_min, x_max)
            boss._target_y = random.randint(y_min, y_max)
        elif phase == 2:
            # HOVER: local repositioning with gentle drift
            boss._target_x = random.randint(
                int(max(margin, boss.rect.x - 130)),
                int(min(screen_w - boss.rect.width - margin, boss.rect.x + 130)),
            )
            boss._target_y = random.randint(
                int(max(y_min, boss.rect.y - 80)),
                int(min(y_max, boss.rect.y + 80)),
            )
        else:
            # CHASE: drift toward player area with random offset
            if player_pos:
                boss._target_x = max(x_min, min(player_pos[0] + random.randint(-60, 60), x_max))
                boss._target_y = max(y_min, min(player_pos[1] - random.randint(80, 160), y_max))
            else:
                boss._target_x = random.randint(x_min, x_max)
                boss._target_y = random.randint(y_min, y_max)

    def tick_active(
        self,
        player_pos: tuple[int, int] | None,
        slow_factor: float,
    ) -> None:
        """Drive the four-phase patrol + arena clamp + subtle bob."""
        boss = self._boss
        boss._move_phase_timer += 1
        if boss._move_phase_timer >= boss._move_phase_duration:
            boss._move_phase_timer = 0
            boss._move_phase_duration = random.randint(90, 200)
            self.select_next_target(player_pos)

        lerp_speed = LERP_FACTOR * boss.data.speed * slow_factor
        boss.rect.x = boss.rect.x + (boss._target_x - boss.rect.x) * lerp_speed
        boss.rect.y = boss.rect.y + (boss._target_y - boss.rect.y) * lerp_speed

        boss.rect.x, boss.rect.y = self.clamped_arena_position(boss.rect.x, boss.rect.y)

        # Subtle vertical bob synced to the survival timer.
        boss.rect.y += math.sin(boss.survival_timer * 0.025) * 0.4

        # Escape warning drift when approaching escape time.
        from airwar.config.constants_access import get_game_constants

        if boss.survival_timer >= boss.data.escape_time - get_game_constants().ENEMY.ESCAPE_WARNING:
            boss._show_escape_warning = True
            boss.rect.y -= ESCAPE_DRIFT

    def clamped_arena_position(self, x: float, y: float) -> tuple[float, float]:
        boss = self._boss
        screen_w = get_screen_width()
        screen_h = get_screen_height()
        return (
            max(0, min(x, screen_w - boss.rect.width)),
            max(MIN_Y, min(y, screen_h // 2 + CENTER_OFFSET)),
        )

    # ------------------------------------------------------------------
    # Aim dash
    # ------------------------------------------------------------------

    def is_aim_dashing(self) -> bool:
        return self._boss._aim_dash_duration > 0

    def start_aim_dash(self, player_pos: tuple[float, float]) -> bool:
        """Begin an aim-dash toward the given player position.

        Returns False when the dash cannot be initiated (e.g. distance
        too small after clamping).
        """
        boss = self._boss
        if not player_pos:
            return False

        boss._aim_fire_target = (float(player_pos[0]), float(player_pos[1]))
        dx = player_pos[0] - boss.rect.centerx
        dy = player_pos[1] - boss.rect.centery
        distance = math.hypot(dx, dy)
        if distance <= 0:
            return False

        dash_distance = AIM_DASH_DISTANCE + boss.phase * AIM_DASH_PHASE_BONUS
        dash_distance = min(dash_distance, distance * AIM_DASH_MAX_DISTANCE_RATIO)
        target_center_x = boss.rect.centerx + dx / distance * dash_distance
        target_center_y = boss.rect.centery + dy / distance * dash_distance
        target_x = target_center_x - boss.rect.width / 2
        target_y = target_center_y - boss.rect.height / 2
        target_x, target_y = self.clamped_arena_position(target_x, target_y)

        if abs(target_x - boss.rect.x) < 1 and abs(target_y - boss.rect.y) < 1:
            return False

        boss._aim_dash_elapsed = 0
        boss._aim_dash_duration = AIM_DASH_DURATION
        boss._aim_dash_start_x = boss.rect.x
        boss._aim_dash_start_y = boss.rect.y
        boss._aim_dash_target_x = target_x
        boss._aim_dash_target_y = target_y
        boss._target_x = target_x
        boss._target_y = target_y
        return True

    def tick_aim_dash(self) -> bool:
        """Advance the aim-dash by one frame. Returns True when finished."""
        boss = self._boss
        if not self.is_aim_dashing():
            return False
        boss._aim_dash_elapsed += 1
        progress = min(1.0, boss._aim_dash_elapsed / boss._aim_dash_duration)
        boss.rect.x = boss._aim_dash_start_x + (boss._aim_dash_target_x - boss._aim_dash_start_x) * progress
        boss.rect.y = boss._aim_dash_start_y + (boss._aim_dash_target_y - boss._aim_dash_start_y) * progress
        boss.rect.x, boss.rect.y = self.clamped_arena_position(boss.rect.x, boss.rect.y)
        return progress >= 1.0

    def finish_aim_dash(self) -> None:
        boss = self._boss
        boss._aim_dash_duration = 0
        boss._aim_dash_elapsed = 0

    # ------------------------------------------------------------------
    # Enrage path
    # ------------------------------------------------------------------

    def enrage_path_radius(self, target: tuple[float, float]) -> float:
        boss = self._boss
        from . import ENRAGE_PATH_RADIUS_SCALE

        base_radius = max(boss.rect.width, boss.rect.height) * ENRAGE_PATH_RADIUS_SCALE
        max_radius = max(
            24.0,
            min(
                target[0] - boss.rect.width / 2,
                get_screen_width() - target[0] - boss.rect.width / 2,
                target[1] - MIN_Y - boss.rect.height / 2,
                get_screen_height() - target[1] - boss.rect.height / 2,
            ),
        )
        return min(base_radius, max_radius)

    def enrage_path_center(self, target: tuple[float, float], progress: float) -> tuple[float, float]:
        from . import ENRAGE_SQUARE_PATH_RATIO

        progress = max(0.0, min(1.0, progress))
        radius = self.enrage_path_radius(target)
        if progress <= ENRAGE_SQUARE_PATH_RATIO:
            square_progress = progress / max(0.0001, ENRAGE_SQUARE_PATH_RATIO)
            return self._enrage_square_path_center(target, radius, square_progress)
        circle_progress = (progress - ENRAGE_SQUARE_PATH_RATIO) / max(0.0001, 1.0 - ENRAGE_SQUARE_PATH_RATIO)
        angle = math.pi / 2 + circle_progress * math.tau
        return (
            target[0] + math.cos(angle) * radius,
            target[1] + math.sin(angle) * radius,
        )

    def _enrage_square_path_center(
        self,
        target: tuple[float, float],
        radius: float,
        progress: float,
    ) -> tuple[float, float]:
        progress = max(0.0, min(1.0, progress))
        segment = min(3, int(progress * 4))
        local = progress * 4 - segment
        # Square path starts/ends at bottom (same as circle-path start) so
        # the square→circle transition at ENRAGE_SQUARE_PATH_RATIO is seamless.
        points = (
            (target[0], target[1] + radius),
            (target[0] - radius, target[1]),
            (target[0], target[1] - radius),
            (target[0] + radius, target[1]),
            (target[0], target[1] + radius),
        )
        start = points[segment]
        end = points[segment + 1]
        return (
            start[0] + (end[0] - start[0]) * local,
            start[1] + (end[1] - start[1]) * local,
        )

    def clamped_enrage_position(self, x: float, y: float) -> tuple[float, float]:
        boss = self._boss
        return (
            max(0, min(x, get_screen_width() - boss.rect.width)),
            max(MIN_Y, min(y, get_screen_height() - boss.rect.height)),
        )

    def tick_enrage_transition(self) -> None:
        """Drive the squarish-then-orbit transition animation."""
        from . import ENRAGE_TRANSITION_DURATION

        boss = self._boss
        target = boss._state.enrage_snapshot_target
        if target is None:
            return
        elapsed = ENRAGE_TRANSITION_DURATION - boss._state.enrage_transition_timer
        transition = max(0.0, min(1.0, elapsed / max(1, ENRAGE_TRANSITION_DURATION)))
        eased = 1.0 - (1.0 - transition) ** 3
        start = boss._state.enrage_transition_origin or (
            boss.rect.centerx,
            boss.rect.centery,
        )
        orbit_progress = boss._state.enrage_progress()
        target_center_x, target_center_y = self.enrage_path_center(target, orbit_progress)
        charge_shake_x = math.sin(transition * math.tau * 7.0) * (1.0 - transition) * 13.0
        charge_shake_y = math.cos(transition * math.tau * 5.0) * (1.0 - transition) * 8.0
        center_x = start[0] + (target_center_x - start[0]) * eased + charge_shake_x
        center_y = start[1] + (target_center_y - start[1]) * eased + charge_shake_y
        boss.rect.x, boss.rect.y = self.clamped_enrage_position(
            center_x - boss.rect.width / 2,
            center_y - boss.rect.height / 2,
        )
        boss.sync_hitbox()

    def tick_enrage_active(self) -> None:
        boss = self._boss
        target = boss._state.enrage_snapshot_target
        if target is None:
            return
        progress = boss._state.enrage_progress()
        target_center_x, target_center_y = self.enrage_path_center(target, progress)
        boss.rect.x, boss.rect.y = self.clamped_enrage_position(
            target_center_x - boss.rect.width / 2,
            target_center_y - boss.rect.height / 2,
        )
        boss.sync_hitbox()

    def tick_enrage_release_hold(self) -> None:
        boss = self._boss
        anchor = boss._state.enrage_release_anchor
        if anchor is None:
            return
        boss.rect.x = anchor[0] - boss.rect.width / 2
        boss.rect.y = anchor[1] - boss.rect.height / 2
        boss._target_x = boss.rect.x
        boss._target_y = boss.rect.y
        boss.sync_hitbox()

    def start_enrage_return(self) -> None:
        boss = self._boss
        origin = (boss.rect.x, boss.rect.y)
        target = self.clamped_arena_position(boss.rect.x, boss.rect.y)
        boss._state.begin_enrage_return(origin, target)

    def tick_enrage_return(self) -> None:
        from . import ENRAGE_RETURN_DURATION

        boss = self._boss
        origin = boss._state.enrage_return_origin or (boss.rect.x, boss.rect.y)
        destination = boss._state.enrage_return_target or self.clamped_arena_position(boss.rect.x, boss.rect.y)
        elapsed = ENRAGE_RETURN_DURATION - boss._state.enrage_return_timer
        progress = max(0.0, min(1.0, elapsed / max(1, ENRAGE_RETURN_DURATION)))
        eased = progress * progress * (3 - 2 * progress)
        boss.rect.x = origin[0] + (destination[0] - origin[0]) * eased
        boss.rect.y = origin[1] + (destination[1] - origin[1]) * eased
        boss._target_x = destination[0]
        boss._target_y = destination[1]
        boss.sync_hitbox()
        if boss._state.enrage_return_timer <= 0:
            boss.rect.x, boss.rect.y = destination


__all__ = [
    "AIM_DASH_DISTANCE",
    "AIM_DASH_DURATION",
    "AIM_DASH_MAX_DISTANCE_RATIO",
    "AIM_DASH_PHASE_BONUS",
    "CENTER_OFFSET",
    "DEFAULT_PHASE_DURATION",
    "ENTRY_SPEED",
    "ESCAPE_DRIFT",
    "LERP_FACTOR",
    "MIN_Y",
    "BossMovement",
]
