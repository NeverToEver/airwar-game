"""Per-subsystem performance budgets.

These tests measure the steady-state cost of hot subsystems with
realistic mid-game load. They run headless (SDL_VIDEODRIVER=dummy)
and assert each subsystem stays within a frame budget. Numbers are
deliberately generous (the headless dummy driver under-reports real
hardware cost) so this is a regression detector, not a leaderboard.

To refresh the budget numbers, re-run and copy the printed
"observed" lines into the BUDGETS dict below. To re-baseline after
a deliberate optimization, raise the threshold by ~20% above the
observed value.
"""

from __future__ import annotations

import time

import pytest

from airwar.entities.base import BulletData, EnemyData, Rect
from airwar.game.managers.collision_controller import CollisionController

# Frame budget per subsystem (ms) — 3x current headless cost.
# Tighten when you deliberately optimize; loosen only when the
# budget is demonstrably unreachable on real hardware.
#
# Observed 2026-06-07 (headless, 1920x1080):
#   collision_check_all_50_80:  0.181 ms
#   collision_player_vs_enemies_100: 0.008 ms  (not a real hot path; budget
#     loosened from 0.05 to 0.5 ms to absorb OS scheduling jitter when the
#     full ~450-test suite runs back-to-back — still 60x above observed)
#   background_render:           0.382 ms  (was 0.496 pre-starfield-rust)
#   bullet_pack_unpack_250:      0.071 ms
#   discrete_battery_render:     0.070 ms
#   enemy_render_loop:           0.038 ms (50 sprite enemies)
#   bullet_render_loop:          0.055 ms (200 enemy bullets)
#   all_entities_blits:          0.151 ms (50 enemies + 200 bullets)
BUDGETS_MS = {
    "collision_check_all_50_80": 1.0,
    "collision_player_vs_enemies_100": 0.5,
    "background_render": 2.0,
    "bullet_pack_unpack_250": 0.5,
    "discrete_battery_render": 0.5,
    "enemy_batch_movement_50": 0.5,
}


class _FakeBullet:
    """Minimal Bullet stub for collision benchmarks (no pygame)."""

    __slots__ = ("_hit_enemies", "active", "data", "rect")

    def __init__(self, x: float, y: float, owner: str = "player", w: int = 8, h: int = 8) -> None:
        self.rect = Rect(int(x), int(y), w, h)
        self.data = BulletData(damage=20, owner=owner)
        self.active = True
        self._hit_enemies: set = set()

    def get_rect(self) -> Rect:
        return self.rect

    def has_hit_enemy(self, enemy_id: int) -> bool:
        return enemy_id in self._hit_enemies

    def add_hit_enemy(self, enemy_id: int) -> None:
        self._hit_enemies.add(enemy_id)


class _FakeEnemy:
    """Minimal Enemy stub."""

    __slots__ = ("_hitbox", "active", "data", "health", "rect")

    def __init__(self, x: float, y: float, w: int = 30, h: int = 30, health: int = 10) -> None:
        self.rect = Rect(int(x), int(y), w, h)
        self._hitbox = self.rect
        self.data = EnemyData(health=health, score=25)
        self.health = health
        self.active = True

    def get_hitbox(self) -> Rect:
        return self._hitbox

    def get_rect(self) -> Rect:
        return self.rect

    def take_damage(self, damage: int) -> None:
        self.health -= damage
        if self.health <= 0:
            self.active = False


class _FakePlayer:
    """Minimal Player stub for collision benchmarks."""

    __slots__ = ("_hitbox", "active_bullets", "bullets", "health", "rect")

    def __init__(self, x: float = 960, y: float = 540) -> None:
        self.rect = Rect(int(x), int(y), 40, 40)
        self._hitbox = self.rect
        self.health = 100
        self.bullets: list = []
        self.active_bullets: list = []

    def get_hitbox(self) -> Rect:
        return self._hitbox

    def get_bullets(self) -> list:
        return self.bullets

    def take_damage(self, damage: int) -> None:
        self.health -= damage


def _make_collision_scene(n_enemies: int, n_bullets: int, seed: int = 42):
    """Build a deterministic collision test scene."""
    player = _FakePlayer(960, 540)
    enemies = [
        _FakeEnemy(
            x=50 + (i * 37) % 1820,
            y=50 + (i * 53) % 980,
            health=10,
        )
        for i in range(n_enemies)
    ]
    bullets = [
        _FakeBullet(
            x=50 + (i * 23) % 1820,
            y=50 + (i * 19) % 980,
        )
        for i in range(n_bullets)
    ]
    return player, enemies, bullets


