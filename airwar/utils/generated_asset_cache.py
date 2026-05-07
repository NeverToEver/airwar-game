"""Versioned on-disk cache for generated pygame image assets."""

import contextlib
import hashlib
import logging
import os
from collections.abc import Callable

import pygame

from airwar.utils.platform_paths import generated_asset_cache_dir as _platform_generated_asset_cache_dir


logger = logging.getLogger(__name__)

ASSET_CACHE_VERSION = 1


def generated_asset_cache_dir() -> str:
    """Return the directory used for generated local image assets."""
    return _platform_generated_asset_cache_dir()


def _cache_path(namespace: str, cache_key: tuple) -> str:
    digest = hashlib.sha256(repr((ASSET_CACHE_VERSION, namespace, cache_key)).encode("utf-8")).hexdigest()[:16]
    safe_namespace = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in namespace)
    return os.path.join(generated_asset_cache_dir(), f"{safe_namespace}_{digest}.png")


def _load_surface(path: str) -> pygame.Surface | None:
    try:
        surface = pygame.image.load(path)
        try:
            return surface.convert_alpha()
        except pygame.error:
            return surface
    except (OSError, pygame.error) as exc:
        logger.warning("Failed to load generated asset cache %s: %s", path, exc)
        return None


def _save_surface(path: str, surface: pygame.Surface) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = path + ".tmp.png"
    try:
        pygame.image.save(surface, tmp_path)
        os.replace(tmp_path, path)
    except (OSError, pygame.error) as exc:
        logger.warning("Failed to save generated asset cache %s: %s", path, exc)
        with contextlib.suppress(OSError):
            os.remove(tmp_path)


def load_or_build_generated_surface(
    namespace: str,
    cache_key: tuple,
    build_surface: Callable[[], pygame.Surface],
) -> pygame.Surface:
    """Load a generated PNG from disk, or build and save it on first use."""
    path = _cache_path(namespace, cache_key)
    if os.path.exists(path):
        cached = _load_surface(path)
        if cached is not None:
            return cached

    surface = build_surface()
    _save_surface(path, surface)
    return surface
