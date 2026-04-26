"""Death animation — player destruction visual effect sequence."""
import math
import random
from typing import List

import pygame


class SparkParticle:
    """火花粒子类，用于死亡动画中的爆炸效果"""

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
    """玩家死亡动画组件

    管理死亡时的三种视觉效果：
    1. 闪烁效果 (0-60帧)：战机位置的红白交替闪烁
    2. 火花效果 (0-180帧)：从战机位置随机爆发的粒子
    3. 光晕效果 (60-180帧)：从中心扩散到全屏的白色光晕
    """

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
        """触发死亡动画

        Args:
            x: 死亡位置X坐标
            y: 死亡位置Y坐标
            screen_diagonal: 屏幕对角线长度，用于光晕效果渲染
        """
        self._active = True
        self._timer = 0
        self._center_x = x
        self._center_y = y
        self._sparks = []
        self._frame_since_last_spark = 0
        self._screen_diagonal = screen_diagonal

    def update(self) -> bool:
        """更新动画状态

        Returns:
            True 如果动画仍在进行，False 如果动画已结束
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
        """渲染死亡动画效果

        Args:
            surface: pygame渲染表面
        """
        if not self._active:
            return

        self._render_flicker(surface)
        self._render_glow(surface)
        self._render_sparks(surface)

    def _render_flicker(self, surface) -> None:
        """渲染闪烁效果（战机位置的红白交替闪烁）"""
        if not self._should_show_flicker():
            return

        flicker_step = (self._timer - self.FLICKER_START_FRAME) // self.FLICKER_INTERVAL
        is_visible = flicker_step % 2 == 0

        if is_visible:
            alpha = self.FLICKER_ALPHA_HIGH if flicker_step % 4 == 0 else self.FLICKER_ALPHA_LOW
            color = self.FLICKER_COLOR if flicker_step % 4 == 0 else (255, 255, 255)
            cache_key = (alpha, color)
            if cache_key not in DeathAnimation._flicker_cache:
                flicker_surf = pygame.Surface((60, 60), pygame.SRCALPHA)
                flicker_surf.set_alpha(alpha)
                pygame.draw.circle(flicker_surf, color, (30, 30), 25)
                DeathAnimation._flicker_cache[cache_key] = flicker_surf
            surface.blit(DeathAnimation._flicker_cache[cache_key], (int(self._center_x - 30), int(self._center_y - 30)))

    def is_active(self) -> bool:
        """检查动画是否处于活跃状态"""
        return self._active

    def _generate_sparks(self) -> None:
        """生成新的火花粒子"""
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
        """更新所有火花粒子的位置和生命周期"""
        for spark in self._sparks:
            spark.x += spark.vx
            spark.y += spark.vy
            spark.vy += self.SPARK_GRAVITY
            spark.life -= 1
        self._sparks = [s for s in self._sparks if s.life > 0]

    def _render_sparks(self, surface) -> None:
        """渲染火花粒子效果"""
        for spark in self._sparks:
            life_ratio = spark.life / spark.max_life
            alpha = int(255 * life_ratio)

            if alpha < 10:
                continue

            color_base = (255, int(200 * life_ratio), int(50 * life_ratio))

            glow_radius = int(spark.size * 2)
            if glow_radius > 0:
                cache_key = (glow_radius, alpha)
                if cache_key not in DeathAnimation._spark_glow_cache:
                    glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
                    glow_alpha = int(alpha * 0.3)
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
        """检查当前帧是否应该显示闪烁效果"""
        if self._timer < self.FLICKER_START_FRAME or self._timer >= self.FLICKER_END_FRAME:
            return False
        flicker_step = (self._timer - self.FLICKER_START_FRAME) // self.FLICKER_INTERVAL
        return flicker_step % 2 == 0

    def _should_show_glow(self) -> bool:
        """检查当前帧是否应该显示光晕效果"""
        return self._timer >= self.GLOW_START_FRAME and self._timer < self.GLOW_END_FRAME

    def _get_glow_progress(self) -> float:
        """获取光晕扩散进度 (0.0 - 1.0)"""
        if self._timer < self.GLOW_START_FRAME or self._timer >= self.GLOW_END_FRAME:
            return 0.0
        return (self._timer - self.GLOW_START_FRAME) / (self.GLOW_END_FRAME - self.GLOW_START_FRAME)

    def _render_glow(self, surface) -> None:
        """渲染扩散光晕效果"""
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
