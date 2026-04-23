import pygame
import math
import random
from typing import List, Optional, Tuple


class TwinkleController:
    """闪烁控制器 - 预计算闪烁值，避免每帧计算"""
    
    def __init__(self, star_count: int):
        self._phases = [random.random() * math.tau for _ in range(star_count)]
        self._time = 0.0
        
    def update(self, delta_time: float = 1.0) -> None:
        self._time += delta_time * 0.05
        
    def get_brightness(self, star_index: int) -> float:
        return 0.5 + 0.5 * math.sin(self._time + self._phases[star_index % len(self._phases)])
    
    def get_size_factor(self, star_index: int) -> float:
        return 0.7 + 0.3 * math.sin(self._time * 1.3 + self._phases[star_index % len(self._phases)])


class Star:
    """单个星星 - 支持辉光效果"""
    _glow_cache = {}
    
    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        size_range: Tuple[float, float],
        color_base: Tuple[int, int, int]
    ):
        self.base_x = random.randint(0, screen_width)
        self.base_y = random.randint(0, screen_height)
        self.size = random.uniform(size_range[0], size_range[1])
        self.speed = random.uniform(0.5, 2.0)
        self.brightness = random.randint(100, 255)
        self.twinkle_speed = random.uniform(0.02, 0.08)
        self.twinkle_offset = random.uniform(0, math.tau)
        self.color = color_base
        self._cached_glow = None
        self._glow_cache_key = None
    
    @classmethod
    def clear_cache(cls) -> None:
        cls._glow_cache.clear()
    
    def _get_glow_surface(self) -> pygame.Surface:
        cache_key = int(self.size * 10)
        if cache_key not in Star._glow_cache:
            size_int = max(1, int(self.size))
            glow_size = size_int * 4 + 4
            glow = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
            for i in range(size_int * 2, 0, -1):
                alpha = int(50 * (1 - i / (size_int * 2)))
                pygame.draw.circle(
                    glow, 
                    (150, 180, 255, alpha),
                    (size_int * 2 + 2, size_int * 2 + 2), 
                    i
                )
            Star._glow_cache[cache_key] = glow
        return Star._glow_cache[cache_key]
    
    def draw(self, surface: pygame.Surface, y: float, brightness: float = 1.0) -> None:
        twinkle_val = int(self.brightness * brightness)
        twinkle_val = max(50, min(255, twinkle_val))
        
        if self.size > 1.5:
            glow = self._get_glow_surface()
            size_int = max(1, int(self.size))
            surface.blit(glow, (int(self.base_x - size_int * 2 - 2), int(y - size_int * 2 - 2)))
        
        color = (
            min(255, twinkle_val), 
            min(255, twinkle_val + 30), 
            min(255, twinkle_val + 50)
        )
        pygame.draw.circle(surface, color, (int(self.base_x), int(y)), int(self.size))


class StarLayer:
    """单层星空渲染器 - 科幻风格"""
    
    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        star_count: int,
        speed: float,
        size_range: Tuple[float, float],
        color_base: Tuple[int, int, int],
        twinkle_enabled: bool = True
    ):
        self._stars: List[Star] = []
        self._scroll_offset = 0.0
        self._speed = speed
        self._screen_height = screen_height
        self._twinkle_enabled = twinkle_enabled
        self._twinkle = TwinkleController(star_count) if twinkle_enabled else None
        self._init_stars(screen_width, star_count, size_range, color_base)
    
    def _init_stars(
        self,
        screen_width: int,
        count: int,
        size_range: Tuple[float, float],
        color_base: Tuple[int, int, int]
    ) -> None:
        self._stars = []
        for _ in range(count):
            self._stars.append(Star(screen_width, self._screen_height, size_range, color_base))
    
    def update(self, delta_time: float = 1.0) -> None:
        self._scroll_offset += self._speed * delta_time
        if self._twinkle:
            self._twinkle.update(delta_time)
    
    def render(self, surface: pygame.Surface) -> None:
        for i, star in enumerate(self._stars):
            y = (star.base_y + self._scroll_offset) % self._screen_height
            brightness = self._twinkle.get_brightness(i) if self._twinkle else 1.0
            star.draw(surface, y, brightness)


