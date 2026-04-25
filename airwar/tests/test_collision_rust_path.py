"""Tests for collision detection, specifically the Rust collision path and bullet single-hit fix."""
import pytest
import pygame
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from airwar.core_bindings import RUST_AVAILABLE


# Mock classes that mirror the real collision behavior but use simpler coordinates
class MockRect:
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


class MockEnemy:
    def __init__(self, health=100, active=True, centerx=0, centery=0):
        self.health = health
        self.active = active
        self.data = type('obj', (object,), {'score': 100, 'damage': 20})()
        # Use same dimensions as collision_controller expects (hitbox is used for collision)
        hitbox_size = 30
        self.rect = MockRect(centerx=centerx, centery=centery, width=hitbox_size, height=hitbox_size)
        self._hitbox = MockRect(centerx=centerx, centery=centery, width=hitbox_size, height=hitbox_size)

    def get_hitbox(self):
        return self._hitbox

    def get_rect(self):
        return self.rect

    def take_damage(self, damage):
        self.health -= damage
        if self.health <= 0:
            self.active = False
            return 100
        return 0


class MockBullet:
    def __init__(self, active=True, damage=10, centerx=0, centery=0):
        self.active = active
        self.data = type('obj', (object,), {'damage': damage, 'owner': 'player'})()
        self.rect = MockRect(centerx=centerx, centery=centery, width=5, height=10)

    def get_rect(self):
        return self.rect


class TestCollisionBulletSingleHit:
    """Tests that verify a bullet only hits one enemy (not multiple).

    These tests specifically test the fix for a bug where the Rust collision
    path was missing a 'break' statement, causing bullets to potentially
    hit multiple enemies in a single frame.
    """

    @pytest.fixture(autouse=True)
    def setup_pygame(self):
        pygame.init()
        yield
        pygame.quit()

    def test_bullet_hits_only_one_enemy_in_rust_path(self):
        """When using Rust collision, a bullet should only hit one enemy.

        This tests the fix for the missing 'break' statement in the Rust collision path.
        With high-damage bullets, we can verify only one enemy dies.
        """
        from airwar.game.managers.collision_controller import CollisionController

        if not RUST_AVAILABLE:
            pytest.skip("Rust core not available")

        controller = CollisionController()
        assert controller._use_rust is True

        # Create a bullet and multiple overlapping enemies
        # Bullet at center (400, 400) with high damage
        bullet = MockBullet(active=True, damage=50, centerx=400, centery=400)

        # Two enemies at the same position - bullet can only hit ONE due to break statement
        # Use low health so they die in one hit
        enemy1 = MockEnemy(health=30, active=True, centerx=400, centery=400)
        enemy2 = MockEnemy(health=30, active=True, centerx=400, centery=400)

        enemies = [enemy1, enemy2]

        # Use the Rust path
        score_gained, enemies_killed = controller.check_player_bullets_vs_enemies(
            [bullet], enemies, 1, 0
        )

        # The key assertion: bullet should become inactive after hitting ANY enemy
        # This verifies the 'break' statement fix
        assert bullet.active is False, "Bullet should be inactive after hitting an enemy"

        # Only one enemy should be killed (bullet hits only one due to break)
        killed_count = sum(1 for e in enemies if not e.active)
        assert killed_count == 1, f"Expected exactly 1 enemy killed, got {killed_count}"

    def test_multiple_bullets_hit_different_enemies(self):
        """Multiple bullets should each hit a different enemy when spaced apart."""
        from airwar.game.managers.collision_controller import CollisionController

        if not RUST_AVAILABLE:
            pytest.skip("Rust core not available")

        controller = CollisionController()

        # 3 bullets at different positions with high damage
        bullets = [
            MockBullet(active=True, damage=50, centerx=100, centery=100),
            MockBullet(active=True, damage=50, centerx=200, centery=100),
            MockBullet(active=True, damage=50, centerx=300, centery=100),
        ]

        # 3 enemies at matching positions with low health
        enemies = [
            MockEnemy(health=30, active=True, centerx=100, centery=100),
            MockEnemy(health=30, active=True, centerx=200, centery=100),
            MockEnemy(health=30, active=True, centerx=300, centery=100),
        ]

        # Process all collisions
        total_killed = 0
        for bullet in bullets:
            sg, ek = controller.check_player_bullets_vs_enemies(
                [bullet], enemies, 1, 0
            )
            total_killed += ek

        # Each bullet should have hit its target
        assert total_killed == 3, f"Expected 3 kills, got {total_killed}"

        # All bullets should now be inactive
        active_bullets = sum(1 for b in bullets if b.active)
        assert active_bullets == 0, f"Expected 0 active bullets after all hits, got {active_bullets}"

    def test_bullet_becomes_inactive_after_single_hit(self):
        """A bullet should become inactive after hitting any enemy."""
        from airwar.game.managers.collision_controller import CollisionController

        if not RUST_AVAILABLE:
            pytest.skip("Rust core not available")

        controller = CollisionController()

        # One bullet
        bullet = MockBullet(active=True, damage=999, centerx=400, centery=400)

        # Multiple enemies stacked - bullet has high damage but should still become inactive
        enemies = [
            MockEnemy(health=50, active=True, centerx=400, centery=400),
            MockEnemy(health=50, active=True, centerx=400, centery=400),
            MockEnemy(health=50, active=True, centerx=400, centery=400),
        ]

        sg, ek = controller.check_player_bullets_vs_enemies(
            [bullet], enemies, 1, 0
        )

        # The critical assertion: bullet must be inactive after ANY hit
        assert bullet.active is False, "Bullet must be inactive after any hit (tests the 'break' fix)"


