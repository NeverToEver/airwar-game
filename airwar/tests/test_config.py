import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConfigSettings:
    @pytest.mark.smoke
    def test_difficulty_settings_exist(self):
        from airwar.config import DIFFICULTY_SETTINGS
        assert 'easy' in DIFFICULTY_SETTINGS
        assert 'medium' in DIFFICULTY_SETTINGS
        assert 'hard' in DIFFICULTY_SETTINGS

    @pytest.mark.smoke
    @pytest.mark.parametrize('difficulty,expected', [
        ('easy', {'enemy_health': 300, 'bullet_damage': 100, 'enemy_speed': 2.5, 'spawn_rate': 40}),
        ('medium', {'enemy_health': 200, 'bullet_damage': 50, 'enemy_speed': 3.0, 'spawn_rate': 30}),
        ('hard', {'enemy_health': 170, 'bullet_damage': 34, 'enemy_speed': 3.5, 'spawn_rate': 25}),
    ])
    def test_difficulty_values(self, difficulty, expected):
        from airwar.config import DIFFICULTY_SETTINGS
        settings = DIFFICULTY_SETTINGS[difficulty]
        for key, value in expected.items():
            assert settings[key] == value, f'{difficulty}.{key}'

    @pytest.mark.smoke
    @pytest.mark.parametrize('difficulty', ['easy', 'medium', 'hard'])
    def test_shots_to_kill_calculation(self, difficulty):
        from airwar.config import DIFFICULTY_SETTINGS
        settings = DIFFICULTY_SETTINGS[difficulty]
        shots = settings['enemy_health'] / settings['bullet_damage']
        assert shots == int(shots), f'{difficulty}: {shots} should be integer'

    @pytest.mark.smoke
    def test_screen_dimensions(self):
        from airwar.config import SCREEN_WIDTH, SCREEN_HEIGHT
        assert SCREEN_WIDTH == 1400
        assert SCREEN_HEIGHT == 800

    @pytest.mark.smoke
    def test_speeds_positive(self):
        from airwar.config import PLAYER_SPEED, BULLET_SPEED, FPS, PLAYER_FIRE_RATE
        assert PLAYER_SPEED > 0
        assert BULLET_SPEED > 0
        assert FPS > 0
        assert PLAYER_FIRE_RATE > 0

    @pytest.mark.smoke
    def test_all_difficulty_settings_have_required_keys(self):
        from airwar.config import DIFFICULTY_SETTINGS
        required_keys = {'enemy_health', 'bullet_damage', 'enemy_speed', 'spawn_rate'}
        for diff, settings in DIFFICULTY_SETTINGS.items():
            assert required_keys.issubset(settings.keys()), f'{diff} missing keys'

    @pytest.mark.smoke
    def test_difficulty_order_logical(self):
        from airwar.config import DIFFICULTY_SETTINGS
        assert DIFFICULTY_SETTINGS['easy']['spawn_rate'] > DIFFICULTY_SETTINGS['medium']['spawn_rate']
        assert DIFFICULTY_SETTINGS['medium']['spawn_rate'] > DIFFICULTY_SETTINGS['hard']['spawn_rate']
        assert DIFFICULTY_SETTINGS['easy']['enemy_speed'] < DIFFICULTY_SETTINGS['medium']['enemy_speed']
        assert DIFFICULTY_SETTINGS['medium']['enemy_speed'] < DIFFICULTY_SETTINGS['hard']['enemy_speed']

    def test_health_regeneration_config(self):
        from airwar.config import HEALTH_REGEN
        assert 'easy' in HEALTH_REGEN
        assert 'medium' in HEALTH_REGEN
        assert 'hard' in HEALTH_REGEN
        for diff, config in HEALTH_REGEN.items():
            assert 'delay' in config
            assert 'rate' in config
            assert 'interval' in config
            assert all(v > 0 for v in config.values())
