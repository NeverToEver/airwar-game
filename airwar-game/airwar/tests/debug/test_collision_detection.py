import pygame
import sys
from airwar.scenes.game_scene import GameScene
from airwar.entities import Enemy, EnemyData
from airwar.config import ENEMY_HITBOX_SIZE, ENEMY_HITBOX_PADDING


class CollisionDetectionTest:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("Collision Detection Test")
        self.game_scene = GameScene()
        self.passed = 0
        self.failed = 0

    def setup(self):
        self.game_scene.enter(difficulty='easy', username='CollisionTest')
        print("Test setup complete")
        print(f"Enemy heatbox size: {ENEMY_HEATBOX_SIZE}")
        print(f"Enemy heatbox padding: {ENEMY_HEATBOX_PADDING}")
        print(f"Total collision box size: {ENEMY_HEATBOX_SIZE + ENEMY_HEATBOX_PADDING * 2}")

    def test_center_hit(self):
        print("\n" + "="*60)
        print("TEST 1: Center Hit")
        print("="*60)
        
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)
        
        bullets = self.game_scene.player.get_bullets()
        bullet = bullets[0] if bullets else None
        
        if not bullet:
            bullet_rect = pygame.Rect(400, 290, 8, 16)
        else:
            bullet_rect = bullet.get_rect()
        
        enemy_hitbox = enemy.get_hitbox()
        
        print(f"Enemy rect: x={enemy.rect.x}, y={enemy.rect.y}, w={enemy.rect.width}, h={enemy.rect.height}")
        print(f"Enemy hitbox: x={enemy_hitbox.x}, y={enemy_hitbox.y}, w={enemy_hitbox.width}, h={enemy_hitbox.height}")
        print(f"Bullet rect: x={bullet_rect.x}, y={bullet_rect.y}, w={bullet_rect.width}, h={bullet_rect.height}")
        
        collision = bullet_rect.colliderect(enemy_hitbox)
        print(f"Center hit collision detected: {collision}")
        
        if collision:
            print("✓ PASSED: Center hit detected")
            self.passed += 1
            return True
        else:
            print("✗ FAILED: Center hit not detected")
            self.failed += 1
            return False

    def test_edge_hit_top_left(self):
        print("\n" + "="*60)
        print("TEST 2: Edge Hit - Top Left (tentacle area)")
        print("="*60)
        
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)
        
        bullet_rect = pygame.Rect(enemy.rect.x - 5, enemy.rect.y - 5, 8, 16)
        enemy_hitbox = enemy.get_hitbox()
        
        print(f"Enemy hitbox: x={enemy_hitbox.x}, y={enemy_hitbox.y}, w={enemy_hitbox.width}, h={enemy_hitbox.height}")
        print(f"Bullet rect (top-left edge): x={bullet_rect.x}, y={bullet_rect.y}")
        
        collision = bullet_rect.colliderect(enemy_hitbox)
        print(f"Top-left edge collision detected: {collision}")
        
        if collision:
            print("✓ PASSED: Top-left edge hit detected")
            self.passed += 1
            return True
        else:
            print("✗ FAILED: Top-left edge hit not detected")
            self.failed += 1
            return False

    def test_edge_hit_bottom_right(self):
        print("\n" + "="*60)
        print("TEST 3: Edge Hit - Bottom Right (tentacle area)")
        print("="*60)
        
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)
        
        bullet_rect = pygame.Rect(enemy.rect.x + enemy.rect.width - 3, enemy.rect.y + enemy.rect.height - 5, 8, 16)
        enemy_hitbox = enemy.get_hitbox()
        
        print(f"Enemy hitbox: x={enemy_hitbox.x}, y={enemy_hitbox.y}, w={enemy_hitbox.width}, h={enemy_hitbox.height}")
        print(f"Bullet rect (bottom-right edge): x={bullet_rect.x}, y={bullet_rect.y}")
        
        collision = bullet_rect.colliderect(enemy_hitbox)
        print(f"Bottom-right edge collision detected: {collision}")
        
        if collision:
            print("✓ PASSED: Bottom-right edge hit detected")
            self.passed += 1
            return True
        else:
            print("✗ FAILED: Bottom-right edge hit not detected")
            self.failed += 1
            return False

    def test_corner_hit_top_right(self):
        print("\n" + "="*60)
        print("TEST 4: Corner Hit - Top Right (spike area)")
        print("="*60)
        
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)
        
        bullet_rect = pygame.Rect(enemy.rect.x + enemy.rect.width + 5, enemy.rect.y - 5, 8, 16)
        enemy_hitbox = enemy.get_hitbox()
        
        print(f"Enemy hitbox: x={enemy_hitbox.x}, y={enemy_hitbox.y}, w={enemy_hitbox.width}, h={enemy_hitbox.height}")
        print(f"Bullet rect (top-right corner): x={bullet_rect.x}, y={bullet_rect.y}")
        
        collision = bullet_rect.colliderect(enemy_hitbox)
        print(f"Top-right corner collision detected: {collision}")
        
        if collision:
            print("✓ PASSED: Top-right corner hit detected")
            self.passed += 1
            return True
        else:
            print("✗ FAILED: Top-right corner hit not detected")
            self.failed += 1
            return False

    def test_multiple_enemy_positions(self):
        print("\n" + "="*60)
        print("TEST 5: Multiple Enemy Positions")
        print("="*60)
        
        test_cases = [
            (100, 100, "Top-left area"),
            (600, 200, "Top-right area"),
            (200, 400, "Bottom-left area"),
            (650, 500, "Bottom-right area"),
        ]
        
        all_passed = True
        for x, y, description in test_cases:
            data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
            enemy = Enemy(x, y, data)
            
            bullet_rect = pygame.Rect(enemy.rect.centerx - 4, enemy.rect.centery - 8, 8, 16)
            enemy_hitbox = enemy.get_hitbox()
            
            collision = bullet_rect.colliderect(enemy_hitbox)
            print(f"{description}: collision={collision}")
            
            if not collision:
                all_passed = False
                print(f"  ✗ FAILED at {description}")
            else:
                print(f"  ✓ PASSED at {description}")
        
        if all_passed:
            print("✓ PASSED: All positions detected")
            self.passed += 1
            return True
        else:
            print("✗ FAILED: Some positions not detected")
            self.failed += 1
            return False

    def test_hitbox_expansion(self):
        print("\n" + "="*60)
        print("TEST 6: Hitbox Expansion Verification")
        print("="*60)
        
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)
        
        base_size = ENEMY_HEATBOX_SIZE
        padding = ENEMY_HEATBOX_PADDING
        expected_size = base_size + padding * 2
        
        print(f"Base heatbox size: {base_size}")
        print(f"Padding: {padding}")
        print(f"Expected total size: {expected_size}")
        print(f"Actual hitbox width: {enemy.get_hitbox().width}")
        print(f"Actual hitbox height: {enemy.get_hitbox().height}")
        
        if enemy.get_hitbox().width == expected_size and enemy.get_hitbox().height == expected_size:
            print("✓ PASSED: Hitbox correctly expanded")
            self.passed += 1
            return True
        else:
            print("✗ FAILED: Hitbox expansion incorrect")
            self.failed += 1
            return False

    def test_diagonal_hit(self):
        print("\n" + "="*60)
        print("TEST 7: Diagonal Hit (angled trajectory)")
        print("="*60)
        
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)
        
        bullet_rect = pygame.Rect(enemy.rect.x - 10, enemy.rect.y - 10, 8, 16)
        enemy_hitbox = enemy.get_hitbox()
        
        print(f"Bullet at diagonal position: x={bullet_rect.x}, y={bullet_rect.y}")
        
        collision = bullet_rect.colliderect(enemy_hitbox)
        print(f"Diagonal collision detected: {collision}")
        
        if collision:
            print("✓ PASSED: Diagonal hit detected")
            self.passed += 1
            return True
        else:
            print("✗ FAILED: Diagonal hit not detected")
            self.failed += 1
            return False

    def run_all_tests(self):
        print("\n" + "="*60)
        print("RUNNING ALL COLLISION DETECTION TESTS")
        print("="*60)
        
        try:
            self.test_center_hit()
            self.test_edge_hit_top_left()
            self.test_edge_hit_bottom_right()
            self.test_corner_hit_top_right()
            self.test_multiple_enemy_positions()
            self.test_hitbox_expansion()
            self.test_diagonal_hit()
        except Exception as e:
            print(f"\n✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print("\n" + "="*60)
        print("TEST RESULTS SUMMARY")
        print("="*60)
        print(f"✓ PASSED: {self.passed}")
        print(f"✗ FAILED: {self.failed}")
        print(f"TOTAL: {self.passed + self.failed}")
        print("="*60)
        
        if self.failed == 0:
            print("✓ SUCCESS: All collision detection tests passed!")
            return True
        else:
            print(f"✗ FAILURE: {self.failed} test(s) failed")
            return False

    def run(self):
        self.setup()
        success = self.run_all_tests()
        
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    test = CollisionDetectionTest()
    test.run()