class TestCollisionControllerWithRealEntities:
    """Integration tests using real Entity classes."""

    @pytest.fixture(autouse=True)
    def setup_pygame(self):
        pygame.init()
        yield
        pygame.quit()

    def test_player_bullets_vs_enemies_collision(self):
        """Test with real Enemy and Bullet classes."""
        from airwar.game.managers.collision_controller import CollisionController
        from airwar.entities import Bullet, BulletData, Enemy, EnemyData

        controller = CollisionController()

        # Create bullet and enemy at same position
        # Use high damage bullet to kill in one hit
        bullet = Bullet(400, 400, BulletData(damage=200))
        bullet.active = True

        enemy = Enemy(400, 400, EnemyData(health=100))
        enemy.active = True

        # Get their rects to verify collision
        bullet_rect = bullet.rect
        enemy_hitbox = enemy.get_hitbox()

        # Verify they should collide
        assert bullet_rect.colliderect(enemy_hitbox), "Bullet and enemy should collide"

        score_gained, enemies_killed = controller.check_player_bullets_vs_enemies(
            [bullet], [enemy], 1, 0
        )

        assert enemies_killed == 1, f"Expected 1 enemy killed, got {enemies_killed}"
        assert bullet.active is False, "Bullet should be inactive after hit"

    def test_bullets_deactivate_after_hitting_enemies(self):
        """Verify bullets become inactive after collision."""
        from airwar.game.managers.collision_controller import CollisionController
        from airwar.entities import Bullet, BulletData, Enemy, EnemyData

        controller = CollisionController()

        # Use high damage bullets to kill in one hit
        bullets = [
            Bullet(100, 100, BulletData(damage=200)),  # Will hit
            Bullet(500, 500, BulletData(damage=200)),  # Won't hit (no enemy)
            Bullet(200, 200, BulletData(damage=200)),  # Will hit
        ]
        for b in bullets:
            b.active = True

        enemies = [
            Enemy(100, 100, EnemyData(health=50)),  # At same pos as bullet 1
            Enemy(200, 200, EnemyData(health=50)),  # At same pos as bullet 3
        ]
        for e in enemies:
            e.active = True

        total_killed = 0
        for bullet in bullets:
            sg, ek = controller.check_player_bullets_vs_enemies(
                [bullet], enemies, 1, 0
            )
            total_killed += ek

        # Bullets that hit should be inactive
        assert bullets[0].active is False, "Bullet 1 should be inactive after hitting"
        assert bullets[1].active is True, "Bullet 2 should still be active (no hit)"
        assert bullets[2].active is False, "Bullet 3 should be inactive after hitting"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
