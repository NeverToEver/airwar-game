"""Explosion pool — object pool for reusing explosion effects."""

from .explosion_effect import ExplosionEffect


class ExplosionPool:
    """Explosion effect object pool — reuses ExplosionEffect instances"""

    DEFAULT_MAX_SIZE = 20

    def __init__(self, max_size: int = DEFAULT_MAX_SIZE) -> None:
        self._max_size = max_size
        self._available: list[ExplosionEffect] = []
        self._in_use: set[ExplosionEffect] = set()

        self._prewarm(min(5, max_size))

    def _prewarm(self, count: int) -> None:
        """Prewarm pool — pre-create instances"""
        for _ in range(count):
            self._available.append(ExplosionEffect())

    def acquire(self) -> ExplosionEffect | None:
        """Acquire explosion effect instance

        Returns:
            ExplosionEffect instance, or None if pool is exhausted

        Note:
            Returns None if pool is full and all instances are in use
        """
        if self._available:
            effect = self._available.pop()
            self._in_use.add(effect)
            return effect
        elif len(self._in_use) < self._max_size:
            effect = ExplosionEffect()
            self._in_use.add(effect)
            return effect
        else:
            return None

    def release(self, effect: ExplosionEffect) -> None:
        """Release explosion effect instance back to pool

        Args:
            effect: Instance to release
        """
        if effect in self._in_use:
            self._in_use.discard(effect)
            effect.reset()
            self._available.append(effect)

    def update(self) -> int:
        """Update all active effects in the pool

        Returns:
            Number of currently active explosion effects
        """
        if not self._in_use:
            return 0

        for effect in list(self._in_use):
            if not effect.is_active() or not effect.update():
                self.release(effect)

        return len(self._in_use)

    def get_stats(self) -> dict[str, int]:
        """Get pool statistics"""
        return {
            "available": len(self._available),
            "in_use": len(self._in_use),
            "total": len(self._available) + len(self._in_use),
            "max_size": self._max_size,
        }

    def get_active_effects(self) -> list[ExplosionEffect]:
        """Get all currently active effects"""
        return [e for e in self._in_use if e.is_active()]
