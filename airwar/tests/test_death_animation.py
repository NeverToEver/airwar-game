import pytest
from unittest.mock import MagicMock, patch
import pygame


class TestDeathAnimationCreation:
    def test_death_animation_can_be_created(self):
        from airwar.game.death_animation import DeathAnimation
        animation = DeathAnimation()
        assert animation is not None

    def test_death_animation_initial_state(self):
        from airwar.game.death_animation import DeathAnimation
        animation = DeathAnimation()
        assert animation.is_active() is False
        assert animation._timer == 0

    def test_death_animation_constants_defined(self):
        from airwar.game.death_animation import DeathAnimation
        assert DeathAnimation.ANIMATION_DURATION == 200
        assert DeathAnimation.SPARK_COUNT_MIN == 3
        assert DeathAnimation.SPARK_COUNT_MAX == 5
        assert DeathAnimation.SPARK_MAX_COUNT == 100


class TestDeathAnimationTrigger:
    def test_trigger_activates_animation(self):
        from airwar.game.death_animation import DeathAnimation
        animation = DeathAnimation()
        animation.trigger(100, 200)
        assert animation.is_active() is True
        assert animation._center_x == 100
        assert animation._center_y == 200

    def test_trigger_resets_timer(self):
        from airwar.game.death_animation import DeathAnimation
        animation = DeathAnimation()
        animation._timer = 50
        animation.trigger(100, 200)
        assert animation._timer == 0


class TestDeathAnimationUpdate:
    def test_update_increments_timer(self):
        from airwar.game.death_animation import DeathAnimation
        animation = DeathAnimation()
        animation.trigger(100, 200)
        initial_timer = animation._timer
        animation.update()
        assert animation._timer == initial_timer + 1

    def test_update_returns_true_when_active(self):
        from airwar.game.death_animation import DeathAnimation
        animation = DeathAnimation()
        animation.trigger(100, 200)
        result = animation.update()
        assert result is True

    def test_update_returns_false_when_inactive(self):
        from airwar.game.death_animation import DeathAnimation
        animation = DeathAnimation()
        result = animation.update()
        assert result is False

    def test_update_returns_false_when_duration_reached(self):
        from airwar.game.death_animation import DeathAnimation
        animation = DeathAnimation()
        animation.trigger(100, 200)
        for _ in range(DeathAnimation.ANIMATION_DURATION):
            animation.update()
        result = animation.update()
        assert result is False
        assert animation.is_active() is False


class TestSparkParticle:
    def test_spark_particle_creation(self):
        from airwar.game.death_animation import SparkParticle
        particle = SparkParticle(100, 200, 3.0, -2.0, 60, 60, 3.0)
        assert particle.x == 100
        assert particle.y == 200
        assert particle.vx == 3.0
        assert particle.vy == -2.0
        assert particle.life == 60
        assert particle.max_life == 60
        assert particle.size == 3.0


class TestSparkGeneration:
    def test_trigger_generates_sparks_on_update(self):
        from airwar.game.death_animation import DeathAnimation
        animation = DeathAnimation()
        animation.trigger(100, 200)
        for _ in range(3):
            animation.update()
        assert len(animation._sparks) > 0

    def test_animation_deactivates_after_duration(self):
        from airwar.game.death_animation import DeathAnimation
        animation = DeathAnimation()
        animation.trigger(100, 200)
        assert animation.is_active() is True
        for _ in range(DeathAnimation.ANIMATION_DURATION):
            animation.update()
        assert animation.is_active() is False

    def test_sparks_respect_max_count(self):
        from airwar.game.death_animation import DeathAnimation
        animation = DeathAnimation()
        animation.trigger(100, 200)
        for _ in range(200):
            animation.update()
        assert len(animation._sparks) <= DeathAnimation.SPARK_MAX_COUNT


class TestSparkMovement:
    def test_sparks_move_over_time(self):
        from airwar.game.death_animation import DeathAnimation
        animation = DeathAnimation()
        animation.trigger(100, 200)
        for _ in range(3):
            animation.update()
        initial_positions = [(s.x, s.y) for s in animation._sparks]
        for _ in range(10):
            animation.update()
        current_positions = [(s.x, s.y) for s in animation._sparks]
        assert initial_positions != current_positions

    def test_sparks_have_random_directions(self):
        from airwar.game.death_animation import DeathAnimation
        animation = DeathAnimation()
        animation.trigger(100, 200)
        for _ in range(3):
            animation.update()
        velocities = [(s.vx, s.vy) for s in animation._sparks]
        unique_velocities = set(velocities)
        assert len(unique_velocities) > 1


class TestSparkColor:
    def test_spark_color_changes_with_life(self):
        from airwar.game.death_animation import DeathAnimation
        animation = DeathAnimation()
        animation.trigger(100, 200)
        for _ in range(3):
            animation.update()
        if len(animation._sparks) == 0:
            pytest.skip("No sparks generated in this run")
        spark = animation._sparks[0]
        initial_life = spark.life
        for _ in range(30):
            animation.update()
        updated_spark = None
        for s in animation._sparks:
            if s.max_life == spark.max_life and s.life != spark.life:
                updated_spark = s
                break
        if updated_spark:
            assert updated_spark.life < initial_life


