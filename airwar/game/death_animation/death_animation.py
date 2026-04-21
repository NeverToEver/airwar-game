import random
import math
from typing import List


class SparkParticle:
    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        life: int,
        max_life: int,
        size: float
    ):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = max_life
        self.size = size


class DeathAnimation:
    ANIMATION_DURATION = 200
    FLICKER_START_FRAME = 0
    FLICKER_END_FRAME = 60
    FLICKER_INTERVAL = 4
    FLICKER_ALPHA_HIGH = 255
    FLICKER_ALPHA_LOW = 80
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
    GLOW_MAX_ALPHA = 150
    GLOW_COLOR = (255, 255, 255)
    FLICKER_COLOR = (255, 50, 50)

    def __init__(self):
        self._active = False
        self._timer = 0
        self._center_x = 0
        self._center_y = 0
        self._sparks: List[SparkParticle] = []
        self._screen_diagonal = 0
        self._frame_since_last_spark = 0

    def trigger(self, x: int, y: int) -> None:
        self._active = True
        self._timer = 0
        self._center_x = x
        self._center_y = y
        self._sparks = []
        self._frame_since_last_spark = 0

    def update(self) -> bool:
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
        if not self._active:
            return

        self._render_sparks(surface)

    def is_active(self) -> bool:
        return self._active

    def _generate_sparks(self) -> None:
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
        for spark in self._sparks:
            spark.x += spark.vx
            spark.y += spark.vy
            spark.vy += self.SPARK_GRAVITY
            spark.life -= 1
        self._sparks = [s for s in self._sparks if s.life > 0]

    def _render_sparks(self, surface) -> None:
        pass

    def _should_show_flicker(self) -> bool:
        if self._timer < self.FLICKER_START_FRAME or self._timer >= self.FLICKER_END_FRAME:
            return False
        flicker_step = (self._timer - self.FLICKER_START_FRAME) // self.FLICKER_INTERVAL
        return flicker_step % 2 == 0

    def _should_show_glow(self) -> bool:
        return self._timer >= self.GLOW_START_FRAME and self._timer < self.GLOW_END_FRAME

    def _get_glow_progress(self) -> float:
        if self._timer < self.GLOW_START_FRAME or self._timer >= self.GLOW_END_FRAME:
            return 0.0
        return (self._timer - self.GLOW_START_FRAME) / (self.GLOW_END_FRAME - self.GLOW_START_FRAME)

    def _render_glow(self, surface) -> None:
        if not self._should_show_glow():
            return

        import pygame
        progress = self._get_glow_progress()
        max_radius = self._screen_diagonal
        radius = int(max_radius * progress)
        alpha = int(self.GLOW_MAX_ALPHA * (1 - progress))

        if radius <= 0:
            return

        glow_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*self.GLOW_COLOR, alpha), (radius, radius), radius)
        surface.blit(glow_surf, (self._center_x - radius, self._center_y - radius))
