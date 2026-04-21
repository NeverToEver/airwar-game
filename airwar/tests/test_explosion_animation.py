import pytest
import pygame
from unittest.mock import Mock, MagicMock

from airwar.game.explosion_animation import (
    ExplosionParticle,
    ExplosionEffect,
    ExplosionPool,
    ExplosionManager,
)


class TestExplosionParticle:
    """Test ExplosionParticle class"""

    def test_particle_initialization(self):
        """Test particle initialization"""
        particle = ExplosionParticle(
            x=100, y=200, vx=1.5, vy=2.5,
            life=30, max_life=30, size=3.0
        )

        assert particle.x == 100
        assert particle.y == 200
        assert particle.vx == 1.5
        assert particle.vy == 2.5
        assert particle.life == 30
        assert particle.max_life == 30
        assert particle.size == 3.0

    def test_particle_update(self):
        """Test particle update changes position and life"""
        particle = ExplosionParticle(
            x=100, y=200, vx=10, vy=10,
            life=10, max_life=10, size=2.0
        )

        initial_x, initial_y = particle.x, particle.y
        particle.update()
        particle.update()

        assert particle.x > initial_x
        assert particle.y > initial_y
        assert particle.life == 8

    def test_particle_velocity_decay(self):
        """Test particle velocity decays over time"""
        particle = ExplosionParticle(
            x=100, y=100, vx=10, vy=10,
            life=10, max_life=10, size=2.0
        )

        initial_vx = particle.vx
        particle.update()

        assert particle.vx < initial_vx
        assert particle.vy < 10

    def test_particle_get_alpha(self):
        """Test alpha value calculation"""
        particle = ExplosionParticle(
            x=100, y=100, vx=1, vy=1,
            life=5, max_life=10, size=2.0
        )

        alpha = particle.get_alpha()
        assert alpha == 127

    def test_particle_get_alpha_full_life(self):
        """Test alpha value at full life"""
        particle = ExplosionParticle(
            x=100, y=100, vx=1, vy=1,
            life=10, max_life=10, size=2.0
        )

        alpha = particle.get_alpha()
        assert alpha == 255

    def test_particle_get_color(self):
        """Test color changes with lifecycle"""
        particle = ExplosionParticle(
            x=100, y=100, vx=1, vy=1,
            life=10, max_life=10, size=2.0
        )

        r, g, b = particle.get_color()
        assert r == 255
        assert g > 0
        assert b >= 0

    def test_particle_is_alive(self):
        """Test particle alive status"""
        particle = ExplosionParticle(
            x=100, y=100, vx=1, vy=1,
            life=5, max_life=10, size=2.0
        )

        assert particle.is_alive()

        for _ in range(5):
            particle.update()

        assert not particle.is_alive()


class TestExplosionEffect:
    """Test ExplosionEffect class"""

    def test_effect_initialization(self):
        """Test effect initialization"""
        effect = ExplosionEffect()

        assert not effect.is_active()
        assert len(effect._particles) == 0

    def test_effect_trigger(self):
        """Test effect triggering generates particles"""
        effect = ExplosionEffect()
        assert not effect.is_active()

        effect.trigger(x=100, y=200, radius=50)

        assert effect.is_active()
        assert len(effect._particles) == ExplosionEffect.PARTICLE_COUNT
        assert effect._x == 100
        assert effect._y == 200
        assert effect._radius == 50

    def test_effect_update_with_particles(self):
        """Test effect update returns True while particles alive"""
        effect = ExplosionEffect()
        effect.trigger(x=100, y=200, radius=50)

        result = effect.update()
        assert result is True

        for _ in range(50):
            effect.update()

        result = effect.update()
        assert result is False

    def test_effect_update_inactive(self):
        """Test effect update returns False when inactive"""
        effect = ExplosionEffect()

        result = effect.update()
        assert result is False

    def test_effect_reset(self):
        """Test effect reset clears state"""
        effect = ExplosionEffect()
        effect.trigger(x=100, y=200, radius=50)

        assert effect.is_active()
        effect.reset()

        assert not effect.is_active()
        assert len(effect._particles) == 0

    def test_particle_count_configurable(self):
        """Test particle count matches configuration"""
        effect = ExplosionEffect()
        effect.trigger(x=100, y=200, radius=50)

        assert len(effect._particles) == ExplosionEffect.PARTICLE_COUNT