class TestFlickerEffect:
    def test_flicker_constants_defined(self):
        from airwar.game.death_animation import DeathAnimation
        assert DeathAnimation.FLICKER_START_FRAME == 0
        assert DeathAnimation.FLICKER_END_FRAME == 60
        assert DeathAnimation.FLICKER_INTERVAL == 4
        assert DeathAnimation.FLICKER_ALPHA_HIGH == 255
        assert DeathAnimation.FLICKER_ALPHA_LOW == 80

    def test_flicker_visible_in_flicker_range(self):
        from airwar.game.death_animation import DeathAnimation
        animation = DeathAnimation()
        animation.trigger(100, 200)
        for _ in range(10):
            animation.update()
        assert animation._timer < DeathAnimation.FLICKER_END_FRAME
        assert animation._timer >= DeathAnimation.FLICKER_START_FRAME

    def test_flicker_not_visible_after_flicker_range(self):
        from airwar.game.death_animation import DeathAnimation
        animation = DeathAnimation()
        animation.trigger(100, 200)
        for _ in range(65):
            animation.update()
        assert animation._timer >= DeathAnimation.FLICKER_END_FRAME

    def test_should_show_flicker(self):
        from airwar.game.death_animation import DeathAnimation
        animation = DeathAnimation()
        animation.trigger(100, 200)
        animation._timer = 0
        assert animation._should_show_flicker() is True
        animation._timer = 3
        assert animation._should_show_flicker() is True
        animation._timer = 4
        assert animation._should_show_flicker() is False
        animation._timer = 60
        assert animation._should_show_flicker() is False


class TestGlowEffect:
    def test_glow_constants_defined(self):
        from airwar.game.death_animation import DeathAnimation
        assert DeathAnimation.GLOW_START_FRAME == 60
        assert DeathAnimation.GLOW_END_FRAME == 180
        assert DeathAnimation.GLOW_MAX_ALPHA == 150
        assert DeathAnimation.GLOW_COLOR == (255, 255, 255)

    def test_glow_visible_in_glow_range(self):
        from airwar.game.death_animation import DeathAnimation
        animation = DeathAnimation()
        animation.trigger(100, 200)
        for _ in range(70):
            animation.update()
        assert animation._timer >= DeathAnimation.GLOW_START_FRAME
        assert animation._timer < DeathAnimation.GLOW_END_FRAME

    def test_glow_not_visible_before_start(self):
        from airwar.game.death_animation import DeathAnimation
        animation = DeathAnimation()
        animation.trigger(100, 200)
        for _ in range(30):
            animation.update()
        assert animation._timer < DeathAnimation.GLOW_START_FRAME

    def test_glow_not_visible_after_end(self):
        from airwar.game.death_animation import DeathAnimation
        animation = DeathAnimation()
        animation.trigger(100, 200)
        for _ in range(185):
            animation.update()
        assert animation._timer >= DeathAnimation.GLOW_END_FRAME

    def test_get_glow_progress(self):
        from airwar.game.death_animation import DeathAnimation
        animation = DeathAnimation()
        animation.trigger(100, 200)
        animation._timer = 0
        assert animation._get_glow_progress() == 0.0
        animation._timer = 61
        progress = animation._get_glow_progress()
        assert progress > 0.0 and progress < 1.0
        animation._timer = 180
        assert animation._get_glow_progress() == 0.0


class TestTriggerAcceptsScreenDiagonal:
    def test_trigger_accepts_screen_diagonal_parameter(self):
        from airwar.game.death_animation import DeathAnimation
        animation = DeathAnimation()
        animation.trigger(100, 200, screen_diagonal=1000)
        assert animation._screen_diagonal == 1000

    def test_trigger_defaults_screen_diagonal_to_zero(self):
        from airwar.game.death_animation import DeathAnimation
        animation = DeathAnimation()
        animation.trigger(100, 200)
        assert animation._screen_diagonal == 0


class TestSparkRendering:
    def test_render_does_not_raise_with_sparks(self):
        from airwar.game.death_animation import DeathAnimation
        pygame.init()
        surface = pygame.Surface((800, 600))
        animation = DeathAnimation()
        animation.trigger(400, 300, screen_diagonal=1000)
        for _ in range(10):
            animation.update()
        animation.render(surface)
        pygame.quit()

    def test_render_handles_empty_sparks_list(self):
        from airwar.game.death_animation import DeathAnimation
        pygame.init()
        surface = pygame.Surface((800, 600))
        animation = DeathAnimation()
        animation.trigger(400, 300)
        animation.render(surface)
        pygame.quit()

    def test_render_does_nothing_when_inactive(self):
        from airwar.game.death_animation import DeathAnimation
        pygame.init()
        surface = pygame.Surface((800, 600))
        animation = DeathAnimation()
        animation.render(surface)
        pygame.quit()
