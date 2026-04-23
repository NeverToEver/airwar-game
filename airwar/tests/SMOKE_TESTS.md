# Smoke Tests Documentation

## Overview

This document lists all smoke tests in the test suite. Smoke tests verify core functionality and should run quickly to provide fast feedback.

## Running Smoke Tests

```bash
# Run only smoke tests
pytest -m smoke

# Run smoke tests with verbose output
pytest -m smoke -v

# Run all tests except smoke tests
pytest -m "not smoke"

# Run all tests (default)
pytest
```

## Smoke Test Coverage

### Configuration Tests (`test_config.py`)

| Test Class | Test Method | Description |
|------------|-------------|-------------|
| `TestConfigSettings` | `test_difficulty_settings_exist` | Verifies difficulty configurations are loaded |
| `TestConfigSettings` | `test_difficulty_values` | Validates difficulty parameter values |
| `TestConfigSettings` | `test_shots_to_kill_calculation` | Ensures shots-to-kill calculations are integer |
| `TestConfigSettings` | `test_screen_dimensions` | Verifies screen dimensions are set |
| `TestConfigSettings` | `test_speeds_positive` | Ensures all speed values are positive |
| `TestConfigSettings` | `test_all_difficulty_settings_have_required_keys` | Validates config structure |
| `TestConfigSettings` | `test_difficulty_order_logical` | Verifies difficulty progression logic |

### Constants Tests (`test_constants.py`)

| Test Class | Test Method | Description |
|------------|-------------|-------------|
| `TestPlayerConstants` | `test_player_constants_values` | Validates player-related constants |
| `TestDamageConstants` | `test_damage_constants_values` | Validates damage-related constants |
| `TestTimingConstants` | `test_timing_constants_values` | Validates timing constants |
| `TestGameBalanceConstants` | `test_game_balance_constants_values` | Validates game balance constants |
| `TestGameConstants` | `test_get_difficulty_multiplier_easy` | Tests difficulty multiplier lookup |
| `TestGameConstants` | `test_get_difficulty_multiplier_medium` | Tests difficulty multiplier lookup |
| `TestGameConstants` | `test_get_difficulty_multiplier_hard` | Tests difficulty multiplier lookup |
| `TestGameConstantsInstance` | `test_game_constants_has_player_constants` | Verifies constants container structure |
| `TestGameConstantsInstance` | `test_game_constants_singleton` | Ensures singleton pattern |

### Entity Tests (`test_entities.py`)

| Test Class | Test Method | Description |
|------------|-------------|-------------|
| `TestPlayerEntity` | `test_player_creation` | Verifies player can be created |
| `TestPlayerEntity` | `test_player_health_cannot_exceed_max` | Validates health cap logic |
| `TestPlayerEntity` | `test_player_health_cannot_go_negative` | Validates health floor logic |
| `TestEnemyEntity` | `test_enemy_creation` | Verifies enemy can be created |
| `TestEnemyEntity` | `test_enemy_take_damage` | Tests enemy damage handling |
| `TestEnemyEntity` | `test_enemy_off_screen` | Verifies off-screen deactivation |
| `TestBulletEntity` | `test_bullet_creation` | Verifies bullet can be created |
| `TestBulletEntity` | `test_bullet_moves_up` | Validates bullet movement |
| `TestBossEntity` | `test_boss_creation` | Verifies boss can be created |
| `TestBossEntity` | `test_boss_take_damage` | Tests boss damage handling |
| `TestBossEntity` | `test_boss_enter_and_exit` | Validates boss entrance logic |
| `TestBossEntity` | `test_boss_escape_mechanism` | Tests boss escape feature |
| `TestPlayerHitbox` | `test_player_hitbox_smaller_than_sprite` | Verifies hitbox sizing |
| `TestEnemySpawner` | `test_spawner_creation` | Verifies spawner can be created |

### Buff System Tests (`test_buffs.py`)

| Test Class | Test Method | Description |
|------------|-------------|-------------|
| `TestBuffRegistry` | `test_buff_registry_exists` | Verifies buff registry is loaded |
| `TestBuffRegistry` | `test_buff_registry_has_all_buffs` | Validates all buffs are registered |
| `TestBuffRegistry` | `test_create_buff_invalid_raises_error` | Tests error handling |
| `TestBuffApplication` | `test_extra_life_buff_apply` | Tests Extra Life buff application |
| `TestBuffApplication` | `test_power_shot_buff_apply` | Tests Power Shot buff application |
| `TestBuffApplication` | `test_shield_buff_apply` | Tests Shield buff application |

### Scene Tests (`test_scenes.py`)

| Test Class | Test Method | Description |
|------------|-------------|-------------|
| `TestSceneManager` | `test_scene_manager_creation` | Verifies scene manager creation |
| `TestSceneManager` | `test_scene_manager_register` | Tests scene registration |
| `TestSceneManager` | `test_scene_manager_switch` | Tests scene switching |
| `TestSceneInterface` | `test_scene_has_required_methods` | Validates scene interface |

### Window Tests (`test_window.py`)

| Test Class | Test Method | Description |
|------------|-------------|-------------|
| `TestWindowFullscreen` | `test_window_initial_state_not_fullscreen` | Verifies initial fullscreen state |
| `TestWindowFullscreen` | `test_window_is_fullscreen_returns_false_initially` | Tests fullscreen state query |

## Adding New Smoke Tests

To mark a test as a smoke test, add the `@pytest.mark.smoke` decorator:

```python
class TestNewFeature:
    @pytest.mark.smoke
    def test_basic_functionality(self):
        # This will be included in smoke test runs
        pass
```

## Guidelines

1. **Smoke tests should be fast** - Avoid tests that initialize pygame display or take > 1s
2. **Smoke tests should be independent** - No dependencies between tests
3. **Smoke tests should be deterministic** - Same result every run
4. **Cover critical paths** - Focus on core game mechanics and configurations

## Excluded Tests

The following tests are intentionally excluded from smoke tests:

- Integration tests (require full game scene setup)
- Performance tests (intentionally slow)
- Tutorial tests (require pygame display)
- Death/exit scene tests (require pygame display)
- Mother ship integration tests (require event bus)