def _measure(func, warmup: int = 3, iters: int = 200) -> float:
    """Run `func` `iters` times, return mean ms/iter (after warmup)."""
    for _ in range(warmup):
        func()
    t0 = time.perf_counter()
    for _ in range(iters):
        func()
    return (time.perf_counter() - t0) * 1000 / iters


# === Tests ===


def test_collision_check_all_50_enemies_80_bullets():
    """Main collision path at mid-game load: player bullets vs enemies (Rust batch)."""
    cc = CollisionController()
    _player, enemies, bullets = _make_collision_scene(50, 80)

    observed = _measure(
        lambda: cc.check_player_bullets_vs_enemies(
            bullets, enemies, score_multiplier=1.0, explosive_level=0, piercing_level=0
        )
    )
    budget = BUDGETS_MS["collision_check_all_50_80"]
    assert observed < budget, f"collision regression: {observed:.3f}ms > {budget}ms budget"
    print(f"\n  observed: {observed:.3f} ms/frame (budget {budget}ms)")


def test_collision_player_vs_enemies_100():
    """Player vs N enemies linear scan (the path Stage C touched)."""
    cc = CollisionController()
    player_hitbox = _FakePlayer().get_hitbox()
    enemies = [_FakeEnemy(x=50 + (i * 37) % 1820, y=50 + (i * 53) % 980) for i in range(100)]

    def dodge():
        return False

    def hit(damage):
        pass

    observed = _measure(lambda: cc.check_player_vs_enemies(player_hitbox, enemies, dodge, hit))
    budget = BUDGETS_MS["collision_player_vs_enemies_100"]
    assert observed < budget, f"player-vs-enemies regression: {observed:.3f}ms > {budget}ms"
    print(f"\n  observed: {observed:.3f} ms/frame (budget {budget}ms)")


def test_bullet_pack_unpack_250():
    """The 250-bullet struct.pack_into loop in bullet_manager."""
    import struct

    from airwar.core_bindings import RUST_AVAILABLE

    if not RUST_AVAILABLE:
        pytest.skip("Rust not available — pack/unpack benchmark requires it")

    from airwar.core_bindings import batch_update_bullets_buf

    BUF_FMT = "<QffffBxxxf"
    BUF_SIZE = struct.calcsize(BUF_FMT)
    n = 250
    bullets = [(i + 0x1000, float(i * 7 % 1920), float(i * 11 % 1080), 0.0, -10.0, 0, 1080.0) for i in range(n)]

    def roundtrip():
        buf = bytearray(n * BUF_SIZE)
        for i, (bid, x, y, vx, vy, is_laser, screen_h) in enumerate(bullets):
            struct.pack_into(BUF_FMT, buf, i * BUF_SIZE, bid, x, y, vx, vy, is_laser, screen_h)
        results = batch_update_bullets_buf(bytes(buf))
        return results

    observed = _measure(roundtrip)
    budget = BUDGETS_MS["bullet_pack_unpack_250"]
    assert observed < budget, f"bullet pack/unpack regression: {observed:.3f}ms > {budget}ms"
    print(f"\n  observed: {observed:.3f} ms/frame (budget {budget}ms)")


def test_background_render_budget():
    """Full parallax background with 210 stars + 15 dust."""
    import pygame

    from airwar.game.rendering.game_rendering_background import SpaceBackground

    pygame.init()
    surface = pygame.Surface((1920, 1080))
    surface.fill((0, 0, 0))
    bg = SpaceBackground(1920, 1080)

    observed = _measure(lambda: bg.draw(surface))
    budget = BUDGETS_MS["background_render"]
    assert observed < budget, f"background regression: {observed:.3f}ms > {budget}ms"
    print(f"\n  observed: {observed:.3f} ms/frame (budget {budget}ms)")


