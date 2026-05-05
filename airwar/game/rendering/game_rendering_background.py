"""Background renderer — parallax starfield and rainforest visuals."""
import pygame
import math
import random
from typing import List, Tuple
from airwar.config.design_tokens import get_design_tokens
import contextlib


class SpaceBackground:
    """Space game background with parallax starfield and nebula hints.

    Performance optimized:
    - Pre-rendered gradient cache
    - Layered parallax stars (3 layers)
    - Cached star surfaces
    """

    _gradient_cache = {}
    _star_cache = {}

    FAR_LAYER = {'speed_mult': 0.3, 'count_divisor': 1, 'size_range': (0.5, 1.5), 'color_brightness': 80}
    MID_LAYER = {'speed_mult': 0.6, 'count_divisor': 2, 'size_range': (1.0, 2.0), 'color_brightness': 120}
    NEAR_LAYER = {'speed_mult': 1.2, 'count_divisor': 4, 'size_range': (1.5, 3.0), 'color_brightness': 160}

    def __init__(self, screen_width: int = 800, screen_height: int = 600):
        self.tokens = get_design_tokens()
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.time = 0.0

        self._cached_gradient = None
        self._init_layers(screen_width, screen_height)
        self._generate_gradient()

    def _init_layers(self, screen_width: int, screen_height: int) -> None:
        """Initialize parallax star layers using token values."""
        colors = self.tokens.colors
        anim = self.tokens.animation
        components = self.tokens.components

        # Far layer - tiny stars, very slow
        self._layer_far = StarLayer(
            screen_width, screen_height,
            count=components.STAR_COUNT // self.FAR_LAYER['count_divisor'],
            speed=anim.STAR_SPEED * self.FAR_LAYER['speed_mult'],
            size_range=self.FAR_LAYER['size_range'],
            color=colors.star_color(self.FAR_LAYER['color_brightness']),
            twinkle_speed_range=(anim.TWINKLE_SPEED_MIN, anim.TWINKLE_SPEED_MAX)
        )

        # Mid layer - medium stars
        self._layer_mid = StarLayer(
            screen_width, screen_height,
            count=components.STAR_COUNT // self.MID_LAYER['count_divisor'],
            speed=anim.STAR_SPEED * self.MID_LAYER['speed_mult'],
            size_range=self.MID_LAYER['size_range'],
            color=colors.star_color(self.MID_LAYER['color_brightness']),
            twinkle_speed_range=(anim.TWINKLE_SPEED_MIN, anim.TWINKLE_SPEED_MAX)
        )

        # Near layer - larger stars, faster
        self._layer_near = StarLayer(
            screen_width, screen_height,
            count=components.STAR_COUNT // self.NEAR_LAYER['count_divisor'],
            speed=anim.STAR_SPEED * self.NEAR_LAYER['speed_mult'],
            size_range=self.NEAR_LAYER['size_range'],
            color=colors.star_color(self.NEAR_LAYER['color_brightness']),
            twinkle_speed_range=(anim.TWINKLE_SPEED_MIN, anim.TWINKLE_SPEED_MAX)
        )

        # Dust particles layer
        self._dust_layer = DustLayer(
            screen_width, screen_height,
            count=components.PARTICLE_COUNT // 3,
            speed_range=(anim.PARTICLE_SPEED_MIN, anim.PARTICLE_SPEED_MAX)
        )

    def _generate_gradient(self) -> None:
        """Generate deep space gradient background."""
        cache_key = (self.screen_width, self.screen_height)
        if cache_key not in SpaceBackground._gradient_cache:
            gradient = pygame.Surface((self.screen_width, self.screen_height))
            colors = self.tokens.colors
            bg_primary = colors.BACKGROUND_PRIMARY
            bg_secondary = colors.BACKGROUND_SECONDARY

            for y in range(self.screen_height):
                ratio = y / self.screen_height
                r = int(bg_primary[0] * (1 - ratio) + bg_secondary[0] * ratio)
                g = int(bg_primary[1] * (1 - ratio) + bg_secondary[1] * ratio)
                b = int(bg_primary[2] * (1 - ratio) + bg_secondary[2] * ratio)
                pygame.draw.line(gradient, (r, g, b), (0, y), (self.screen_width, y))
            with contextlib.suppress(pygame.error):
                gradient = gradient.convert()
            SpaceBackground._gradient_cache[cache_key] = gradient
        self._cached_gradient = SpaceBackground._gradient_cache[cache_key]

    def update(self, delta_time: float = 1.0) -> None:
        self.time += delta_time
        self._layer_far.update(delta_time)
        self._layer_mid.update(delta_time)
        self._layer_near.update(delta_time)
        self._dust_layer.update(delta_time)

    def draw(self, surface: pygame.Surface) -> None:
        if self._cached_gradient:
            surface.blit(self._cached_gradient, (0, 0))

        self._layer_far.render(surface, self.time)
        self._layer_mid.render(surface, self.time)
        self._layer_near.render(surface, self.time)
        self._dust_layer.render(surface, self.time)

    def resize(self, screen_width: int, screen_height: int) -> None:
        self.screen_width = screen_width
        self.screen_height = screen_height
        self._init_layers(screen_width, screen_height)
        self._generate_gradient()


