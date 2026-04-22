import pytest
from airwar.game.managers.collision_controller import (
    CollisionController,
    CollisionEvent,
    CollisionResult
)


class TestCollisionEvent:
    def test_collision_event_creation(self):
        event = CollisionEvent(type='player_hit')
        assert event.type == 'player_hit'
        assert event.source is None
        assert event.target is None
        assert event.damage == 0
        assert event.score == 0
    
    def test_collision_event_with_all_fields(self):
        event = CollisionEvent(
            type='enemy_killed',
            source='bullet_1',
            target='enemy_1',
            damage=10,
            score=100
        )
        assert event.type == 'enemy_killed'
        assert event.source == 'bullet_1'
        assert event.target == 'enemy_1'
        assert event.damage == 10
        assert event.score == 100


class TestCollisionResult:
    def test_collision_result_defaults(self):
        result = CollisionResult()
        assert result.player_damaged is False
        assert result.enemies_killed == 0
        assert result.score_gained == 0
        assert result.boss_damaged is False
        assert result.boss_killed is False


class TestCollisionController:
    def test_collision_controller_initialization(self):
        controller = CollisionController()
        assert controller.events == []
        assert isinstance(controller.events, list)
    
    def test_clear_events(self):
        controller = CollisionController()
        controller._events.append(CollisionEvent(type='test'))
        assert len(controller.events) == 1
        
        controller.clear_events()
        assert len(controller.events) == 0
    
    def test_events_property_returns_copy(self):
        controller = CollisionController()
        controller._events.append(CollisionEvent(type='test'))
        
        events1 = controller.events
        events1.append(CollisionEvent(type='another'))
        
        assert len(controller.events) == 1
        assert len(events1) == 2
    
    def test_check_all_collisions_with_no_boss(self):
        controller = CollisionController()
        
        mock_player = type('MockPlayer', (), {
            'get_bullets': lambda self: [],
            'get_hitbox': lambda self: type('MockRect', (), {'colliderect': lambda x, y: False})()
        })()
        
        mock_reward_system = type('MockRewardSystem', (), {
            'explosive_level': 0,
            'calculate_damage_taken': lambda self, d: d,
            'piercing_level': 0
        })()
        
        controller.check_all_collisions(
            player=mock_player,
            enemies=[],
            boss=None,
            enemy_bullets=[],
            reward_system=mock_reward_system,
            player_invincible=False,
            score_multiplier=1,
            on_enemy_killed=None,
            on_boss_killed=None,
            on_boss_hit=None,
            on_player_hit=None,
            on_lifesteal=None,
        )
        
        assert isinstance(controller.events, list)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
