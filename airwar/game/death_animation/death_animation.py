"""Death animation — player destruction visual effect sequence."""
import math
import random
from typing import List

import pygame
from airwar.config.design_tokens import Colors


class SparkParticle:
    """Spark particle used in the death explosion animation."""

    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        life: int,
        max_life: int,
        size: float
    ) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = max_life
        self.size = size


class DeathAnimation:
    """Player death animation component.

    Manages three visual effects on death:
    1. Flicker (0-60 frames): red-white alternating flash at the ship position
    2. Spark (0-180 frames): particles bursting from the ship position
    3. Glow (60-180 frames): white glow expanding from center to full screen
    """

    ANIMATION_DURATION = 200
    FLICKER_START_FRAME = 0
    FLICKER_END_FRAME = 42
    FLICKER_INTERVAL = 18
    FLICKER_ALPHA_HIGH = 96
    FLICKER_ALPHA_LOW = 48
    SPARK_START_FRAME = 0
    SPARK_END_FRAME = 180
    SPARK_GENERATION_INTERVAL = 3
    SPARK_COUNT_MIN = 3
    SPARK_COUNT_MAX = 5
    SPARK_LIFE_MIN = 60
    SPARK_LIFE_MAX = 90
    SPARK_SPEED_MIN = 2.0
    SPARK_SPEED_MAX = 5.0
    SPARK_SIZE_MIN = 2.0
    SPARK_SIZE_MAX = 4.0
    SPARK_GRAVITY = 0.05
    SPARK_MAX_COUNT = 100
    GLOW_START_FRAME = 60
    GLOW_END_FRAME = 180
    GLOW_MAX_ALPHA = 42
    GLOW_COLOR = (255, 126, 82)
    FLICKER_COLOR = Colors.ACCENT_DANGER

    MAX_SPARK_ALPHA = 150
    SPARK_GLOW_ALPHA_RATIO = 0.18

    # Cache for flicker surfaces
    _flicker_cache = {}
    _spark_glow_cache = {}

    def __init__(self) -> None:
        self._active = False
        self._timer = 0
        self._center_x = 0
        self._center_y = 0
        self._sparks: List[SparkParticle] = []
        self._screen_diagonal = 0
        self._frame_since_last_spark = 0

    def trigger(self, x: int, y: int, screen_diagonal: int = 0) -> None:
        """Trigger the death animation.

        Args:
            x: Death position X coordinate.
            y: Death position Y coordinate.
            screen_diagonal: Screen diagonal length for glow effect rendering.
        """
        self._active = True
        self._timer = 0
        self._center_x = x
        self._center_y = y
        self._sparks = []
        self._frame_since_last_spark = 0
        self._screen_diagonal = screen_diagonal

    def update(self) -> bool:
        """Update animation state.

        Returns:
            True if the animation is still running, False if it has ended.
        """
        if not self._active:
            return False

        self._timer += 1
        self._frame_since_last_spark += 1

        if self._timer <= self.SPARK_END_FRAME:
            if self._frame_since_last_spark >= self.SPARK_GENERATION_INTERVAL:
                self._generate_sparks()
                self._frame_since_last_spark = 0

        self._update_sparks()

        if self._timer >= self.ANIMATION_DURATION:
            self._active = False
            return False

        return True

    def render(self, surface) -> None:
        """Render death animation effects.

        Args:
            surface: Pygame rendering surface.
        """
        if not self._active:
            return

        self._render_flicker(surface)
        self._render_glow(surface)
        self._render_sparks(surface)

    def _render_flicker(self, surface) -> None:
        """Render a low-intensity damage flare at the wreck center."""
        if not self._should_show_flicker():
            return

        flicker_step = (self._timer - self.FLICKER_START_FRAME) // self.FLICKER_INTERVAL
        alpha = self.FLICKER_ALPHA_HIGH if flicker_step == 0 else self.FLICKER_ALPHA_LOW
        color = self.FLICKER_COLOR
        cache_key = (alpha, color)
        if cache_key not in DeathAnimation._flicker_cache:
            flicker_surf = pygame.Surface((60, 60), pygame.SRCALPHA)
            pygame.draw.circle(flicker_surf, (*color, alpha), (30, 30), 25)
            pygame.draw.circle(flicker_surf, (255, 164, 104, alpha // 2), (30, 30), 14)
            DeathAnimation._flicker_cache[cache_key] = flicker_surf
        surface.blit(DeathAnimation._flicker_cache[cache_key], (int(self._center_x - 30), int(self._center_y - 30)))

    def is_active(self) -> bool:
        """Check whether the animation is currently active."""
        return self._active

    def _generate_sparks(self) -> None:
        """Generate new spark particles."""
        if len(self._sparks) >= self.SPARK_MAX_COUNT:
            return

        count = random.randint(self.SPARK_COUNT_MIN, self.SPARK_COUNT_MAX)
        for _ in range(count):
            if len(self._sparks) >= self.SPARK_MAX_COUNT:
                break
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(self.SPARK_SPEED_MIN, self.SPARK_SPEED_MAX)
            life = random.randint(self.SPARK_LIFE_MIN, self.SPARK_LIFE_MAX)
            size = random.uniform(self.SPARK_SIZE_MIN, self.SPARK_SIZE_MAX)
            self._sparks.append(SparkParticle(
                x=self._center_x,
                y=self._center_y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=life,
                max_life=life,
                size=size
            ))

    def _update_sparks(self) -> None:
        """Update position and lifetime of all spark particles."""
        for spark in self._sparks:
            spark.x += spark.vx
            spark.y += spark.vy
            spark.vy += self.SPARK_GRAVITY
            spark.life -= 1
        self._sparks = [s for s in self._sparks if s.life > 0]

    def _render_sparks(self, surface) -> None:
        """Render spark particle effects."""
        for spark in self._sparks:
            life_ratio = spark.life / spark.max_life if spark.max_life > 0 else 0.0
            alpha = int(self.MAX_SPARK_ALPHA * life_ratio)

            if alpha < 10:
                continue

            color_base = (255, int(200 * life_ratio), int(50 * life_ratio))

            glow_radius = int(spark.size * 2)
            if glow_radius > 0:
                cache_key = (glow_radius, alpha)
                if cache_key not in DeathAnimation._spark_glow_cache:
                    glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
                    glow_alpha = int(alpha * self.SPARK_GLOW_ALPHA_RATIO)
                    pygame.draw.circle(
                        glow_surf,
                        (*color_base, glow_alpha),
                        (glow_radius, glow_radius),
                        glow_radius
                    )
                    DeathAnimation._spark_glow_cache[cache_key] = glow_surf
                surface.blit(DeathAnimation._spark_glow_cache[cache_key], (int(spark.x) - glow_radius, int(spark.y) - glow_radius))

            pygame.draw.circle(
                surface,
                color_base,
                (int(spark.x), int(spark.y)),
                max(1, int(spark.size * life_ratio))
            )

    def _should_show_flicker(self) -> bool:
        """Check whether the current frame should show a flicker."""
        return self.FLICKER_START_FRAME <= self._timer < self.FLICKER_END_FRAME

    def _should_show_glow(self) -> bool:
        """Check whether the current frame should show the glow effect."""
        return self._timer >= self.GLOW_START_FRAME and self._timer < self.GLOW_END_FRAME

    def _get_glow_progress(self) -> float:
        """Get glow expansion progress (0.0 - 1.0)."""
        if self._timer < self.GLOW_START_FRAME or self._timer >= self.GLOW_END_FRAME:
            return 0.0
        return (self._timer - self.GLOW_START_FRAME) / (self.GLOW_END_FRAME - self.GLOW_START_FRAME)

    def _render_glow(self, surface) -> None:
        """Render the expanding glow effect."""
        if not self._should_show_glow():
            return

        progress = self._get_glow_progress()
        max_radius = self._screen_diagonal
        radius = int(max_radius * progress)
        alpha = int(self.GLOW_MAX_ALPHA * (1 - progress))

        if radius <= 0:
            return

        glow_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*self.GLOW_COLOR, alpha), (radius, radius), radius)
        surface.blit(glow_surf, (self._center_x - radius, self._center_y - radius))
