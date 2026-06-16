"""Game engine package — scene management, game loop, and rendering."""

from importlib import import_module

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

_LAZY_EXPORTS = {
    "CollisionController": ".managers.collision_controller",
    "EnemyBulletSpawner": ".spawners.enemy_bullet_spawner",
    "Game": ".game",
    "GameController": ".managers.game_controller",
    "GameEntities": ".rendering.game_renderer",
    "GameRenderer": ".rendering.game_renderer",
    "GameState": ".managers.game_controller",
    "HUDRenderer": ".rendering",
    "HealthSystem": ".systems.health_system",
    "NotificationManager": ".systems.notification_manager",
    "RewardSystem": ".systems.reward_system",
    "SpawnController": ".managers.spawn_controller",
}


def __getattr__(name):
    if name in _LAZY_EXPORTS:
        module = import_module(_LAZY_EXPORTS[name], __name__)
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
