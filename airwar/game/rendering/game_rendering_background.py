import pygame
import random
from typing import List, Optional


class Star:
    _glow_cache: dict = {}

    def __init__(self, screen_width: int, screen_height: int):
        self.x = random.randint(0, screen_width)
        self.y = random.randint(0, screen_height)
        self.size = random.uniform(0.5, 2.5)
        self.speed = random.uniform(0.5, 2.0)
        self.brightness = random.randint(100, 255)
        self.twinkle_speed = random.uniform(0.02, 0.08)
        self.twinkle_offset = random.uniform(0, 6.28)
        self._cached_glow_size: Optional[int] = None
        self._cached_glow: Optional[pygame.Surface] = None

    def update(self, screen_height: int) -> None:
        self.y += self.speed
        if self.y > screen_height:
            self.y = 0
            self.x = random.randint(0, 800)

    @classmethod
    def clear_cache(cls) -> None:
        cls._glow_cache.clear()

    def _get_glow_surface(self) -> pygame.Surface:
        cache_key = int(self.size * 10)
        if cache_key not in Star._glow_cache:
            size_int = int(self.size)
            if size_int < 1:
                size_int = 1
            glow_size = size_int * 4 + 4
            glow = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
            for i in range(size_int * 2, 0, -1):
                alpha = int(50 * (1 - i / (size_int * 2)))
                pygame.draw.circle(glow, (150, 180, 255, alpha),
                                  (size_int * 2 + 2, size_int * 2 + 2), i)
            Star._glow_cache[cache_key] = glow
        return Star._glow_cache[cache_key]

    def draw(self, surface: pygame.Surface, time: float) -> None:
        twinkle = (self.brightness + 50 * (1 - abs(1 - (time * self.twinkle_speed + self.twinkle_offset) % 2))) / 2
        twinkle = max(50, min(255, int(twinkle)))

        if self.size > 1.5:
            glow = self._get_glow_surface()
            size_int = int(self.size)
            if size_int < 1:
                size_int = 1
            surface.blit(glow, (int(self.x - size_int * 2 - 2), int(self.y - size_int * 2 - 2)))

        color = (twinkle, twinkle, min(255, twinkle + 30))
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), int(self.size))


class Nebula:
    _nebula_cache: dict = {}

    def __init__(self, screen_width: int, screen_height: int):
        self.x = random.randint(-200, screen_width + 200)
        self.y = random.randint(0, screen_height)
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
        self._cached_surface: Optional[pygame.Surface] = None
        self._cache_key: Optional[tuple] = None

    def update(self, screen_height: int) -> None:
        self.y += self.speed
        if self.y > screen_height + self.radius:
            self.y = -self.radius
            self.x = random.randint(-200, 1000)

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
                pygame.draw.circle(nebula_surface, color,
                                 (self.radius + 10, self.radius + 10), i)
            Nebula._nebula_cache[cache_key] = nebula_surface
        return Nebula._nebula_cache[cache_key]

    def draw(self, surface: pygame.Surface) -> None:
        nebula_surface = self._get_nebula_surface()
        surface.blit(nebula_surface, (int(self.x - self.radius - 10), int(self.y - self.radius - 10)))


class GameSceneBackground:
    _gradient_cache: dict = {}
    _particle_surface_cache: dict = {}

    def __init__(self, screen_width: int = 800, screen_height: int = 600):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.stars: List[Star] = []
        self.nebulas: List[Nebula] = []
        self.particles: List[dict] = []
        self.time = 0
        self._cached_gradient: Optional[pygame.Surface] = None
        self._init_stars()
        self._init_nebulas()
        self._generate_gradient()

    def _init_stars(self) -> None:
        for _ in range(80):
            self.stars.append(Star(self.screen_width, self.screen_height))

    def _init_nebulas(self) -> None:
        for _ in range(3):
            self.nebulas.append(Nebula(self.screen_width, self.screen_height))

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
        if size_key not in BackgroundRenderer._particle_surface_cache:
            particle_surf = pygame.Surface((int(size * 2 + 2), int(size * 2 + 2)), pygame.SRCALPHA)
            BackgroundRenderer._particle_surface_cache[size_key] = particle_surf
        return BackgroundRenderer._particle_surface_cache[size_key]

    def update(self) -> None:
        self.time += 0.05
        for star in self.stars:
            star.update(self.screen_height)
        for nebula in self.nebulas:
            nebula.update(self.screen_height)

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

        for nebula in self.nebulas:
            nebula.draw(surface)

        for particle in self.particles:
            alpha = int(255 * particle['life'] / 40)
            color = (*particle['color'][:3], alpha) if len(particle['color']) == 4 else (*particle['color'], alpha)
            particle_surf = self._get_particle_surface(particle['size'])
            pygame.draw.circle(particle_surf, color,
                              (int(particle['size'] + 1), int(particle['size'] + 1)), int(particle['size']))
            surface.blit(particle_surf, (int(particle['x'] - particle['size'] - 1), int(particle['y'] - particle['size'] - 1)))

        for star in self.stars:
            star.draw(surface, self.time)

    def resize(self, screen_width: int, screen_height: int) -> None:
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.stars.clear()
        self.nebulas.clear()
        self._init_stars()
        self._init_nebulas()
        self._generate_gradient()
