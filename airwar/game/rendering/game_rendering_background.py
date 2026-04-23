import pygame
import math
import random
from typing import List, Optional, Tuple
from airwar.config.design_tokens import ForestColors


class RainforestBackground:
    """雨林风格游戏背景 - 柔和的绿色渐变配合浮动微粒

    性能优化：
    - 预渲染渐变背景到缓存
    - 使用简单的矩形/圆形代替复杂图形
    - 限制粒子数量
    - 视差滚动层数有限
    """

    _gradient_cache = {}
    _leaf_cache = {}

    def __init__(self, screen_width: int = 800, screen_height: int = 600):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.time = 0.0

        self._cached_gradient = None
        self._init_layers(screen_width, screen_height)
        self._generate_gradient()
        self._generate_leaf_shapes()

    def _init_layers(self, screen_width: int, screen_height: int) -> None:
        """初始化雨林层"""
        # 远景层 - 大型模糊叶影，移动缓慢
        self._layer_far = RainforestLayer(
            screen_width, screen_height,
            count=8, speed=0.2, size_range=(80, 150),
            color=(15, 35, 15, 40),  # 深绿半透明
            shape='large_leaf'
        )

        # 中景层 - 中型叶影
        self._layer_mid = RainforestLayer(
            screen_width, screen_height,
            count=12, speed=0.5, size_range=(40, 80),
            color=(20, 50, 20, 60),
            shape='medium_leaf'
        )

        # 光斑层 - 模拟树隙光
        self._light_layer = LightRayLayer(
            screen_width, screen_height,
            count=3, speed=0.1
        )

    def _generate_gradient(self) -> None:
        """生成雨林渐变背景 - 从顶部深绿到底部更亮的绿"""
        cache_key = (self.screen_width, self.screen_height)
        if cache_key not in RainforestBackground._gradient_cache:
            gradient = pygame.Surface((self.screen_width, self.screen_height))
            for y in range(self.screen_height):
                ratio = y / self.screen_height
                # 从顶部深绿(8,15,8)渐变到底部较亮的绿(15,35,15)
                r = int(8 + ratio * 12)
                g = int(15 + ratio * 30)
                b = int(8 + ratio * 12)
                pygame.draw.line(gradient, (r, g, b), (0, y), (self.screen_width, y))
            RainforestBackground._gradient_cache[cache_key] = gradient
        self._cached_gradient = RainforestBackground._gradient_cache[cache_key]

    def _generate_leaf_shapes(self) -> None:
        """预生成叶子形状到缓存"""
        for size in [100, 150, 200]:
            if size not in RainforestBackground._leaf_cache:
                leaf_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                # 简单的椭圆叶子形状
                center = size
                # 叶身
                for i in range(size // 2, 0, -2):
                    alpha = int(60 * (1 - i / (size // 2)))
                    pygame.draw.ellipse(
                        leaf_surf,
                        (20, 50, 20, alpha),
                        (center - i, center - i * 2, i * 2, i * 4)
                    )
                RainforestBackground._leaf_cache[size] = leaf_surf

    @classmethod
    def clear_all_caches(cls) -> None:
        cls._gradient_cache.clear()
        cls._leaf_cache.clear()

    def update(self, delta_time: float = 1.0) -> None:
        self.time += delta_time
        self._layer_far.update(delta_time)
        self._layer_mid.update(delta_time)
        self._light_layer.update(delta_time)

    def draw(self, surface: pygame.Surface) -> None:
        # 绘制渐变背景
        if self._cached_gradient:
            surface.blit(self._cached_gradient, (0, 0))

        # 绘制光斑层（最底层）
        self._light_layer.render(surface)

        # 绘制远景叶影层
        self._layer_far.render(surface)

        # 绘制中景叶影层
        self._layer_mid.render(surface)

    def resize(self, screen_width: int, screen_height: int) -> None:
        self.screen_width = screen_width
        self.screen_height = screen_height
        self._init_layers(screen_width, screen_height)
        self._generate_gradient()


class RainforestLayer:
    """雨林叶影层"""

    _leaf_surface_cache = {}

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        count: int,
        speed: float,
        size_range: Tuple[float, float],
        color: Tuple[int, int, int, int],
        shape: str = 'large_leaf'
    ):
        self._leaves: List[dict] = []
        self._scroll_offset = 0.0
        self._speed = speed
        self._screen_height = screen_height
        self._count = count
        self._size_range = size_range
        self._color = color
        self._shape = shape
        self._screen_width = screen_width
        self._init_leaves(screen_width, screen_height, count)

    def _get_leaf_surface(self, size: float) -> pygame.Surface:
        size_key = int(size * 10)
        if size_key not in RainforestLayer._leaf_surface_cache:
            surf = pygame.Surface((int(size * 2), int(size * 3)), pygame.SRCALPHA)
            pygame.draw.ellipse(
                surf,
                (*self._color[:3], self._color[3]),
                (0, 0, int(size * 2), int(size * 3))
            )
            pygame.draw.line(
                surf,
                (*self._color[:3], self._color[3] + 20),
                (size, size * 0.2),
                (size, size * 2.8),
                1
            )
            RainforestLayer._leaf_surface_cache[size_key] = surf
        return RainforestLayer._leaf_surface_cache[size_key]

    def _init_leaves(self, screen_width: int, screen_height: int, count: int) -> None:
        self._leaves = []
        for _ in range(count):
            self._leaves.append({
                'x': random.randint(0, screen_width),
                'base_y': random.randint(0, screen_height),
                'size': random.uniform(self._size_range[0], self._size_range[1]),
                'speed_factor': random.uniform(0.8, 1.2),
                'sway_phase': random.uniform(0, math.tau),
                'sway_amount': random.uniform(5, 15),
                'alpha': random.randint(self._color[3] - 20, self._color[3])
            })

    def update(self, delta_time: float = 1.0) -> None:
        self._scroll_offset += self._speed * delta_time

    def render(self, surface: pygame.Surface) -> None:
        time = RainforestBackground.time
        for leaf in self._leaves:
            y = (leaf['base_y'] + self._scroll_offset * leaf['speed_factor']) % (self._screen_height + leaf['size'] * 2)
            y = y - leaf['size']

            sway = math.sin(time + leaf['sway_phase']) * leaf['sway_amount']

            leaf_surf = self._get_leaf_surface(leaf['size'])
            leaf_surf.set_alpha(leaf['alpha'])

            x = leaf['x'] + sway
            surface.blit(leaf_surf, (int(x - leaf['size']), int(y - leaf['size'])))

    time = 0.0  # 类变量，用于同步摇摆


class LightRayLayer:
    """光束层 - 模拟树隙透射的光线"""

    _ray_surface_cache = {}

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        count: int,
        speed: float
    ):
        self._rays: List[dict] = []
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._speed = speed
        self._time = 0.0
        self._init_rays(screen_width, count)

    def _get_ray_surface(self, width: float, screen_height: int) -> pygame.Surface:
        cache_key = (int(width * 10), screen_height)
        if cache_key not in LightRayLayer._ray_surface_cache:
            surf = pygame.Surface((int(width * 2), screen_height), pygame.SRCALPHA)
            points = [
                (width * 0.3, 0),
                (width * 1.7, 0),
                (width * 2, screen_height),
                (0, screen_height)
            ]
            pygame.draw.polygon(surf, (180, 200, 100, 255), points)
            LightRayLayer._ray_surface_cache[cache_key] = surf
        return LightRayLayer._ray_surface_cache[cache_key]

    def _init_rays(self, screen_width: int, count: int) -> None:
        self._rays = []
        for _ in range(count):
            self._rays.append({
                'x': random.randint(0, screen_width),
                'width': random.uniform(30, 80),
                'alpha': random.randint(8, 15),
                'speed_factor': random.uniform(0.5, 1.0),
                'phase': random.uniform(0, math.tau),
                'pulse_speed': random.uniform(0.01, 0.03)
            })

    def update(self, delta_time: float = 1.0) -> None:
        self._time += delta_time
        for ray in self._rays:
            ray['x'] += ray['speed_factor'] * delta_time * 0.1
            if ray['x'] > self._screen_width + ray['width']:
                ray['x'] = -ray['width']

    def render(self, surface: pygame.Surface) -> None:
        for ray in self._rays:
            pulse = math.sin(self._time * ray['pulse_speed'] + ray['phase'])
            alpha = int(ray['alpha'] * (0.7 + 0.3 * pulse))

            ray_surf = self._get_ray_surface(ray['width'], self._screen_height)
            ray_surf.set_alpha(alpha)
            surface.blit(ray_surf, (int(ray['x'] - ray['width']), 0))


RainforestBackground.time = 0.0
