import pygame
import random
from typing import List


class Star:
    def __init__(self, screen_width: int, screen_height: int):
        self.x = random.randint(0, screen_width)
        self.y = random.randint(0, screen_height)
        self.size = random.uniform(0.5, 2.5)
        self.speed = random.uniform(0.5, 2.0)
        self.brightness = random.randint(100, 255)
        self.twinkle_speed = random.uniform(0.02, 0.08)
        self.twinkle_offset = random.uniform(0, 6.28)

    def update(self, screen_height: int) -> None:
        self.y += self.speed
        if self.y > screen_height:
            self.y = 0
            self.x = random.randint(0, 800)

    def draw(self, surface: pygame.Surface, time: float) -> None:
        twinkle = (self.brightness + 50 * (1 - abs(1 - (time * self.twinkle_speed + self.twinkle_offset) % 2))) / 2
        twinkle = max(50, min(255, int(twinkle)))

        if self.size > 1.5:
            glow = pygame.Surface((int(self.size * 4 + 4), int(self.size * 4 + 4)), pygame.SRCALPHA)
            for i in range(int(self.size * 2), 0, -1):
                alpha = int(50 * (1 - i / (self.size * 2)))
                pygame.draw.circle(glow, (150, 180, 255, alpha),
                                  (int(self.size * 2 + 2), int(self.size * 2 + 2)), i)
            surface.blit(glow, (int(self.x - self.size * 2 - 2), int(self.y - self.size * 2 - 2)))

        color = (twinkle, twinkle, min(255, twinkle + 30))
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), int(self.size))


class Nebula:
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

    def update(self, screen_height: int) -> None:
        self.y += self.speed
        if self.y > screen_height + self.radius:
            self.y = -self.radius
            self.x = random.randint(-200, 1000)

    def draw(self, surface: pygame.Surface) -> None:
        nebula_surface = pygame.Surface((self.radius * 2 + 20, self.radius * 2 + 20), pygame.SRCALPHA)
        for i in range(self.radius, 0, -2):
            alpha = int(self.alpha * (1 - i / self.radius) * 0.5)
            color = (*self.color, alpha)
            pygame.draw.circle(nebula_surface, color,
                             (self.radius + 10, self.radius + 10), i)
        surface.blit(nebula_surface, (int(self.x - self.radius - 10), int(self.y - self.radius - 10)))


class BackgroundRenderer:
    def __init__(self, screen_width: int = 800, screen_height: int = 600):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.stars: List[Star] = []
        self.nebulas: List[Nebula] = []
        self.particles: List[dict] = []
        self.time = 0
        self._init_stars()
        self._init_nebulas()

    def _init_stars(self) -> None:
        for _ in range(80):
            self.stars.append(Star(self.screen_width, self.screen_height))

    def _init_nebulas(self) -> None:
        for _ in range(3):
            self.nebulas.append(Nebula(self.screen_width, self.screen_height))

    def update(self) -> None:
        self.time += 0.05
        for star in self.stars:
            star.update(self.screen_height)
        for nebula in self.nebulas:
            nebula.update(self.screen_height)

        for particle in self.particles[:]:
            particle['x'] += particle['vx']
            particle['y'] += particle['vy']
            particle['life'] -= 1
            if particle['life'] <= 0:
                self.particles.remove(particle)

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
        gradient = pygame.Surface((self.screen_width, self.screen_height))
        for y in range(self.screen_height):
            ratio = y / self.screen_height
            r = int(5 + ratio * 10)
            g = int(5 + ratio * 8)
            b = int(20 + ratio * 30)
            pygame.draw.line(gradient, (r, g, b), (0, y), (self.screen_width, y))
        surface.blit(gradient, (0, 0))

        for nebula in self.nebulas:
            nebula.draw(surface)

        for particle in self.particles:
            alpha = int(255 * particle['life'] / 40)
            color = (*particle['color'][:3], alpha) if len(particle['color']) == 4 else (*particle['color'], alpha)
            particle_surf = pygame.Surface((int(particle['size'] * 2 + 2), int(particle['size'] * 2 + 2)), pygame.SRCALPHA)
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
