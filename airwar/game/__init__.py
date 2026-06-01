"""Game engine package — scene management, game loop, and rendering."""

# Systems modules
from .managers.collision_controller import CollisionController

# Controller modules (migrated to managers)
from .managers.game_controller import GameController, GameState
from .managers.spawn_controller import SpawnController

# Rendering modules (includes HUD)
from .rendering import HUDRenderer

# Rendering modules
from .rendering.game_renderer import GameEntities, GameRenderer

# Spawners
from .spawners.enemy_bullet_spawner import EnemyBulletSpawner
from .systems.health_system import HealthSystem
from .systems.notification_manager import NotificationManager
from .systems.reward_system import RewardSystem

__all__ = [
    "CollisionController",
    "EnemyBulletSpawner",
    "GameController",
    "GameEntities",
    "GameRenderer",
    "GameState",
    "HUDRenderer",
    "HealthSystem",
    "NotificationManager",
    "RewardSystem",
    "SpawnController",
]

# Lazy import to avoid circular import
_game_module = None


def __getattr__(name):
    if name == "Game":
        from .game import Game

        return Game
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
