"""Game engine package — scene management, game loop, and rendering."""

# Systems modules
from .systems.health_system import HealthSystem
from .systems.reward_system import RewardSystem
from .systems.notification_manager import NotificationManager

# Rendering modules (includes HUD)
from .rendering import HUDRenderer

# Controller modules (migrated to managers)
from .managers.game_controller import GameController, GameState
from .managers.spawn_controller import SpawnController
from .managers.collision_controller import CollisionController

# Rendering modules
from .rendering.game_renderer import GameRenderer, GameEntities

# Spawners
from .spawners.enemy_bullet_spawner import EnemyBulletSpawner

__all__ = [
    'HealthSystem', 'RewardSystem', 'HUDRenderer', 'NotificationManager',
    'GameController', 'GameState', 'SpawnController', 'CollisionController',
    'GameRenderer', 'GameEntities',
    'EnemyBulletSpawner'
]

# Lazy import to avoid circular import
_game_module = None

def __getattr__(name):
    global _game_module
    if name == 'Game' and _game_module is None:
        from .game import Game
        return Game
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
