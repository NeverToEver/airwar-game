"""Game Manager Module.

Centralizes specialized manager components for game-related functionality,
following the Single Responsibility Principle. Each manager coordinates
business logic for a specific domain.

Manager Classes:
    BulletManager: Manages player and enemy bullet updates, collisions, and cleanup.
    BossManager: Manages boss lifecycle, behavior, and combat logic.
    MilestoneManager: Handles milestone triggering and reward selection flow.
    InputCoordinator: Manages input event handling and surrender system.
    UIManager: Manages game UI rendering.
    GameLoopManager: Manages the main game loop logic.

Usage:
    from airwar.game.managers import BulletManager

    bullet_manager = BulletManager(player, spawn_controller)
    bullet_manager.update_all()
"""

from importlib import import_module

__all__ = [
    "BossManager",
    "BulletManager",
    "CollisionController",
    "CollisionResult",
    "GameController",
    "GameLoopManager",
    "GameState",
    "InputCoordinator",
    "MilestoneManager",
    "SpawnController",
    "UIManager",
]

_LAZY_EXPORTS = {
    "BossManager": ".boss_manager",
    "BulletManager": ".bullet_manager",
    "CollisionController": ".collision_controller",
    "CollisionResult": ".collision_controller",
    "GameController": ".game_controller",
    "GameLoopManager": ".game_loop_manager",
    "GameState": ".game_controller",
    "InputCoordinator": ".input_coordinator",
    "MilestoneManager": ".milestone_manager",
    "SpawnController": ".spawn_controller",
    "UIManager": ".ui_manager",
}


def __getattr__(name: str):
    if name in _LAZY_EXPORTS:
        module = import_module(_LAZY_EXPORTS[name], __name__)
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