class Nebula:
    """星云效果 - 彩色微弱光晕"""
    _nebula_cache = {}
    
    def __init__(self, screen_width: int, screen_height: int):
        self.x = random.randint(-200, screen_width + 200)
        self.base_y = random.randint(0, screen_height)
        self.radius = random.randint(100, 250)
        self.color = random.choice([
            (60, 20, 80),
            (20, 40, 80),
            (40, 60, 80),
            (80, 30, 60),
            (30, 60, 80)
        ])
        self.alpha = random.randint(15, 35)
        self.speed = random.uniform(0.1, 0.3)
        self._cached_surface = None
        self._cache_key = None
    
    @classmethod
    def clear_cache(cls) -> None:
        cls._nebula_cache.clear()
    
    def _get_nebula_surface(self) -> pygame.Surface:
        cache_key = (self.radius, self.color, self.alpha)
        if cache_key not in Nebula._nebula_cache:
            nebula_surface = pygame.Surface((self.radius * 2 + 20, self.radius * 2 + 20), pygame.SRCALPHA)
            for i in range(self.radius, 0, -2):
                alpha = int(self.alpha * (1 - i / self.radius) * 0.5)
                color = (*self.color, alpha)
                pygame.draw.circle(
                    nebula_surface, 
                    color,
                    (self.radius + 10, self.radius + 10), 
                    i
                )
            Nebula._nebula_cache[cache_key] = nebula_surface
        return Nebula._nebula_cache[cache_key]
    
    def draw(self, surface: pygame.Surface, y: float) -> None:
        nebula_surface = self._get_nebula_surface()
        surface.blit(
            nebula_surface, 
            (int(self.x - self.radius - 10), int(y - self.radius - 10))
        )


class NebulaLayer:
    """动态星云层 - 背景装饰效果"""
    
    def __init__(self, screen_width: int, screen_height: int, nebula_count: int = 4):
        self._nebulas: List[Nebula] = []
        self._scroll_offset = 0.0
        self._speed = 0.1
        self._screen_height = screen_height
        self._init_nebulas(screen_width, screen_height, nebula_count)
    
    def _init_nebulas(self, screen_width: int, screen_height: int, count: int) -> None:
        self._nebulas = []
        for _ in range(count):
            self._nebulas.append(Nebula(screen_width, screen_height))
    
    def update(self, delta_time: float = 1.0) -> None:
        self._scroll_offset += self._speed * delta_time
    
    def render(self, surface: pygame.Surface) -> None:
        for nebula in self._nebulas:
            y = (nebula.base_y + self._scroll_offset) % self._screen_height
            nebula.draw(surface, y)


class Meteor:
    """流星效果 - 带有拖尾"""
    
    def __init__(self, screen_width: int, screen_height: int):
        self.x = random.randint(0, screen_width)
        self.y = random.randint(-50, 0)
        self.speed = random.uniform(8, 15)
        self.angle = math.radians(random.uniform(30, 60))
        self.vx = math.cos(self.angle) * self.speed
        self.vy = math.sin(self.angle) * self.speed
        self.trail: List[Tuple[float, float, float]] = []
        self.life = random.randint(30, 60)
        self.max_life = self.life
        self.is_alive = True
    
    def update(self, delta_time: float = 1.0) -> None:
        if not self.is_alive:
            return
        
        self.trail.append((self.x, self.y, self.life / self.max_life))
        if len(self.trail) > 8:
            self.trail.pop(0)
        
        self.x += self.vx * delta_time
        self.y += self.vy * delta_time
        self.life -= delta_time
        
        if self.life <= 0:
            self.is_alive = False
    
    def draw(self, surface: pygame.Surface) -> None:
        if not self.is_alive:
            return
        
        for i, (tx, ty, alpha) in enumerate(self.trail):
            size = max(1, int(3 - i * 0.3))
            brightness = int(255 * alpha)
            color = (
                min(255, brightness + 100),
                min(255, brightness + 150),
                brightness
            )
            pygame.draw.circle(surface, color, (int(tx), int(ty)), size)


class MeteorSystem:
    """流星效果系统 - 随机生成流星"""
    
    def __init__(self):
        self._meteors: List[Meteor] = []
        self._next_spawn_time = random.uniform(5, 15)
        self._spawn_interval = random.uniform(5, 15)
        self._screen_width = 800
        self._screen_height = 600
    
    def set_screen_size(self, width: int, height: int) -> None:
        self._screen_width = width
        self._screen_height = height
    
    def _spawn_meteor(self) -> None:
        self._meteors.append(Meteor(self._screen_width, self._screen_height))
        self._spawn_interval = random.uniform(5, 15)
    
    def update(self, delta_time: float = 1.0) -> None:
        self._next_spawn_time -= delta_time
        if self._next_spawn_time <= 0:
            self._spawn_meteor()
            self._next_spawn_time = self._spawn_interval
        
        for meteor in self._meteors:
            meteor.update(delta_time)
        
        self._meteors = [m for m in self._meteors if m.is_alive]
    
    def render(self, surface: pygame.Surface) -> None:
        for meteor in self._meteors:
            meteor.draw(surface)


