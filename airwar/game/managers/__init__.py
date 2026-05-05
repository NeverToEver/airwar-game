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

from .bullet_manager import BulletManager
from .boss_manager import BossManager
from .milestone_manager import MilestoneManager
from .input_coordinator import InputCoordinator
from .ui_manager import UIManager
from .game_loop_manager import GameLoopManager

from .game_controller import GameController, GameState
from .spawn_controller import SpawnController
from .collision_controller import CollisionController, CollisionResult

__all__ = [
    'BulletManager', 'BossManager', 'MilestoneManager',
    'InputCoordinator', 'UIManager', 'GameLoopManager',
    'GameController', 'GameState',
    'SpawnController',
    'CollisionController', 'CollisionResult',
]
