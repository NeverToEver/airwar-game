import pytest
import pygame
from airwar.scenes.game_scene import GameScene
from airwar.entities import Enemy, EnemyData
from airwar.config import ENEMY_HITBOX_SIZE, ENEMY_HITBOX_PADDING, ENEMY_VISUAL_SCALE, ENEMY_COLLISION_SCALE

pygame.init()
pygame.display.set_mode((800, 600))


class TestEnemyHitboxExpansion:
    """Tests for enemy hitbox expansion feature"""

    def test_hitbox_padding_increased(self):
        """Verify that hitbox padding has been increased"""
        assert ENEMY_HITBOX_PADDING == 8, "ENEMY_HITBOX_PADDING should be 8"
        assert ENEMY_HITBOX_SIZE == 50, "ENEMY_HITBOX_SIZE should be 50"

    def test_enemy_hitbox_expanded_by_padding(self):
        """Verify enemy hitbox is correctly expanded (with scaling)"""
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)

        base_size = ENEMY_HITBOX_SIZE + ENEMY_HITBOX_PADDING * 2
        expected_collision_size = int(base_size * ENEMY_COLLISION_SCALE)
        hitbox = enemy.get_hitbox()

        assert hitbox.width == expected_collision_size, f"Expected collision width {expected_collision_size}, got {hitbox.width}"
        assert hitbox.height == expected_collision_size, f"Expected collision height {expected_collision_size}, got {hitbox.height}"

    def test_enemy_visual_size_scaled(self):
        """Verify enemy visual size is proportionally scaled"""
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)

        base_size = ENEMY_HITBOX_SIZE + ENEMY_HITBOX_PADDING * 2
        expected_visual_size = int(base_size * ENEMY_VISUAL_SCALE)

        assert enemy.rect.width == expected_visual_size, f"Expected visual width {expected_visual_size}, got {enemy.rect.width}"
        assert enemy.rect.height == expected_visual_size, f"Expected visual height {expected_visual_size}, got {enemy.rect.height}"

    def test_enemy_render_and_collision_sizes_differ(self):
        """Verify render and collision sizes are different"""
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)

        assert enemy.rect.width != enemy.get_hitbox().width, "Visual size should differ from collision size"
        assert enemy.rect.height != enemy.get_hitbox().height, "Visual size should differ from collision size"

    def test_collision_larger_than_visual(self):
        """Verify collision hitbox is larger than visual size"""
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)

        assert enemy.get_hitbox().width > enemy.rect.width, "Collision hitbox should be larger than visual"
        assert enemy.get_hitbox().height > enemy.rect.height, "Collision hitbox should be larger than visual"

    def test_enemy_get_hitbox_method_exists(self):
        """Verify get_hitbox method exists"""
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)

        assert hasattr(enemy, 'get_hitbox'), "Enemy should have get_hitbox method"
        hitbox = enemy.get_hitbox()
        assert isinstance(hitbox, pygame.Rect), "get_hitbox should return pygame.Rect"

    def test_enemy_check_point_collision_method_exists(self):
        """Verify check_point_collision method exists"""
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)

        assert hasattr(enemy, 'check_point_collision'), "Enemy should have check_point_collision method"