class StarLayer:
    """Parallax star layer with twinkling effect."""

    GLOW_BRIGHTNESS_THRESHOLD = 30
    GLOW_ALPHA_CAP = 40
    GLOW_ALPHA_DIVISOR = 4
    CORE_BLUE_BOOST = 20

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        count: int,
        speed: float,
        size_range: Tuple[float, float],
        color: Tuple[int, int, int],
        twinkle_speed_range: Tuple[float, float]
    ):
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._speed = speed
        self._size_range = size_range
        self._color = color
        self._twinkle_speed_range = twinkle_speed_range
        self._scroll_offset = 0.0
        self._stars: List[dict] = []
        self._glow_cache: dict = {}
        self._sin_table_size = 1024
        self._sin_table = [math.sin(math.tau * i / self._sin_table_size) for i in range(self._sin_table_size)]
        self._sin_table_mask = self._sin_table_size - 1
        self._init_stars(screen_width, screen_height, count)

    def _init_stars(self, screen_width: int, screen_height: int, count: int) -> None:
        self._stars = []
        for _ in range(count):
            self._stars.append({
                'x': random.random(),
                'y': random.random(),
                'size': random.uniform(self._size_range[0], self._size_range[1]),
                'brightness': random.uniform(0.5, 1.0),
                'twinkle_speed': random.uniform(
                    self._twinkle_speed_range[0],
                    self._twinkle_speed_range[1]
                ),
                'twinkle_offset': random.random() * math.tau,
            })

    def update(self, delta_time: float = 1.0) -> None:
        self._scroll_offset += self._speed * delta_time

    def render(self, surface: pygame.Surface, time: float) -> None:
        for star in self._stars:
            y = (star['y'] + self._scroll_offset) % 1.0

            x = int(star['x'] * self._screen_width)
            y_pos = int(y * self._screen_height)

            idx = int((time * star['twinkle_speed'] + star['twinkle_offset']) * (self._sin_table_size / math.tau)) & self._sin_table_mask
            twinkle = self._sin_table[idx]
            brightness = int(star['brightness'] * (0.5 + 0.5 * twinkle) * 255)

            size = max(1, int(star['size']))

            if brightness > self.GLOW_BRIGHTNESS_THRESHOLD:
                glow_radius = size * 2
                glow_alpha = min(self.GLOW_ALPHA_CAP, brightness // self.GLOW_ALPHA_DIVISOR)
                cache_key = (glow_radius, glow_alpha)
                if cache_key not in self._glow_cache:
                    glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
                    pygame.draw.circle(
                        glow_surf,
                        (*self._color, glow_alpha),
                        (glow_radius, glow_radius),
                        glow_radius
                    )
                    self._glow_cache[cache_key] = glow_surf
                surface.blit(self._glow_cache[cache_key], (x - glow_radius, y_pos - glow_radius),
                           special_flags=pygame.BLEND_RGBA_ADD)

            core_brightness = max(0, min(255, brightness))
            pygame.draw.circle(
                surface,
                (core_brightness, core_brightness, min(255, core_brightness + self.CORE_BLUE_BOOST)),
                (x, y_pos),
                size
            )


class DustLayer:
    """Space dust particles drifting slowly."""

    DUST_SIZE_RANGE = (1.0, 2.5)
    DUST_PULSE_ALPHA_BASE = 0.6
    DUST_PULSE_ALPHA_AMP = 0.4
    DUST_PULSE_SIZE_BASE = 0.7
    DUST_PULSE_SIZE_AMP = 0.3

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        count: int,
        speed_range: Tuple[float, float]
    ):
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._dust: List[dict] = []
        self._speed_range = speed_range
        self._scroll_offset = 0.0
        self._glow_cache: dict = {}
        self._init_dust(screen_width, screen_height, count)

    def _init_dust(self, screen_width: int, screen_height: int, count: int) -> None:
        self._dust = []
        for _ in range(count):
            speed = random.uniform(self._speed_range[0], self._speed_range[1])
            self._dust.append({
                'x': random.random(),
                'y': random.random(),
                'size': random.uniform(*self.DUST_SIZE_RANGE),
                'speed': speed * 0.3,
                'alpha': random.randint(30, 80),
                'drift_x': random.uniform(-0.0001, 0.0001),
                'pulse_speed': random.uniform(0.01, 0.03),
                'pulse_offset': random.random() * math.tau,
            })

    def update(self, delta_time: float = 1.0) -> None:
        self._scroll_offset += delta_time * 0.02

        for dust in self._dust:
            dust['y'] -= dust['speed'] * delta_time * 0.01
            dust['x'] += dust.get('drift_x', 0) * delta_time

            if dust['y'] < -0.05:
                dust['y'] = 1.05
                dust['x'] = random.random()
            if dust['x'] < -0.05:
                dust['x'] = 1.05
            elif dust['x'] > 1.05:
                dust['x'] = -0.05

    def render(self, surface: pygame.Surface, time: float) -> None:
        colors = get_design_tokens().colors
        particle_color = colors.PARTICLE_PRIMARY

        for d in self._dust:
            x = int(d['x'] * self._screen_width)
            y = int(d['y'] * self._screen_height)

            pulse = math.sin(time * d['pulse_speed'] + d['pulse_offset'])
            alpha = int(d['alpha'] * (self.DUST_PULSE_ALPHA_BASE + self.DUST_PULSE_ALPHA_AMP * pulse))
            size = max(1, int(d['size'] * (self.DUST_PULSE_SIZE_BASE + self.DUST_PULSE_SIZE_AMP * pulse)))

            cache_key = (size, alpha)
            if cache_key not in self._glow_cache:
                dust_surf = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
                for layer in range(size * 2, 0, -2):
                    layer_alpha = int(alpha * (size * 2 - layer) / (size * 2) * 0.3)
                    pygame.draw.circle(
                        dust_surf,
                        (*particle_color, layer_alpha),
                        (size * 2, size * 2),
                        layer
                    )
                self._glow_cache[cache_key] = dust_surf
            surface.blit(self._glow_cache[cache_key], (x - size * 2, y - size * 2),
                        special_flags=pygame.BLEND_RGBA_ADD)

