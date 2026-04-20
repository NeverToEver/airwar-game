import pytest
from airwar.game.constants import (
    PlayerConstants,
    DamageConstants,
    AnimationConstants,
    GameBalanceConstants,
    GameConstants,
    GAME_CONSTANTS
)


class TestPlayerConstants:
    def test_player_constants_values(self):
        assert PlayerConstants.INITIAL_X_OFFSET == 25
        assert PlayerConstants.INITIAL_Y == -80
        assert PlayerConstants.FINAL_Y == -100
        assert PlayerConstants.SCREEN_BOTTOM_OFFSET == 100
        assert PlayerConstants.INVINCIBILITY_DURATION == 90
        assert PlayerConstants.MOTHERSHIP_Y_POSITION == 200
        assert PlayerConstants.DEFAULT_SCREEN_WIDTH == 800


class TestDamageConstants:
    def test_damage_constants_values(self):
        assert DamageConstants.BOSS_COLLISION_DAMAGE == 30
        assert DamageConstants.ENEMY_COLLISION_DAMAGE == 20
        assert DamageConstants.DEFAULT_REGEN_RATE == 2
        assert DamageConstants.REGEN_THRESHOLD == 60


class TestAnimationConstants:
    def test_animation_constants_values(self):
        assert AnimationConstants.ENTRANCE_DURATION == 60
        assert AnimationConstants.RIPPLE_INITIAL_RADIUS == 15
        assert AnimationConstants.RIPPLE_INITIAL_ALPHA == 350
        assert AnimationConstants.NOTIFICATION_DECAY_RATE == 1


class TestGameBalanceConstants:
    def test_game_balance_constants_values(self):
        assert GameBalanceConstants.MAX_CYCLES == 10
        assert GameBalanceConstants.BASE_THRESHOLDS == (1000, 2500, 5000, 10000, 20000)
        assert GameBalanceConstants.CYCLE_MULTIPLIER == 1.5
        assert GameBalanceConstants.DIFFICULTY_MULTIPLIERS == (1.0, 1.5, 2.0)


class TestGameConstants:
    def test_get_difficulty_multiplier_easy(self):
        assert GAME_CONSTANTS.get_difficulty_multiplier('easy') == 1.0
    
    def test_get_difficulty_multiplier_medium(self):
        assert GAME_CONSTANTS.get_difficulty_multiplier('medium') == 1.5
    
    def test_get_difficulty_multiplier_hard(self):
        assert GAME_CONSTANTS.get_difficulty_multiplier('hard') == 2.0
    
    def test_get_difficulty_multiplier_invalid(self):
        assert GAME_CONSTANTS.get_difficulty_multiplier('invalid') == 1.0
    
    def test_get_next_threshold_first_milestone_easy(self):
        threshold = GAME_CONSTANTS.get_next_threshold(0, 'easy')
        assert threshold == 1000.0
    
    def test_get_next_threshold_first_milestone_medium(self):
        threshold = GAME_CONSTANTS.get_next_threshold(0, 'medium')
        assert threshold == 1500.0
    
    def test_get_next_threshold_first_milestone_hard(self):
        threshold = GAME_CONSTANTS.get_next_threshold(0, 'hard')
        assert threshold == 2000.0
    
    def test_get_next_threshold_cycle_bonus(self):
        threshold_0 = GAME_CONSTANTS.get_next_threshold(0, 'medium')
        threshold_5 = GAME_CONSTANTS.get_next_threshold(5, 'medium')
        assert threshold_5 > threshold_0


class TestGameConstantsInstance:
    def test_game_constants_has_player_constants(self):
        assert isinstance(GAME_CONSTANTS.PLAYER, PlayerConstants)
    
    def test_game_constants_has_damage_constants(self):
        assert isinstance(GAME_CONSTANTS.DAMAGE, DamageConstants)
    
    def test_game_constants_has_animation_constants(self):
        assert isinstance(GAME_CONSTANTS.ANIMATION, AnimationConstants)
    
    def test_game_constants_has_balance_constants(self):
        assert isinstance(GAME_CONSTANTS.BALANCE, GameBalanceConstants)
    
    def test_game_constants_singleton(self):
        from airwar.game.constants import GAME_CONSTANTS as CONSTANTS2
        assert GAME_CONSTANTS is CONSTANTS2


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
