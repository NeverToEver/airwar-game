from typing import Callable, Dict, Tuple
import pygame


Color = Tuple[int, ...]


class SurfaceCache:
    _gradient_cache: Dict[tuple, pygame.Surface] = {}
    _rect_fill_cache: Dict[tuple, pygame.Surface] = {}
    _rect_border_cache: Dict[tuple, pygame.Surface] = {}
    _rect_glow_cache: Dict[tuple, pygame.Surface] = {}
    _particle_glow_cache: Dict[tuple, pygame.Surface] = {}
    _circle_cache: Dict[tuple, pygame.Surface] = {}
    _line_cache: Dict[tuple, pygame.Surface] = {}
    _fade_cache: Dict[tuple, pygame.Surface] = {}

    @staticmethod
    def _normalize_color(color: Color) -> Tuple[int, int, int, int]:
        if len(color) == 4:
            return color  # type: ignore[return-value]
        return color[0], color[1], color[2], 255

    @staticmethod
    def _quantize_alpha(alpha: int, step: int = 8) -> int:
        alpha_int = max(0, min(255, int(alpha)))
        if alpha_int == 0:
            return 0
        return min(255, int(round(alpha_int / step) * step))

    @staticmethod
    def _get_or_create(
        cache: Dict[tuple, pygame.Surface],
        key: tuple,
        max_entries: int,
        builder: Callable[[], pygame.Surface],
    ) -> pygame.Surface:
        cached = cache.get(key)
        if cached is not None:
            cache.pop(key)
            cache[key] = cached
            return cached

        surface = builder()
        cache[key] = surface
        if len(cache) > max_entries:
            oldest_key = next(iter(cache))
            cache.pop(oldest_key, None)
        return surface

    @classmethod
    def get_vertical_gradient(
        cls,
        width: int,
        height: int,
        color1: Color,
        color2: Color,
        step: int = 1,
    ) -> pygame.Surface:
        draw_step = max(1, step)
        key = (width, height, color1, color2, draw_step)

        def _build() -> pygame.Surface:
            gradient = pygame.Surface((width, height))
            for y in range(0, height, draw_step):
                ratio = y / max(1, height)
                r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
                g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
                b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
                pygame.draw.rect(gradient, (r, g, b), (0, y, width, draw_step))
            return gradient

        return cls._get_or_create(cls._gradient_cache, key, 12, _build)

    @classmethod
    def get_rect_fill(
        cls,
        width: int,
        height: int,
        color: Color,
        border_radius: int = 0,
    ) -> pygame.Surface:
        key = (width, height, color, border_radius)

        def _build() -> pygame.Surface:
            surface = pygame.Surface((width, height), pygame.SRCALPHA)
            pygame.draw.rect(surface, cls._normalize_color(color), surface.get_rect(), border_radius=border_radius)
            return surface

        return cls._get_or_create(cls._rect_fill_cache, key, 128, _build)

    @classmethod
    def get_rect_border(
        cls,
        width: int,
        height: int,
        color: Color,
        border_width: int = 1,
        border_radius: int = 0,
    ) -> pygame.Surface:
        key = (width, height, color, border_width, border_radius)

        def _build() -> pygame.Surface:
            surface = pygame.Surface((width, height), pygame.SRCALPHA)
            pygame.draw.rect(
                surface,
                cls._normalize_color(color),
                surface.get_rect(),
                width=border_width,
                border_radius=border_radius,
            )
            return surface

        return cls._get_or_create(cls._rect_border_cache, key, 128, _build)

    @classmethod
    def get_rect_glow(
        cls,
        width: int,
        height: int,
        color: Color,
        border_radius: int = 0,
    ) -> pygame.Surface:
        key = (width, height, color, border_radius)

        def _build() -> pygame.Surface:
            surface = pygame.Surface((width, height), pygame.SRCALPHA)
            pygame.draw.rect(surface, cls._normalize_color(color), surface.get_rect(), border_radius=border_radius)
            return surface

        return cls._get_or_create(cls._rect_glow_cache, key, 160, _build)

    @classmethod
    def get_particle_glow(cls, size: int, color: Color, alpha: int) -> pygame.Surface:
        size_int = max(1, int(size))
        alpha_bucket = cls._quantize_alpha(alpha)
        key = (size_int, color[:3], alpha_bucket)

        def _build() -> pygame.Surface:
            surface_size = size_int * 4
            particle_surface = pygame.Surface((surface_size, surface_size), pygame.SRCALPHA)
            for radius in range(size_int * 2, 0, -2):
                layer_alpha = int(alpha_bucket * (size_int * 2 - radius) / max(1, size_int * 2) * 0.4)
                pygame.draw.circle(
                    particle_surface,
                    (*color[:3], layer_alpha),
                    (surface_size // 2, surface_size // 2),
                    radius,
                )
            return particle_surface

        return cls._get_or_create(cls._particle_glow_cache, key, 96, _build)

    @classmethod
    def get_circle_surface(cls, radius: int, color: Color) -> pygame.Surface:
        radius_int = max(1, int(radius))
        key = (radius_int, color)

        def _build() -> pygame.Surface:
            surface = pygame.Surface((radius_int * 2, radius_int * 2), pygame.SRCALPHA)
            pygame.draw.circle(surface, cls._normalize_color(color), (radius_int, radius_int), radius_int)
            return surface

        return cls._get_or_create(cls._circle_cache, key, 96, _build)

    @classmethod
    def get_line_surface(cls, width: int, height: int, color: Color) -> pygame.Surface:
        key = (width, height, color)

        def _build() -> pygame.Surface:
            surface = pygame.Surface((width, height), pygame.SRCALPHA)
            surface.fill(cls._normalize_color(color))
            return surface

        return cls._get_or_create(cls._line_cache, key, 64, _build)

    @classmethod
    def get_fade_overlay(
        cls,
        width: int,
        height: int,
        alpha: int,
        color: Color = (0, 0, 0),
    ) -> pygame.Surface:
        alpha_bucket = cls._quantize_alpha(alpha)
        key = (width, height, alpha_bucket, color)

        def _build() -> pygame.Surface:
            overlay = pygame.Surface((width, height), pygame.SRCALPHA)
            overlay.fill((*color[:3], alpha_bucket))
            return overlay

        return cls._get_or_create(cls._fade_cache, key, 48, _build)

    @classmethod
    def clear(cls) -> None:
        cls._gradient_cache.clear()
        cls._rect_fill_cache.clear()
        cls._rect_border_cache.clear()
        cls._rect_glow_cache.clear()
        cls._particle_glow_cache.clear()
        cls._circle_cache.clear()
        cls._line_cache.clear()
        cls._fade_cache.clear()
