"""Entity interfaces — IBulletSpawner and IEntityObserver protocols."""
from abc import ABC, abstractmethod
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from airwar.entities.bullet import Bullet


class IBulletSpawner(ABC):
    """Interface for bullet spawning — implemented by enemy and boss spawners."""
    @abstractmethod
    def spawn_bullet(self, bullet: 'Bullet') -> None:
        pass


class IEntityObserver(ABC):
    """Interface for entity event observation — enemy/boss fire and destroy events."""
    @abstractmethod
    def on_enemy_fired(self, enemy_id: int, bullets: List['Bullet']) -> None:
        pass

    @abstractmethod
    def on_boss_fired(self, boss_id: int, bullets: List['Bullet']) -> None:
        pass

    @abstractmethod
    def on_entity_destroyed(self, entity_id: int, score: int) -> None:
        pass
