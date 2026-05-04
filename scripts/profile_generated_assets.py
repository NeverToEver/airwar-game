"""Profile generated sprite cache cost for cold build, disk load, and memory hits."""

import argparse
import os
import shutil
import sys
import tempfile
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame

from airwar.utils._sprites_ships import (
    _boss_sprite_cache,
    _elite_sprite_cache,
    _enemy_sprite_cache,
    _player_sprite_cache,
    get_boss_sprite,
    get_elite_enemy_sprite,
    get_enemy_sprite,
    get_player_sprite,
    prewarm_ship_sprite_caches,
)
from airwar.utils.generated_asset_cache import generated_asset_cache_dir


def _clear_memory_caches() -> None:
    _player_sprite_cache.clear()
    _enemy_sprite_cache.clear()
    _elite_sprite_cache.clear()
    _boss_sprite_cache.clear()


def _time_call(label: str, call, iterations: int = 1) -> float:
    start = time.perf_counter()
    for _ in range(iterations):
        call()
    elapsed_ms = (time.perf_counter() - start) * 1000
    print(f"{label}: {elapsed_ms:.2f} ms")
    return elapsed_ms


def _sample_common_sprites() -> None:
    get_player_sprite(68, 82)
    for health_ratio in (1.0, 0.5, 0.25):
        get_enemy_sprite(50, 50, health_ratio)
        get_elite_enemy_sprite(65, 65, health_ratio)
        get_boss_sprite(120, 100, health_ratio)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=200, help="Memory-hit iterations to measure.")
    parser.add_argument("--cache-dir", default=None, help="Generated asset cache directory. Defaults to a temp dir.")
    args = parser.parse_args()

    cache_dir = args.cache_dir or tempfile.mkdtemp(prefix="airwar-generated-assets-")
    os.environ["AIRWAR_GENERATED_ASSET_DIR"] = cache_dir

    pygame.init()
    pygame.display.set_mode((1, 1))
    try:
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)

        _clear_memory_caches()
        _time_call("cold build + png save", prewarm_ship_sprite_caches)

        png_count = sum(1 for name in os.listdir(generated_asset_cache_dir()) if name.endswith(".png"))
        print(f"generated png files: {png_count}")

        _clear_memory_caches()
        _time_call("disk png load", _sample_common_sprites)

        _time_call(f"memory cache hits x{args.iterations}", _sample_common_sprites, args.iterations)
        print(f"cache dir: {generated_asset_cache_dir()}")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
