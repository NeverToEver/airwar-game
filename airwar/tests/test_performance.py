"""Performance Tests

测试游戏关键功能的性能:
- 碰撞检测性能
- 子弹更新性能
- 游戏循环性能
"""

import pytest
import time
from airwar.game.controllers.collision_controller import CollisionController


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
    """碰撞检测性能测试"""
    
    def test_collision_detection_performance_small_scale(self):
        """测试小规模碰撞检测性能 (10子弹 x 10敌人)"""
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
        """测试中等规模碰撞检测性能 (50子弹 x 50敌人)"""
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
        """测试大规模碰撞检测性能 (100子弹 x 100敌人)"""
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
    """子弹更新性能测试"""
    
    def test_bullet_update_performance(self):
        """测试大量子弹更新的性能 (100子弹)"""
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
    """爆炸伤害性能测试"""
    
    def test_explosive_damage_performance(self):
        """测试爆炸伤害的性能 (50敌人范围伤害)"""
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
