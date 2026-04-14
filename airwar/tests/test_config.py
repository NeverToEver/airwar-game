import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestConfigSettings:
    def test_difficulty_settings_exist(self):
        from airwar.config import DIFFICULTY_SETTINGS
        assert 'easy' in DIFFICULTY_SETTINGS
        assert 'medium' in DIFFICULTY_SETTINGS
        assert 'hard' in DIFFICULTY_SETTINGS

    def test_easy_difficulty_values(self):
        from airwar.config import DIFFICULTY_SETTINGS
        easy = DIFFICULTY_SETTINGS['easy']
        assert easy['enemy_health'] == 300
        assert easy['bullet_damage'] == 100
        assert easy['enemy_speed'] == 2.5
        assert easy['spawn_rate'] == 40

    def test_medium_difficulty_values(self):
        from airwar.config import DIFFICULTY_SETTINGS
        medium = DIFFICULTY_SETTINGS['medium']
        assert medium['enemy_health'] == 200
        assert medium['bullet_damage'] == 50
        assert medium['enemy_speed'] == 3.0
        assert medium['spawn_rate'] == 30

    def test_hard_difficulty_values(self):
        from airwar.config import DIFFICULTY_SETTINGS
        hard = DIFFICULTY_SETTINGS['hard']
        assert hard['enemy_health'] == 170
        assert hard['bullet_damage'] == 34
        assert hard['enemy_speed'] == 3.5
        assert hard['spawn_rate'] == 25

    def test_shots_to_kill_calculation(self):
        from airwar.config import DIFFICULTY_SETTINGS
        for diff, settings in DIFFICULTY_SETTINGS.items():
            hp = settings['enemy_health']
            dmg = settings['bullet_damage']
            shots = hp / dmg
            assert shots == int(shots), f'{diff}: {shots} should be integer'

    def test_screen_dimensions(self):
        from airwar.config import SCREEN_WIDTH, SCREEN_HEIGHT
        assert SCREEN_WIDTH == 1200
        assert SCREEN_HEIGHT == 700

    def test_player_speed_positive(self):
        from airwar.config import PLAYER_SPEED, BULLET_SPEED
        assert PLAYER_SPEED > 0
        assert BULLET_SPEED > 0

    def test_all_difficulty_settings_have_required_keys(self):
        from airwar.config import DIFFICULTY_SETTINGS
        required_keys = {'enemy_health', 'bullet_damage', 'enemy_speed', 'spawn_rate'}
        for diff, settings in DIFFICULTY_SETTINGS.items():
            assert required_keys.issubset(settings.keys()), f'{diff} missing keys'

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

    def test_fps_positive(self):
        from airwar.config import FPS
        assert FPS > 0

    def test_fire_rate_positive(self):
        from airwar.config import PLAYER_FIRE_RATE
        assert PLAYER_FIRE_RATE > 0
