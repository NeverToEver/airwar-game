"""cProfile-based single-frame profiler.

Usage:
    python3 scripts/profile_hot_frame.py [--frame N] [--output FILE]

Spawns a minimal headless game scene and records the per-frame
breakdown using cProfile. Output is suitable for `snakeviz`.

The default scene has realistic mid-game load:
- 50 enemies, 80 player bullets, 1 player
- No boss, no mothership, no homecoming
- Pre-warms caches so first-frame allocation is not in the profile
"""

import argparse
import cProfile
import pstats
import sys
from pathlib import Path

# Ensure airwar is importable when running from project root.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame

from airwar.entities.base import BulletData, EnemyData, Rect
from airwar.game.managers.collision_controller import CollisionController


class _Bullet:
    __slots__ = ("rect", "data", "active", "_hit_enemies")

    def __init__(self, x, y, owner="player"):
        self.rect = Rect(int(x), int(y), 8, 8)
        self.data = BulletData(damage=20, owner=owner)
        self.active = True
        self._hit_enemies = set()

    def get_rect(self):
        return self.rect

    def has_hit_enemy(self, eid):
        return eid in self._hit_enemies

    def add_hit_enemy(self, eid):
        self._hit_enemies.add(eid)


class _Enemy:
    __slots__ = ("rect", "_hitbox", "data", "health", "active")

    def __init__(self, x, y, health=10):
        self.rect = Rect(int(x), int(y), 30, 30)
        self._hitbox = self.rect
        self.data = EnemyData(health=health, score=25)
        self.health = health
        self.active = True

    def get_hitbox(self):
        return self._hitbox

    def get_rect(self):
        return self.rect

    def take_damage(self, d):
        self.health -= d
        if self.health <= 0:
            self.active = False


class _Player:
    __slots__ = ("rect", "_hitbox", "health")

    def __init__(self, x=960, y=540):
        self.rect = Rect(x, y, 40, 40)
        self._hitbox = self.rect
        self.health = 100

    def get_hitbox(self):
        return self._hitbox

    def take_damage(self, d):
        self.health -= d


def build_scene(n_enemies=50, n_bullets=80, seed=42):
    """Build a deterministic mid-game test scene."""
    import random
    rng = random.Random(seed)
    player = _Player(960, 540)
    enemies = [
        _Enemy(50 + (i * 37 + rng.randint(0, 9)) % 1820, 50 + (i * 53 + rng.randint(0, 9)) % 980)
        for i in range(n_enemies)
    ]
    bullets = [
        _Bullet(50 + (i * 23 + rng.randint(0, 9)) % 1820, 50 + (i * 19 + rng.randint(0, 9)) % 980)
        for i in range(n_bullets)
    ]
    return player, enemies, bullets


def single_frame(player, enemies, bullets, bg_surface):
    """Run one frame's worth of subsystem work.

    Covers: background render + bullet-vs-enemy collision + player-vs-enemies scan.
    Intentionally avoids the full GameScene because that needs a display
    surface, event loop, and 10+ subsystems that are orthogonal to perf
    hotspots.
    """
    from airwar.game.rendering.game_rendering_background import SpaceBackground

    # Background render (biggest subsystem at ~0.5ms)
    if not hasattr(single_frame, "_bg"):
        single_frame._bg = SpaceBackground(1920, 1080)
    single_frame._bg.draw(bg_surface)
    single_frame._bg.update(1.0)

    # Player bullets vs enemies (Rust batch path)
    cc = single_frame._cc
    cc.check_player_bullets_vs_enemies(
        bullets, enemies, score_multiplier=1.0, explosive_level=0, piercing_level=0
    )
    # Player vs enemies linear scan
    cc.check_player_vs_enemies(
        player.get_hitbox(), enemies, lambda: False, lambda d: None
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--frame", type=int, default=10, help="number of frames to profile")
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="output .prof file (default: print top 30 to stdout)",
    )
    args = parser.parse_args()

    pygame.init()
    surface = pygame.Surface((1920, 1080))
    surface.fill((0, 0, 0))

    # Init subsystem singletons so we don't profile their init.
    single_frame._cc = CollisionController()
    player, enemies, bullets = build_scene()

    # Warm up
    for _ in range(3):
        single_frame(player, enemies, bullets, surface)

    # Profile
    pr = cProfile.Profile()
    pr.enable()
    for _ in range(args.frame):
        single_frame(player, enemies, bullets, surface)
    pr.disable()

    stats = pstats.Stats(pr)
    stats.strip_dirs().sort_stats("cumulative")

    if args.output:
        pr.dump_stats(args.output)
        print(f"Profile written to {args.output} — visualize with: snakeviz {args.output}")
    else:
        print(f"\n=== Top 30 by cumulative time ({args.frame} frames) ===\n")
        stats.print_stats(30)


if __name__ == "__main__":
    main()
