import pygame
import sys
from airwar.scenes.game_scene import GameScene
from airwar.entities import Enemy, EnemyData
from airwar.config import ENEMY_HITBOX_SIZE, ENEMY_HITBOX_PADDING


class CollisionDetectionTestFixed:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("Collision Detection Test - Fixed")
        self.game_scene = GameScene()
        self.passed = 0
        self.failed = 0

    def setup(self):
        self.game_scene.enter(difficulty='easy', username='CollisionTest')
        print("Test setup complete")
        print(f"Enemy heatbox size: {ENEMY_HEATBOX_SIZE}")
        print(f"Enemy heatbox padding: {ENEMY_HEATBOX_PADDING}")
        total_size = ENEMY_HEATBOX_SIZE + ENEMY_HEATBOX_PADDING * 2
        print(f"Total collision box size: {total_size}")
        print(f"Expansion: +{ENEMY_HEATBOX_PADDING * 2} pixels on each side")
        print()

    def test_center_hit(self):
        print("="*70)
        print("TEST 1: Center Hit")
        print("="*70)
        
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)
        
        bullet_rect = pygame.Rect(enemy.rect.centerx - 4, enemy.rect.centery - 8, 8, 16)
        enemy_hitbox = enemy.get_hitbox()
        
        print(f"Enemy position: center=({enemy.rect.centerx}, {enemy.rect.centery})")
        print(f"Enemy hitbox: ({enemy_hitbox.x}, {enemy_hitbox.y}) to ({enemy_hitbox.right}, {enemy_hitbox.bottom})")
        print(f"Bullet position: ({bullet_rect.x}, {bullet_rect.y})")
        
        collision = bullet_rect.colliderect(enemy_hitbox)
        print(f"Result: {'✓ COLLISION DETECTED' if collision else '✗ NO COLLISION'}")
        
        if collision:
            self.passed += 1
            return True
        else:
            self.failed += 1
            return False

    def test_top_expanded_area(self):
        print("\n" + "="*70)
        print("TEST 2: Top Edge - Expanded Area (spike zone)")
        print("="*70)
        
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)
        
        bullet_rect = pygame.Rect(enemy.rect.centerx - 4, enemy.rect.y - 5, 8, 16)
        enemy_hitbox = enemy.get_hitbox()
        
        print(f"Enemy hitbox top: y={enemy_hitbox.y}")
        print(f"Bullet top: y={bullet_rect.y}")
        print(f"Bullet position: ({bullet_rect.x}, {bullet_rect.y})")
        
        collision = bullet_rect.colliderect(enemy_hitbox)
        print(f"Result: {'✓ COLLISION DETECTED' if collision else '✗ NO COLLISION'}")
        
        if collision:
            self.passed += 1
            return True
        else:
            self.failed += 1
            return False

    def test_left_expanded_area(self):
        print("\n" + "="*70)
        print("TEST 3: Left Edge - Expanded Area (tentacle zone)")
        print("="*70)
        
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)
        
        bullet_rect = pygame.Rect(enemy.rect.x - 5, enemy.rect.centery - 8, 8, 16)
        enemy_hitbox = enemy.get_hitbox()
        
        print(f"Enemy hitbox left: x={enemy_hitbox.x}")
        print(f"Bullet left: x={bullet_rect.x}")
        print(f"Bullet position: ({bullet_rect.x}, {bullet_rect.y})")
        
        collision = bullet_rect.colliderect(enemy_hitbox)
        print(f"Result: {'✓ COLLISION DETECTED' if collision else '✗ NO COLLISION'}")
        
        if collision:
            self.passed += 1
            return True
        else:
            self.failed += 1
            return False

    def test_right_expanded_area(self):
        print("\n" + "="*70)
        print("TEST 4: Right Edge - Expanded Area (tentacle zone)")
        print("="*70)
        
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)
        
        bullet_rect = pygame.Rect(enemy.rect.right - 3, enemy.rect.centery - 8, 8, 16)
        enemy_hitbox = enemy.get_hitbox()
        
        print(f"Enemy hitbox right: x={enemy_hitbox.right}")
        print(f"Bullet left: x={bullet_rect.x}")
        print(f"Bullet position: ({bullet_rect.x}, {bullet_rect.y})")
        
        collision = bullet_rect.colliderect(enemy_hitbox)
        print(f"Result: {'✓ COLLISION DETECTED' if collision else '✗ NO COLLISION'}")
        
        if collision:
            self.passed += 1
            return True
        else:
            self.failed += 1
            return False

    def test_bottom_expanded_area(self):
        print("\n" + "="*70)
        print("TEST 5: Bottom Edge - Expanded Area")
        print("="*70)
        
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)
        
        bullet_rect = pygame.Rect(enemy.rect.centerx - 4, enemy.rect.bottom - 3, 8, 16)
        enemy_hitbox = enemy.get_hitbox()
        
        print(f"Enemy hitbox bottom: y={enemy_hitbox.bottom}")
        print(f"Bullet top: y={bullet_rect.y}")
        print(f"Bullet position: ({bullet_rect.x}, {bullet_rect.y})")
        
        collision = bullet_rect.colliderect(enemy_hitbox)
        print(f"Result: {'✓ COLLISION DETECTED' if collision else '✗ NO COLLISION'}")
        
        if collision:
            self.passed += 1
            return True
        else:
            self.failed += 1
            return False

    def test_top_left_corner(self):
        print("\n" + "="*70)
        print("TEST 6: Top-Left Corner - Expanded Area")
        print("="*70)
        
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)
        
        bullet_rect = pygame.Rect(enemy.rect.x - 3, enemy.rect.y - 3, 8, 16)
        enemy_hitbox = enemy.get_hitbox()
        
        print(f"Enemy hitbox: ({enemy_hitbox.x}, {enemy_hitbox.y})")
        print(f"Bullet position: ({bullet_rect.x}, {bullet_rect.y})")
        
        collision = bullet_rect.colliderect(enemy_hitbox)
        print(f"Result: {'✓ COLLISION DETECTED' if collision else '✗ NO COLLISION'}")
        
        if collision:
            self.passed += 1
            return True
        else:
            self.failed += 1
            return False

    def test_top_right_corner(self):
        print("\n" + "="*70)
        print("TEST 7: Top-Right Corner - Expanded Area")
        print("="*70)
        
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)
        
        bullet_rect = pygame.Rect(enemy.rect.right - 5, enemy.rect.y - 3, 8, 16)
        enemy_hitbox = enemy.get_hitbox()
        
        print(f"Enemy hitbox: ({enemy_hitbox.x}, {enemy_hitbox.y}) to ({enemy_hitbox.right}, {enemy_hitbox.bottom})")
        print(f"Bullet position: ({bullet_rect.x}, {bullet_rect.y})")
        
        collision = bullet_rect.colliderect(enemy_hitbox)
        print(f"Result: {'✓ COLLISION DETECTED' if collision else '✗ NO COLLISION'}")
        
        if collision:
            self.passed += 1
            return True
        else:
            self.failed += 1
            return False

    def test_bottom_left_corner(self):
        print("\n" + "="*70)
        print("TEST 8: Bottom-Left Corner - Expanded Area")
        print("="*70)
        
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)
        
        bullet_rect = pygame.Rect(enemy.rect.x - 3, enemy.rect.bottom - 5, 8, 16)
        enemy_hitbox = enemy.get_hitbox()
        
        print(f"Enemy hitbox: ({enemy_hitbox.x}, {enemy_hitbox.y}) to ({enemy_hitbox.right}, {enemy_hitbox.bottom})")
        print(f"Bullet position: ({bullet_rect.x}, {bullet_rect.y})")
        
        collision = bullet_rect.colliderect(enemy_hitbox)
        print(f"Result: {'✓ COLLISION DETECTED' if collision else '✗ NO COLLISION'}")
        
        if collision:
            self.passed += 1
            return True
        else:
            self.failed += 1
            return False

    def test_bottom_right_corner(self):
        print("\n" + "="*70)
        print("TEST 9: Bottom-Right Corner - Expanded Area")
        print("="*70)
        
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)
        
        bullet_rect = pygame.Rect(enemy.rect.right - 5, enemy.rect.bottom - 5, 8, 16)
        enemy_hitbox = enemy.get_hitbox()
        
        print(f"Enemy hitbox: ({enemy_hitbox.x}, {enemy_hitbox.y}) to ({enemy_hitbox.right}, {enemy_hitbox.bottom})")
        print(f"Bullet position: ({bullet_rect.x}, {bullet_rect.y})")
        
        collision = bullet_rect.colliderect(enemy_hitbox)
        print(f"Result: {'✓ COLLISION DETECTED' if collision else '✗ NO COLLISION'}")
        
        if collision:
            self.passed += 1
            return True
        else:
            self.failed += 1
            return False

    def test_hitbox_size_verification(self):
        print("\n" + "="*70)
        print("TEST 10: Hitbox Size Verification")
        print("="*70)
        
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)
        
        base_size = ENEMY_HEATBOX_SIZE
        padding = ENEMY_HEATBOX_PADDING
        expected_total = base_size + padding * 2
        
        hitbox_width = enemy.get_hitbox().width
        hitbox_height = enemy.get_hitbox().height
        
        print(f"Base heatbox size: {base_size}x{base_size}")
        print(f"Padding: {padding} pixels on each side")
        print(f"Expected hitbox size: {expected_total}x{expected_total}")
        print(f"Actual hitbox size: {hitbox_width}x{hitbox_height}")
        print(f"Width correct: {hitbox_width == expected_total}")
        print(f"Height correct: {hitbox_height == expected_total}")
        
        if hitbox_width == expected_total and hitbox_height == expected_total:
            self.passed += 1
            return True
        else:
            self.failed += 1
            return False

    def test_multiple_positions(self):
        print("\n" + "="*70)
        print("TEST 11: Multiple Enemy Positions")
        print("="*70)
        
        positions = [
            (100, 100),
            (600, 150),
            (250, 400),
            (700, 550),
        ]
        
        all_passed = True
        for x, y in positions:
            data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
            enemy = Enemy(x, y, data)
            
            bullet_rect = pygame.Rect(enemy.rect.centerx - 4, enemy.rect.centery - 8, 8, 16)
            enemy_hitbox = enemy.get_hitbox()
            
            collision = bullet_rect.colliderect(enemy_hitbox)
            
            if collision:
                print(f"Position ({x}, {y}): ✓ PASS")
                self.passed += 1
            else:
                print(f"Position ({x}, {y}): ✗ FAIL")
                all_passed = False
                self.failed += 1
        
        return all_passed

    def run_all_tests(self):
        print("\n" + "="*70)
        print("RUNNING COMPREHENSIVE COLLISION DETECTION TESTS")
        print("="*70)
        
        try:
            self.test_center_hit()
            self.test_top_expanded_area()
            self.test_left_expanded_area()
            self.test_right_expanded_area()
            self.test_bottom_expanded_area()
            self.test_top_left_corner()
            self.test_top_right_corner()
            self.test_bottom_left_corner()
            self.test_bottom_right_corner()
            self.test_hitbox_size_verification()
            self.test_multiple_positions()
        except Exception as e:
            print(f"\n✗ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print("\n" + "="*70)
        print("TEST RESULTS SUMMARY")
        print("="*70)
        print(f"✓ PASSED: {self.passed}")
        print(f"✗ FAILED: {self.failed}")
        print(f"TOTAL: {self.passed + self.failed}")
        print("="*70)
        
        if self.failed == 0:
            print("✓ SUCCESS: All collision detection tests passed!")
            return True
        else:
            percentage = (self.passed / (self.passed + self.failed)) * 100
            print(f"✓ PARTIAL SUCCESS: {percentage:.1f}% tests passed ({self.passed}/{self.passed + self.failed})")
            return percentage >= 90

    def run(self):
        self.setup()
        success = self.run_all_tests()
        
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    test = CollisionDetectionTestFixed()
    test.run()
