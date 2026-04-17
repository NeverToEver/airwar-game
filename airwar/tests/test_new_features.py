import pytest
import pygame
from airwar.scenes.game_scene import GameScene
from airwar.entities import Enemy, EnemyData
from airwar.config import ENEMY_HEATBOX_SIZE, ENEMY_HEATBOX_PADDING

pygame.init()
pygame.display.set_mode((800, 600))


class TestEnemyHeatboxExpansion:
    """测试敌机碰撞体扩展功能"""

    def test_heatbox_padding_increased(self):
        """验证碰撞体填充区域已增加"""
        assert ENEMY_HEATBOX_PADDING == 8, "ENEMY_HEATBOX_PADDING should be 8"
        assert ENEMY_HEATBOX_SIZE == 50, "ENEMY_HEATBOX_SIZE should be 50"

    def test_enemy_heatbox_expanded_by_padding(self):
        """验证敌机碰撞体已正确扩展"""
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)

        expected_size = ENEMY_HEATBOX_SIZE + ENEMY_HEATBOX_PADDING * 2
        hitbox = enemy.get_hitbox()

        assert hitbox.width == expected_size, f"Expected width {expected_size}, got {hitbox.width}"
        assert hitbox.height == expected_size, f"Expected height {expected_size}, got {hitbox.height}"

    def test_enemy_heatbox_position_offset(self):
        """验证碰撞体位置已正确偏移"""
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)

        padding = ENEMY_HEATBOX_PADDING
        expected_x = 400 - padding
        expected_y = 300 - padding

        assert enemy.rect.x == expected_x, f"Expected x {expected_x}, got {enemy.rect.x}"
        assert enemy.rect.y == expected_y, f"Expected y {expected_y}, got {enemy.rect.y}"

    def test_enemy_get_hitbox_method_exists(self):
        """验证get_hitbox方法存在"""
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)

        assert hasattr(enemy, 'get_hitbox'), "Enemy should have get_hitbox method"
        hitbox = enemy.get_hitbox()
        assert isinstance(hitbox, pygame.Rect), "get_hitbox should return pygame.Rect"

    def test_enemy_check_point_collision_method_exists(self):
        """验证check_point_collision方法存在"""
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)

        assert hasattr(enemy, 'check_point_collision'), "Enemy should have check_point_collision method"


class TestCollisionDetectionEnhanced:
    """测试增强的碰撞检测功能"""

    def test_center_collision_detected(self):
        """测试中央碰撞检测"""
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)

        bullet_rect = pygame.Rect(enemy.rect.centerx - 4, enemy.rect.centery - 8, 8, 16)
        enemy_hitbox = enemy.get_hitbox()

        assert bullet_rect.colliderect(enemy_hitbox), "Center collision should be detected"

    def test_top_edge_collision_detected(self):
        """测试顶部边缘碰撞检测"""
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)

        bullet_rect = pygame.Rect(enemy.rect.centerx - 4, enemy.rect.y - 5, 8, 16)
        enemy_hitbox = enemy.get_hitbox()

        assert bullet_rect.colliderect(enemy_hitbox), "Top edge collision should be detected"

    def test_left_edge_collision_detected(self):
        """测试左侧边缘碰撞检测"""
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)

        bullet_rect = pygame.Rect(enemy.rect.x - 5, enemy.rect.centery - 8, 8, 16)
        enemy_hitbox = enemy.get_hitbox()

        assert bullet_rect.colliderect(enemy_hitbox), "Left edge collision should be detected"

    def test_right_edge_collision_detected(self):
        """测试右侧边缘碰撞检测"""
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)

        bullet_rect = pygame.Rect(enemy.rect.right - 3, enemy.rect.centery - 8, 8, 16)
        enemy_hitbox = enemy.get_hitbox()

        assert bullet_rect.colliderect(enemy_hitbox), "Right edge collision should be detected"

    def test_bottom_edge_collision_detected(self):
        """测试底部边缘碰撞检测"""
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)

        bullet_rect = pygame.Rect(enemy.rect.centerx - 4, enemy.rect.bottom - 3, 8, 16)
        enemy_hitbox = enemy.get_hitbox()

        assert bullet_rect.colliderect(enemy_hitbox), "Bottom edge collision should be detected"

    def test_corner_collision_detected(self):
        """测试角落碰撞检测"""
        data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
        enemy = Enemy(400, 300, data)

        bullet_rect = pygame.Rect(enemy.rect.x - 3, enemy.rect.y - 3, 8, 16)
        enemy_hitbox = enemy.get_hitbox()

        assert bullet_rect.colliderect(enemy_hitbox), "Corner collision should be detected"

    def test_multiple_positions_collision(self):
        """测试多个位置的碰撞检测"""
        positions = [(100, 100), (600, 200), (300, 500), (700, 400)]

        for x, y in positions:
            data = EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight")
            enemy = Enemy(x, y, data)

            bullet_rect = pygame.Rect(enemy.rect.centerx - 4, enemy.rect.centery - 8, 8, 16)
            enemy_hitbox = enemy.get_hitbox()

            assert bullet_rect.colliderect(enemy_hitbox), f"Collision should be detected at position ({x}, {y})"


class TestMotherShipRippleClearIntegration:
    """测试母舰涟漪特效清除集成"""

    def test_ripple_effects_initial_empty(self):
        """验证涟漪特效列表初始为空"""
        scene = GameScene()
        scene.enter(difficulty='easy', username='TestPlayer')

        assert len(scene.game_controller.state.ripple_effects) == 0

    def test_ripple_effect_created_on_hit(self):
        """验证命中时创建涟漪特效"""
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
        """验证对接开始时清除涟漪特效"""
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
        """验证对接完成时清除涟漪特效"""
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
        """验证脱离对接时清除涟漪特效"""
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
        """验证返回空闲状态时清除涟漪特效"""
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
        """验证多个涟漪特效同时清除"""
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
    """测试游戏场景碰撞检测集成"""

    def test_bullet_enemy_collision_uses_expanded_hitbox(self):
        """验证子弹与敌机碰撞使用扩展碰撞体"""
        scene = GameScene()
        scene.enter(difficulty='easy', username='TestPlayer')

        enemy = Enemy(400, 300, EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight"))
        scene.spawn_controller.enemies.append(enemy)

        initial_health = enemy.health

        bullet = scene.player.fire()
        bullet.rect.x = enemy.rect.centerx - 4
        bullet.rect.y = enemy.rect.centery - 8

        scene._check_player_bullets_vs_enemies()

        assert enemy.health < initial_health, f"Enemy should take damage from expanded hitbox collision. Initial: {initial_health}, Current: {enemy.health}"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
