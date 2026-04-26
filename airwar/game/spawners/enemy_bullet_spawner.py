"""Enemy bullet spawner — creates and manages enemy bullet entities."""
from typing import List
from airwar.entities.interfaces import IBulletSpawner
from airwar.entities.bullet import Bullet


class EnemyBulletSpawner(IBulletSpawner):
    """Enemy bullet spawner — creates and manages enemy bullet entities.
    
        Implements IBulletSpawner to spawn enemy bullets from various
        attack patterns (single, spread, laser, wave).
        """
    def __init__(self, bullet_list: List[Bullet] = None):
        self.bullet_list = bullet_list if bullet_list is not None else []

    def spawn_bullet(self, bullet: Bullet) -> None:
        self.bullet_list.append(bullet)

    def get_bullets(self) -> List[Bullet]:
        return self.bullet_list

    def clear_inactive(self) -> None:
        # Use in-place filter to preserve list reference
        self.bullet_list[:] = [b for b in self.bullet_list if b.active]
