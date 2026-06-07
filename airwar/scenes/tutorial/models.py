"""Tutorial-scene data models used outside the scene module.

Lifts the base-console data classes out of
:mod:`airwar.scenes.tutorial_scene` so :mod:`.base_console` (and
future helpers) can import them without creating a circular import.
The legacy names are re-exported from :mod:`tutorial_scene` for
back-compat.

Note: the in-scene entity dataclasses (``TutorialEnemy``,
``TutorialBullet``, ``TutorialBoss``, ``TutorialExplosion``) stay
where they are -- they're tightly coupled to the scene's update loop
and aren't shared with any external module.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TutorialBasePlayerStatus:
    """Minimal player-shaped status object for the real base console."""

    health: int = 78
    max_health: int = 120
    boost_current: float = 64.0
    boost_max: float = 100.0
    bullet_damage: int = 62
    fire_interval: int = 7
    boost_recovery_rate: float = 1.0
    phase_dash_enabled: bool = True
    mothership_cooldown_mult: float = 0.5

    def get_boost_status(self) -> dict:
        return {
            "current": self.boost_current,
            "max": self.boost_max,
            "active": False,
            "dash_enabled": self.is_phase_dash_enabled,
            "dash_cooldown": 0,
        }

    def set_weapon_modifiers(self, spread: bool, laser: bool, explosive: bool) -> None:
        self.weapon_spread = spread
        self.weapon_laser = laser
        self.weapon_explosive = explosive

    def activate_shotgun(self) -> None:
        self.weapon_spread = True

    def activate_laser(self, _duration: int) -> None:
        self.weapon_laser = True

    def activate_explosive(self) -> None:
        self.weapon_explosive = True

    def activate_phase_dash(self) -> None:
        self.is_phase_dash_enabled = True


@dataclass
class TutorialBaseGameState:
    score: int = 860
    kill_count: int = 5
    boss_kill_count: int = 1
    difficulty: str = "medium"
    requisition_points: int = 80


class TutorialBaseGameController:
    """Small controller facade with the methods read by BaseTalentConsole."""

    def __init__(self) -> None:
        self.state = TutorialBaseGameState()

    def get_next_progress(self) -> int:
        return 72

    def get_next_threshold(self) -> int:
        return 1200


__all__ = [
    "TutorialBaseGameController",
    "TutorialBaseGameState",
    "TutorialBasePlayerStatus",
]
