"""Performance Tests

Tests for game critical functionality performance:
- Collision detection performance
- Bullet update performance
- Game loop performance
"""

import pytest
import time
from airwar.game.managers.collision_controller import CollisionController


class MockHitbox:
    """Mock hitbox for performance testing"""
    def __init__(self, centerx=0, centery=0, width=12, height=16):
        self.centerx = centerx
        self.centery = centery
        self.width = width
        self.height = height
    
    def colliderect(self, other):
        ax1 = self.centerx - self.width // 2
        ay1 = self.centery - self.height // 2
        ax2 = ax1 + self.width
        ay2 = ay1 + self.height
        
        bx1 = other.centerx - other.width // 2
        by1 = other.centery - other.height // 2
        bx2 = bx1 + other.width
        by2 = by1 + other.height
        
        return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1


class MockBullet:
    """Mock bullet for performance testing"""
    def __init__(self, centerx=0, centery=0):
        self.active = True
        self.data = type('obj', (object,), {'damage': 10, 'owner': 'player'})()
        self.rect = MockHitbox(centerx=centerx, centery=centery, width=5, height=10)
    
    def get_rect(self):
        return self.rect
    
    def update(self):
        pass


class MockEnemy:
    """Mock enemy for performance testing"""
    def __init__(self, centerx=0, centery=0):
        self.health = 100
        self.active = True
        self.data = type('obj', (object,), {'score': 100, 'damage': 20})()
        self.rect = MockHitbox(centerx=centerx, centery=centery, width=30, height=30)
    
    def get_hitbox(self):
        return self.rect
    
    def get_rect(self):
        return self.rect
    
    def take_damage(self, damage):
        self.health -= damage
        if self.health <= 0:
            self.active = False
            return 100
        return 0


class TestCollisionPerformance:
    """Collision detection performance tests"""
    
    def test_collision_detection_performance_small_scale(self):
        """Test small scale collision detection (10 bullets x 10 enemies)"""
        controller = CollisionController()
        
        bullets = [MockBullet() for _ in range(10)]
        enemies = [MockEnemy() for _ in range(10)]
        
        iterations = 1000
        start = time.perf_counter()
        
        for _ in range(iterations):
            controller.check_player_bullets_vs_enemies(
                bullets, enemies, score_multiplier=1, explosive_level=0
            )
        
        elapsed = time.perf_counter() - start
        avg_time_ms = (elapsed / iterations) * 1000
        
        assert avg_time_ms < 1.0, f"Collision check too slow: {avg_time_ms:.3f}ms (expected <1.0ms)"
    
    def test_collision_detection_performance_medium_scale(self):
        """Test medium scale collision detection (50 bullets x 50 enemies)"""
        controller = CollisionController()
        
        bullets = [MockBullet() for _ in range(50)]
        enemies = [MockEnemy() for _ in range(50)]
        
        iterations = 100
        start = time.perf_counter()
        
        for _ in range(iterations):
            controller.check_player_bullets_vs_enemies(
                bullets, enemies, score_multiplier=1, explosive_level=0
            )
        
        elapsed = time.perf_counter() - start
        avg_time_ms = (elapsed / iterations) * 1000
        
        assert avg_time_ms < 10.0, f"Collision check too slow: {avg_time_ms:.3f}ms (expected <10.0ms)"
    
    def test_collision_detection_performance_large_scale(self):
        """Test large scale collision detection (100 bullets x 100 enemies)"""
        controller = CollisionController()
        
        bullets = [MockBullet() for _ in range(100)]
        enemies = [MockEnemy() for _ in range(100)]
        
        iterations = 10
        start = time.perf_counter()
        
        for _ in range(iterations):
            controller.check_player_bullets_vs_enemies(
                bullets, enemies, score_multiplier=1, explosive_level=0
            )
        
        elapsed = time.perf_counter() - start
        avg_time_ms = (elapsed / iterations) * 1000
        
        assert avg_time_ms < 16.0, f"Collision check too slow: {avg_time_ms:.3f}ms (expected <16.0ms for 60fps)"


class TestBulletUpdatePerformance:
    """Bullet update performance tests"""
    
    def test_bullet_update_performance(self):
        """Test large scale bullet update performance (100 bullets)"""
        bullets = [MockBullet() for _ in range(100)]
        
        iterations = 1000
        start = time.perf_counter()
        
        for _ in range(iterations):
            for bullet in bullets:
                bullet.update()
        
        elapsed = time.perf_counter() - start
        avg_time_ms = (elapsed / iterations) * 1000
        
        assert avg_time_ms < 5.0, f"Bullet update too slow: {avg_time_ms:.3f}ms (expected <5.0ms)"


class TestExplosiveDamagePerformance:
    """Explosive damage performance tests"""
    
    def test_explosive_damage_performance(self):
        """Test explosive damage performance (50 enemy AoE damage)"""
        controller = CollisionController()
        
        bullet = MockBullet()
        bullet.rect = type('obj', (object,), {'centerx': 400, 'centery': 300})()
        
        enemies = [MockEnemy() for _ in range(50)]
        
        iterations = 100
        start = time.perf_counter()
        
        for _ in range(iterations):
            controller._handle_explosive_damage(bullet, enemies, explosive_level=2)
        
        elapsed = time.perf_counter() - start
        avg_time_ms = (elapsed / iterations) * 1000
        
        assert avg_time_ms < 2.0, f"Explosive damage too slow: {avg_time_ms:.3f}ms (expected <2.0ms)"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
