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

from airwar.game.managers.bullet_manager import BulletManager
from airwar.game.managers.boss_manager import BossManager
from airwar.game.managers.milestone_manager import MilestoneManager
from airwar.game.managers.input_coordinator import InputCoordinator
from airwar.game.managers.ui_manager import UIManager
from airwar.game.managers.game_loop_manager import GameLoopManager

from airwar.game.managers.game_controller import GameController, GameState
from airwar.game.managers.spawn_controller import SpawnController
from airwar.game.managers.collision_controller import CollisionController, CollisionResult

__all__ = [
    'BulletManager', 'BossManager', 'MilestoneManager',
    'InputCoordinator', 'UIManager', 'GameLoopManager',
    'GameController', 'GameState',
    'SpawnController',
    'CollisionController', 'CollisionResult',
]