class TestCollisionDetectionEnhanced:
    """Tests for enhanced collision detection feature"""

    def test_center_collision_detected(self):
        """Test center collision detection"""
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)

        bullet_rect = pygame.Rect(enemy.rect.centerx - 4, enemy.rect.centery - 8, 8, 16)
        enemy_hitbox = enemy.get_hitbox()

        assert bullet_rect.colliderect(enemy_hitbox), "Center collision should be detected"

    def test_top_edge_collision_detected(self):
        """Test top edge collision detection"""
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)

        bullet_rect = pygame.Rect(enemy.rect.centerx - 4, enemy.rect.y - 5, 8, 16)
        enemy_hitbox = enemy.get_hitbox()

        assert bullet_rect.colliderect(enemy_hitbox), "Top edge collision should be detected"

    def test_left_edge_collision_detected(self):
        """Test left edge collision detection"""
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)

        bullet_rect = pygame.Rect(enemy.rect.x - 5, enemy.rect.centery - 8, 8, 16)
        enemy_hitbox = enemy.get_hitbox()

        assert bullet_rect.colliderect(enemy_hitbox), "Left edge collision should be detected"

    def test_right_edge_collision_detected(self):
        """Test right edge collision detection"""
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)

        bullet_rect = pygame.Rect(enemy.rect.right - 3, enemy.rect.centery - 8, 8, 16)
        enemy_hitbox = enemy.get_hitbox()

        assert bullet_rect.colliderect(enemy_hitbox), "Right edge collision should be detected"

    def test_bottom_edge_collision_detected(self):
        """Test bottom edge collision detection"""
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)

        bullet_rect = pygame.Rect(enemy.rect.centerx - 4, enemy.rect.bottom - 3, 8, 16)
        enemy_hitbox = enemy.get_hitbox()

        assert bullet_rect.colliderect(enemy_hitbox), "Bottom edge collision should be detected"

    def test_corner_collision_detected(self):
        """Test corner collision detection"""
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)

        bullet_rect = pygame.Rect(enemy.rect.x - 3, enemy.rect.y - 3, 8, 16)
        enemy_hitbox = enemy.get_hitbox()

        assert bullet_rect.colliderect(enemy_hitbox), "Corner collision should be detected"

    def test_multiple_positions_collision(self):
        """Test collision detection at multiple positions"""
        positions = [(100, 100), (600, 200), (300, 500), (700, 400)]

        for x, y in positions:
            data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
            enemy = Enemy(x, y, data)

            bullet_rect = pygame.Rect(enemy.rect.centerx - 4, enemy.rect.centery - 8, 8, 16)
            enemy_hitbox = enemy.get_hitbox()

            assert bullet_rect.colliderect(enemy_hitbox), f"Collision should be detected at position ({x}, {y})"


