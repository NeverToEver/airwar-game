import math
from typing import Tuple


class ExplosionParticle:
    """Explosion particle — represents a glowing point in an explosion"""

    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        life: int,
        max_life: int,
        size: float
    ) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = max_life
        self.size = size

    def update(self, dt: float = 1.0) -> None:
        """Update particle state

        Args:
            dt: Time multiplier (frame multiplier), default 1.0
        """
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.98
        self.vy *= 0.98
        self.life -= 1

    def get_alpha(self) -> int:
        """Get alpha value (0-255)"""
        return int(255 * (self.life / self.max_life))

    def get_color(self) -> Tuple[int, int, int]:
        """Get color (changes with lifecycle)

        Transitions from orange-red to yellow"""
        life_ratio = self.life / self.max_life
        r = 255
        g = int(150 * life_ratio)
        b = int(30 * life_ratio)
        return (r, g, b)

    def is_alive(self) -> bool:
        """Check if particle is alive"""
        return self.life > 0
