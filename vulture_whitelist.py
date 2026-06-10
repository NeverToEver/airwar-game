# Vulture whitelist — re-exports and conditional imports that vulture flags as unused.

# __init__.py re-exports (used by external consumers via `from airwar.config import ...`)
airwar.config.get_colors
airwar.config.DIFFICULTY_CONFIGS
airwar.config.TUTORIAL_PAGES
airwar.config.tutorial.TUTORIAL_PAGES

# core_bindings.py conditional imports (Rust fallback pattern)
airwar.core_bindings.batch_hallucinated_enemy_centers
airwar.core_bindings.vec2_add
airwar.core_bindings.vec2_angle
airwar.core_bindings.vec2_clamp_length
airwar.core_bindings.vec2_distance
airwar.core_bindings.vec2_dot
airwar.core_bindings.vec2_from_angle
airwar.core_bindings.vec2_lerp
airwar.core_bindings.vec2_scale
airwar.core_bindings.vec2_sub

# __init__.py re-exports
airwar.game.managers.CollisionResult
airwar.game.systems.MovementPatternGenerator
airwar.input.MockInputHandler
airwar.ui.GameOverScreen
airwar.utils.sprites.create_gradient_surface
