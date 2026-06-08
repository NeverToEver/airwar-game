"""Property checks applied to a stream of :class:`GameSnapshot`."""

from __future__ import annotations

import logging
import math
from collections import Counter
from dataclasses import dataclass
from typing import Sequence

from .snapshot import GameSnapshot

logger = logging.getLogger(__name__)


@dataclass
class InvariantViolation:
    """A single invariant that failed on a specific frame.

    Attributes:
        rule: Name of the rule (e.g. ``"no_nan"``).
        frame: Frame index where the violation occurred.
        message: Human-readable description of the failure.
    """

    rule: str
    frame: int
    message: str


class InvariantSuite:
    """A bundle of invariants; each ``check_*`` is a pure function.

    To add a new invariant: write ``check_my_thing`` that takes a
    snapshot and returns ``None`` (ok) or an :class:`InvariantViolation`.
    Then add it to :attr:`checks`.  ``check_all`` runs them all and
    reports counts / violations.
    """

    def __init__(self) -> None:
        self.check_counts: Counter[str] = Counter()
        self.violations: list[InvariantViolation] = []
        self._checks = [
            self.check_no_nan,
            self.check_score_monotonic,
            self.check_enemy_count_bounded,
            self.check_bullet_count_bounded,
            self.check_player_position_bounded,
            self.check_state_consistency,
            self.check_health_bounded,
        ]

    # -- Individual rules ------------------------------------------------

    def check_no_nan(self, snap: GameSnapshot) -> InvariantViolation | None:
        """No NaN / inf in player position, health, or extra values."""
        if snap.has_nan():
            return InvariantViolation(
                rule="no_nan",
                frame=snap.frame,
                message=f"NaN/inf detected in snapshot: {snap.to_dict()}",
            )
        return None

    def check_score_monotonic(self, snap: GameSnapshot) -> InvariantViolation | None:
        """Score must never decrease across consecutive game-scene snapshots.

        The previous snapshot is read from ``self._prev`` (set by
        :meth:`check_all`).  We use a hidden state to keep the
        check's signature uniform with the other rules.

        Two resets are honoured: a frame-counter reset to 0 (start
        of a new scenario) and a non-game scene in between (the
        score of the new game scene starts from zero).
        """
        prev = getattr(self, "_prev", None)
        if prev is None or snap.score is None or prev.score is None:
            return None
        if snap.scene_name != "game" or prev.scene_name != "game":
            return None
        # New scenario (frame counter reset) or score reset to 0 from
        # a non-zero prev -- treat as a clean break, not a regression.
        if snap.frame == 0:
            return None
        if prev.frame > snap.frame:
            return None
        if snap.score < prev.score:
            return InvariantViolation(
                rule="score_monotonic",
                frame=snap.frame,
                message=f"score decreased {prev.score} -> {snap.score}",
            )
        return None

    def check_enemy_count_bounded(self, snap: GameSnapshot) -> InvariantViolation | None:
        """No more than 200 active enemies on screen (sanity ceiling)."""
        if snap.enemy_count is None:
            return None
        if snap.enemy_count > 200:
            return InvariantViolation(
                rule="enemy_count_bounded",
                frame=snap.frame,
                message=f"enemy_count={snap.enemy_count} > 200",
            )
        return None

    def check_bullet_count_bounded(self, snap: GameSnapshot) -> InvariantViolation | None:
        """No more than 1000 active bullets in any single pool."""
        for name, val in (
            ("player_bullet_count", snap.player_bullet_count),
            ("enemy_bullet_count", snap.enemy_bullet_count),
        ):
            if val is None:
                continue
            if val > 1000:
                return InvariantViolation(
                    rule="bullet_count_bounded",
                    frame=snap.frame,
                    message=f"{name}={val} > 1000",
                )
        return None

    def check_player_position_bounded(self, snap: GameSnapshot) -> InvariantViolation | None:
        """Player position must remain on-screen."""
        if snap.player_position is None:
            return None
        x, y = snap.player_position
        if not (math.isfinite(x) and math.isfinite(y)):
            return None  # covered by no_nan
        # Generous bounds: 3x screen size to catch wild teleports.
        if not (-3000 <= x <= 5000 and -3000 <= y <= 3000):
            return InvariantViolation(
                rule="player_position_bounded",
                frame=snap.frame,
                message=f"player_position=({x}, {y}) wildly off-screen",
            )
        return None

    def check_state_consistency(self, snap: GameSnapshot) -> InvariantViolation | None:
        """Player cannot be alive AND dying at the same time."""
        if snap.player_alive and snap.player_dying:
            return InvariantViolation(
                rule="state_consistency",
                frame=snap.frame,
                message="player reported both alive and dying simultaneously",
            )
        return None

    def check_health_bounded(self, snap: GameSnapshot) -> InvariantViolation | None:
        """Player health must be in [0, max_health]."""
        if snap.player_health is None or snap.player_max_health is None:
            return None
        if snap.player_health < 0:
            return InvariantViolation(
                rule="health_bounded",
                frame=snap.frame,
                message=f"player_health={snap.player_health} < 0",
            )
        if snap.player_health > snap.player_max_health * 1.01:
            return InvariantViolation(
                rule="health_bounded",
                frame=snap.frame,
                message=f"player_health={snap.player_health} > max_health={snap.player_max_health}",
            )
        return None

    # -- Driver ----------------------------------------------------------

    def check_all(self, snapshots: Sequence[GameSnapshot]) -> list[InvariantViolation]:
        """Run all checks over ``snapshots``; return the list of violations."""
        self.violations = []
        self.check_counts = Counter()
        prev: GameSnapshot | None = None
        for snap in snapshots:
            # Score monotonicity needs the previous snapshot; the check
            # reads it from ``self._prev`` which we update at the end
            # of each loop iteration.  Using a hidden state avoids
            # binding-method equality issues in ``self._checks``.
            self._prev = prev
            for check in self._checks:
                self.check_counts[check.__name__] += 1
                violation = check(snap)
                if violation is not None:
                    self.violations.append(violation)
            prev = snap
            self._prev = None
        return list(self.violations)
