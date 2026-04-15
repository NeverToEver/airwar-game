# Systems modules
from airwar.game.systems.health_system import HealthSystem
from airwar.game.systems.reward_system import RewardSystem
from airwar.game.systems.hud_renderer import HUDRenderer
from airwar.game.systems.notification_manager import NotificationManager

# Controller modules
from airwar.game.controllers.game_controller import GameController, GameState
from airwar.game.controllers.spawn_controller import SpawnController
from airwar.game.controllers.collision_controller import CollisionController

# Rendering modules
from airwar.game.rendering.game_renderer import GameRenderer, GameEntities

# Spawners
from airwar.game.spawners.enemy_bullet_spawner import EnemyBulletSpawner

__all__ = [
    'HealthSystem', 'RewardSystem', 'HUDRenderer', 'NotificationManager',
    'GameController', 'GameState', 'SpawnController', 'CollisionController',
    'GameRenderer', 'GameEntities',
    'EnemyBulletSpawner'
]

# Lazy import to avoid circular import
import sys
_game_module = None

def __getattr__(name):
    global _game_module
    if name == 'Game' and _game_module is None:
        from airwar.game.game import Game
        return Game
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