class GameSceneBackground:
    """游戏场景星空背景 - 三层视差科幻星空效果"""
    _gradient_cache = {}
    _particle_surface_cache = {}
    
    def __init__(self, screen_width: int = 800, screen_height: int = 600):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.time = 0.0
        self._cached_gradient = None
        
        self._layer_far = StarLayer(
            screen_width, screen_height, 150, 0.3, (0.5, 1.5), (100, 120, 180)
        )
        self._layer_mid = StarLayer(
            screen_width, screen_height, 60, 1.0, (1.5, 2.5), (150, 180, 255)
        )
        self._layer_near = StarLayer(
            screen_width, screen_height, 30, 2.0, (2.5, 4.0), (200, 220, 255)
        )
        
        self._nebula_layer = NebulaLayer(screen_width, screen_height)
        self._meteor_system = MeteorSystem()
        self._meteor_system.set_screen_size(screen_width, screen_height)
        
        self.particles: List[dict] = []
        
        self._generate_gradient()
    
    def _generate_gradient(self) -> None:
        cache_key = (self.screen_width, self.screen_height)
        if cache_key not in GameSceneBackground._gradient_cache:
            gradient = pygame.Surface((self.screen_width, self.screen_height))
            for y in range(self.screen_height):
                ratio = y / self.screen_height
                r = int(5 + ratio * 10)
                g = int(5 + ratio * 8)
                b = int(20 + ratio * 30)
                pygame.draw.line(gradient, (r, g, b), (0, y), (self.screen_width, y))
            GameSceneBackground._gradient_cache[cache_key] = gradient
        self._cached_gradient = GameSceneBackground._gradient_cache[cache_key]
    
    @classmethod
    def clear_all_caches(cls) -> None:
        cls._gradient_cache.clear()
        cls._particle_surface_cache.clear()
        Star.clear_cache()
        Nebula.clear_cache()
    
    def _get_particle_surface(self, size: float) -> pygame.Surface:
        size_key = int(size * 10)
        if size_key not in GameSceneBackground._particle_surface_cache:
            particle_surf = pygame.Surface((int(size * 2 + 2), int(size * 2 + 2)), pygame.SRCALPHA)
            GameSceneBackground._particle_surface_cache[size_key] = particle_surf
        return GameSceneBackground._particle_surface_cache[size_key]
    
    def update(self, delta_time: float = 1.0) -> None:
        self.time += delta_time
        self._layer_far.update(delta_time)
        self._layer_mid.update(delta_time)
        self._layer_near.update(delta_time)
        self._nebula_layer.update(delta_time)
        self._meteor_system.update(delta_time)
        
        self.particles = [p for p in self.particles if self._update_particle(p)]
    
    def _update_particle(self, particle: dict) -> bool:
        particle['x'] += particle['vx']
        particle['y'] += particle['vy']
        particle['life'] -= 1
        return particle['life'] > 0
    
    def spawn_particle(self, x: float, y: float, color: tuple) -> None:
        for _ in range(5):
            self.particles.append({
                'x': x,
                'y': y,
                'vx': random.uniform(-1, 1),
                'vy': random.uniform(-2, 0),
                'size': random.uniform(1, 3),
                'life': random.randint(20, 40),
                'color': color
            })
    
    def draw(self, surface: pygame.Surface) -> None:
        if self._cached_gradient:
            surface.blit(self._cached_gradient, (0, 0))
        
        self._nebula_layer.render(surface)
        self._layer_far.render(surface)
        self._meteor_system.render(surface)
        self._layer_mid.render(surface)
        self._layer_near.render(surface)
        
        for particle in self.particles:
            alpha = int(255 * particle['life'] / 40)
            color = (*particle['color'][:3], alpha) if len(particle['color']) == 4 else (*particle['color'], alpha)
            particle_surf = self._get_particle_surface(particle['size'])
            pygame.draw.circle(
                particle_surf, color,
                (int(particle['size'] + 1), int(particle['size'] + 1)),
                int(particle['size'])
            )
            surface.blit(
                particle_surf,
                (int(particle['x'] - particle['size'] - 1), int(particle['y'] - particle['size'] - 1))
            )
    
    def resize(self, screen_width: int, screen_height: int) -> None:
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        self._layer_far = StarLayer(
            screen_width, screen_height, 150, 0.3, (0.5, 1.5), (100, 120, 180)
        )
        self._layer_mid = StarLayer(
            screen_width, screen_height, 60, 1.0, (1.5, 2.5), (150, 180, 255)
        )
        self._layer_near = StarLayer(
            screen_width, screen_height, 30, 2.0, (2.5, 4.0), (200, 220, 255)
        )
        self._nebula_layer = NebulaLayer(screen_width, screen_height)
        self._meteor_system = MeteorSystem()
        self._meteor_system.set_screen_size(screen_width, screen_height)
        self._generate_gradient()
