"""Entity interfaces — IBulletSpawner protocol."""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from airwar.entities.bullet import Bullet


class IBulletSpawner(ABC):
    """Interface for bullet spawning — implemented by enemy and boss spawners."""
    @abstractmethod
    def spawn_bullet(self, bullet: 'Bullet') -> None:
        pass
