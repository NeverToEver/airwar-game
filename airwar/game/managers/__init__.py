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

from .boss_manager import BossManager
from .bullet_manager import BulletManager
from .collision_controller import CollisionController, CollisionResult
from .game_controller import GameController, GameState
from .game_loop_manager import GameLoopManager
from .input_coordinator import InputCoordinator
from .milestone_manager import MilestoneManager
from .spawn_controller import SpawnController
from .ui_manager import UIManager

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