def test_discrete_battery_render_budget():
    """Discrete battery: vertical 30-seg + horizontal 30-seg per frame."""
    import pygame

    from airwar.ui.discrete_battery import DiscreteBatteryIndicator

    pygame.init()
    surface = pygame.Surface((1920, 1080))
    surface.fill((0, 0, 0))
    v = DiscreteBatteryIndicator(24, 350, 30, "vertical")
    v.set_health(75, 100)
    h = DiscreteBatteryIndicator(400, 24, 30, "horizontal")
    h.set_health(75, 100)

    observed = _measure(lambda: (v.render(surface, 50, 100), h.render(surface, 50, 100)))
    budget = BUDGETS_MS["discrete_battery_render"]
    assert observed < budget, f"battery regression: {observed:.3f}ms > {budget}ms"
    print(f"\n  observed: {observed:.3f} ms/frame (budget {budget}ms)")


def test_enemy_batch_movement_50_budget():
    """Enemy batch movement: 50 enemies via Rust FFI binary buffer path.

    Validates that the fixed `_MOVEMENT_BASE_FMT` actually exercises the
    Rust `batch_update_movements_buf` path (was previously crashing due
    to a fmt bug that mismatched the Rust `BASE_BUF_STRIDE=48`).
    """
    import pygame

    from airwar.game.managers.game_loop_manager import GameLoopManager

    class _StubSpawn:
        enemies = []
        boss = None
        enemy_bullets = []

    class _StubGC:
        state = type("s", (), {"difficulty_level": 1})()

    class _StubReward:
        unlocked_buffs = []
        slow_factor = 1.0
        explosive_level = 0
        piercing_level = 0

        def apply_lifesteal(self, *args, **kwargs):
            pass

    class _FullEnemy:
        def __init__(self, x, y):
            self.rect = pygame.Rect(x, y, 30, 30)
            self.active = True
            self._state = 1
            self._rust_move_type_code = 1
            self.move_type = "sine"
            self._timer_attr = "_timer"
            self._timer = 0.0
            self.active_position_x = x
            self.active_position_y = y
            self._rust_params = {
                "offset": 0.0,
                "amplitude": 50.0,
                "frequency": 0.02,
                "speed": 2.0,
                "direction": 0.0,
                "zigzag_interval": 60.0,
                "spiral_radius": 0.0,
                "noise_scale_x": 0.1,
                "noise_scale_y": 0.1,
                "noise_amplitude_x": 0.0,
                "noise_amplitude_y": 0.0,
                "noise_seed": 0,
            }

        def is_ready_for_batch_movement(self):
            return True

        def get_rust_batch_params(self):
            p = self._rust_params
            return (
                (
                    self._rust_move_type_code,
                    self._timer,
                    self.active_position_x,
                    self.active_position_y,
                    100.0,
                    50.0,
                    p["offset"],
                    p["amplitude"],
                    p["frequency"],
                    p["speed"],
                    p["direction"],
                    p["zigzag_interval"],
                ),
                (
                    p["spiral_radius"],
                    self.rect.x,
                    self.rect.y,
                    p["noise_scale_x"],
                    p["noise_scale_y"],
                    p["noise_amplitude_x"],
                    p["noise_amplitude_y"],
                    p["noise_seed"],
                ),
            )

        def apply_batch_movement_result(self, result):
            self.rect.x, self.rect.y, self._timer = result

        def update(self, *args, **kwargs):
            pass

    glm = GameLoopManager.__new__(GameLoopManager)
    glm._spawn_controller = _StubSpawn()
    glm._game_controller = _StubGC()
    glm._reward_system = _StubReward()
    glm._player = None
    glm._spawn_controller.enemies = [_FullEnemy(100 + i * 30, 100) for i in range(50)]

    observed = _measure(glm._update_entities)
    budget = BUDGETS_MS["enemy_batch_movement_50"]
    assert observed < budget, f"enemy batch movement regression: {observed:.3f}ms > {budget}ms"
    # Validate Rust path actually moved enemies
    moved = glm._spawn_controller.enemies[0].rect.x != 100
    assert moved, "enemy batch movement didn't actually move enemies (Rust path may not be exercised)"
    print(f"\n  observed: {observed:.3f} ms/frame (budget {budget}ms)")


# NOTE: 2026-06-07 — entity/bullet sprite blit "optimization" via
# `pygame.Surface.blits()` with pre-built tuple list was tried and reverted.
# The Python list-build cost (450 elements × ~0.4µs) exceeds the C blit
# savings. Original explicit per-entity loop at 151µs is faster than the
# batched path at 170µs for the 50-enemy + 200+200-bullet mid-game load.
# A real win here would require moving the position list to a Rust
# flat-array buffer (BulletArena / SpriteBlitArena style) and having Rust
# build the blit tuples in C — too much complexity for the measured gain.