class TestMotherShipRippleClearIntegration:
    """Tests for mother ship ripple effect clearing integration"""

    def test_ripple_effects_initial_empty(self):
        """Verify ripple effects list starts empty"""
        scene = GameScene()
        scene.enter(difficulty='easy', username='TestPlayer')

        assert len(scene.game_controller.state.ripple_effects) == 0

    def test_ripple_effect_created_on_hit(self):
        """Verify ripple effect is created on hit"""
        scene = GameScene()
        scene.enter(difficulty='easy', username='TestPlayer')

        scene.game_controller.on_player_hit(20, scene.player)

        assert len(scene.game_controller.state.ripple_effects) == 1
        ripple = scene.game_controller.state.ripple_effects[0]
        assert 'x' in ripple
        assert 'y' in ripple
        assert 'radius' in ripple
        assert 'alpha' in ripple

    def test_ripple_effects_cleared_on_docking_start(self):
        """Verify ripple effects are cleared on docking start"""
        scene = GameScene()
        scene.enter(difficulty='easy', username='TestPlayer')

        scene.game_controller.on_player_hit(20, scene.player)
        assert len(scene.game_controller.state.ripple_effects) == 1

        event_bus = scene._mother_ship_integrator._event_bus
        event_bus.publish('H_PRESSED')

        for _ in range(3):
            scene._mother_ship_integrator.update()

        assert len(scene.game_controller.state.ripple_effects) == 0, "Ripple effects should be cleared on H_PRESSED"

    def test_ripple_effects_cleared_on_docked(self):
        """Verify ripple effects are cleared on docking complete"""
        scene = GameScene()
        scene.enter(difficulty='easy', username='TestPlayer')

        event_bus = scene._mother_ship_integrator._event_bus
        event_bus.publish('H_PRESSED')

        for _ in range(3):
            scene._mother_ship_integrator.update()

        scene.game_controller.on_player_hit(20, scene.player)
        assert len(scene.game_controller.state.ripple_effects) == 1

        event_bus.publish('PROGRESS_COMPLETE')

        for _ in range(3):
            scene._mother_ship_integrator.update()

        for _ in range(100):
            scene._mother_ship_integrator.update()
            if not scene._mother_ship_integrator.is_docking_animation_active():
                break

        assert len(scene.game_controller.state.ripple_effects) == 0, "Ripple effects should be cleared on DOCKED"

    def test_ripple_effects_cleared_on_undocking(self):
        """Verify ripple effects are cleared on undocking"""
        scene = GameScene()
        scene.enter(difficulty='easy', username='TestPlayer')

        event_bus = scene._mother_ship_integrator._event_bus
        event_bus.publish('H_PRESSED')
        for _ in range(3):
            scene._mother_ship_integrator.update()
        event_bus.publish('PROGRESS_COMPLETE')
        for _ in range(100):
            scene._mother_ship_integrator.update()
            if not scene._mother_ship_integrator.is_docking_animation_active():
                break

        event_bus.publish('H_PRESSED')
        for _ in range(3):
            scene._mother_ship_integrator.update()

        scene.game_controller.on_player_hit(20, scene.player)
        assert len(scene.game_controller.state.ripple_effects) == 1

        for _ in range(80):
            scene._mother_ship_integrator.update()
            if not scene._mother_ship_integrator.is_undocking_animation_active():
                break

        assert len(scene.game_controller.state.ripple_effects) == 0, "Ripple effects should be cleared on undocking"

    def test_ripple_effects_cleared_on_idle(self):
        """Verify ripple effects are cleared when returning to idle state"""
        scene = GameScene()
        scene.enter(difficulty='easy', username='TestPlayer')

        event_bus = scene._mother_ship_integrator._event_bus
        event_bus.publish('H_PRESSED')
        for _ in range(3):
            scene._mother_ship_integrator.update()

        scene.game_controller.on_player_hit(20, scene.player)
        assert len(scene.game_controller.state.ripple_effects) == 1

        event_bus.publish('H_RELEASED')
        for _ in range(3):
            scene._mother_ship_integrator.update()

        assert len(scene.game_controller.state.ripple_effects) == 0, "Ripple effects should be cleared on H_RELEASED"

    def test_multiple_ripples_cleared_together(self):
        """Verify multiple ripple effects are cleared together"""
        scene = GameScene()
        scene.enter(difficulty='easy', username='TestPlayer')

        for _ in range(3):
            scene.game_controller.on_player_hit(20, scene.player)
            for _ in range(10):
                scene._mother_ship_integrator.update()

        assert len(scene.game_controller.state.ripple_effects) == 3

        event_bus = scene._mother_ship_integrator._event_bus
        event_bus.publish('H_PRESSED')
        for _ in range(3):
            scene._mother_ship_integrator.update()

        assert len(scene.game_controller.state.ripple_effects) == 0, "All ripple effects should be cleared together"


class TestGameSceneCollisionIntegration:
    """Tests for game scene collision detection integration"""

    def test_bullet_enemy_collision_uses_expanded_hitbox(self):
        """Verify bullet-enemy collision uses expanded hitbox"""
        scene = GameScene()
        scene.enter(difficulty='easy', username='TestPlayer')

        enemy = Enemy(400, 300, EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight"))
        scene.spawn_controller.enemies.append(enemy)

        initial_health = enemy.health

        bullet = scene.player.fire()
        bullet.rect.x = enemy.rect.centerx - 4
        bullet.rect.y = enemy.rect.centery - 8

        scene.collision_controller.check_player_bullets_vs_enemies(
            scene.player.get_bullets(),
            scene.spawn_controller.enemies,
            1,
            0
        )

        assert enemy.health < initial_health, f"Enemy should take damage from expanded hitbox collision. Initial: {initial_health}, Current: {enemy.health}"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