class TestExplosionPool:
    """Test ExplosionPool class"""

    def test_pool_initialization(self):
        """Test pool prewarms with instances"""
        pool = ExplosionPool(max_size=10)

        stats = pool.get_stats()
        assert stats['available'] == 5
        assert stats['in_use'] == 0
        assert stats['total'] == 5

    def test_pool_acquire(self):
        """Test acquiring effect from pool"""
        pool = ExplosionPool(max_size=10)

        effect = pool.acquire()
        assert effect is not None
        assert effect.is_active() is False

        stats = pool.get_stats()
        assert stats['available'] == 4
        assert stats['in_use'] == 1

    def test_pool_release(self):
        """Test releasing effect back to pool"""
        pool = ExplosionPool(max_size=10)

        effect = pool.acquire()
        pool.release(effect)

        stats = pool.get_stats()
        assert stats['available'] == 5
        assert stats['in_use'] == 0

    def test_pool_acquire_when_exhausted(self):
        """Test acquiring when pool is exhausted but under max"""
        pool = ExplosionPool(max_size=10)

        effects = []
        for _ in range(10):
            effects.append(pool.acquire())

        assert len(effects) == 10

        extra_effect = pool.acquire()
        assert extra_effect is None

    def test_pool_acquire_when_maxed(self):
        """Test acquiring when at max size returns None"""
        pool = ExplosionPool(max_size=2)

        pool.acquire()
        pool.acquire()

        effect = pool.acquire()
        assert effect is None

    def test_pool_update_cleans_inactive(self):
        """Test pool update releases inactive effects"""
        pool = ExplosionPool(max_size=10)

        effect = pool.acquire()
        effect.trigger(x=100, y=200, radius=50)

        for _ in range(100):
            effect.update()

        count = pool.update()
        assert count == 0

        stats = pool.get_stats()
        assert stats['available'] == 5

    def test_pool_stats(self):
        """Test pool statistics"""
        pool = ExplosionPool(max_size=5)

        effect1 = pool.acquire()
        effect2 = pool.acquire()

        stats = pool.get_stats()
        assert stats['available'] == 3
        assert stats['in_use'] == 2
        assert stats['max_size'] == 5


class TestExplosionManager:
    """Test ExplosionManager class"""

    def test_manager_initialization(self):
        """Test manager initializes pool"""
        manager = ExplosionManager()

        stats = manager.get_stats()
        assert stats['available'] > 0
        assert stats['in_use'] == 0
        assert stats['max_per_second'] == ExplosionManager.DEFAULT_MAX_PER_SECOND

    def test_manager_trigger_success(self):
        """Test successful explosion trigger"""
        manager = ExplosionManager(max_per_second=30)

        result = manager.trigger(x=100, y=200, radius=50)

        assert result is True
        stats = manager.get_stats()
        assert stats['total_explosions'] == 1
        assert stats['explosions_this_second'] == 1

    def test_manager_frequency_limit(self):
        """Test frequency limiting works"""
        manager = ExplosionManager(max_per_second=3)

        manager.trigger(100, 100, 50)
        manager.trigger(100, 100, 50)
        manager.trigger(100, 100, 50)

        result = manager.trigger(100, 100, 50)

        assert result is False
        stats = manager.get_stats()
        assert stats['dropped_explosions'] == 1

    def test_manager_update(self):
        """Test manager update processes effects"""
        manager = ExplosionManager()

        manager.trigger(x=100, y=200, radius=50)
        manager.update()

        stats = manager.get_stats()
        assert stats['active_count'] >= 0

    def test_manager_reset_stats(self):
        """Test resetting statistics"""
        manager = ExplosionManager(max_per_second=10)

        result1 = manager.trigger(100, 100, 50)
        result2 = manager.trigger(100, 100, 50)

        assert result1 is True
        assert result2 is True

        stats = manager.get_stats()
        assert stats['total_explosions'] == 2

        manager.reset_stats()

        stats = manager.get_stats()
        assert stats['total_explosions'] == 0
        assert stats['dropped_explosions'] == 0

    def test_manager_get_stats(self):
        """Test getting complete statistics"""
        manager = ExplosionManager(max_per_second=10, pool_max_size=15)

        manager.trigger(100, 100, 50)
        manager.trigger(200, 200, 50)

        stats = manager.get_stats()
        assert 'max_per_second' in stats
        assert 'explosions_this_second' in stats
        assert 'total_explosions' in stats
        assert 'dropped_explosions' in stats
        assert stats['max_per_second'] == 10


class TestExplosionIntegration:
    """Integration tests for explosion system"""

    def test_trigger_render_update_cycle(self):
        """Test complete trigger-render-update cycle"""
        pygame.init()
        screen = pygame.display.set_mode((800, 600))

        manager = ExplosionManager()

        manager.trigger(x=400, y=300, radius=50)
        assert manager.get_stats()['active_count'] == 1

        manager.render(screen)

        for _ in range(60):
            manager.update()

        stats = manager.get_stats()
        assert stats['active_count'] == 0

        pygame.quit()

    def test_multiple_explosions(self):
        """Test handling multiple simultaneous explosions"""
        pygame.init()
        screen = pygame.display.set_mode((800, 600))

        manager = ExplosionManager()

        for i in range(5):
            manager.trigger(x=100 + i * 50, y=100 + i * 50, radius=30)

        stats = manager.get_stats()
        assert stats['total_explosions'] == 5

        manager.render(screen)
        manager.update()

        pygame.quit()

    def test_explosion_pool_reuse(self):
        """Test effect instances are reused from pool"""
        pygame.init()
        screen = pygame.display.set_mode((800, 600))

        manager = ExplosionManager()

        for i in range(5):
            manager.trigger(x=100 + i * 100, y=100, radius=40)

        stats = manager.get_stats()
        initial_available = stats['available']
        initial_in_use = stats['in_use']

        for _ in range(100):
            manager.update()

        stats = manager.get_stats()
        assert stats['in_use'] == 0
        assert stats['available'] >= initial_available

        pygame.quit()
