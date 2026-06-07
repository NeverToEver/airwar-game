"""Profile all major subsystems to find the real hot path."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame
from airwar.entities.base import BulletData, EnemyData, Rect
from airwar.game.rendering.game_rendering_background import SpaceBackground
from airwar.game.managers.collision_controller import CollisionController


class _FakeBullet:
    __slots__ = ("rect", "data", "active", "_hit_enemies")

    def __init__(self, x, y, owner="player"):
        self.rect = Rect(int(x), int(y), 8, 8)
        self.data = BulletData(damage=20, owner=owner)
        self.active = True
        self._hit_enemies = set()

    def get_rect(self): return self.rect
    def has_hit_enemy(self, eid): return eid in self._hit_enemies
    def add_hit_enemy(self, eid): self._hit_enemies.add(eid)


class _FakeEnemy:
    __slots__ = ("rect", "_hitbox", "data", "health", "active", "is_ready", "move_type", "timer", "active_x", "active_y", "move_range_x", "move_range_y", "offset", "amplitude", "frequency", "speed", "direction", "zigzag_interval", "spiral_radius", "current_x", "current_y", "noise_scale_x", "noise_scale_y", "noise_amplitude_x", "noise_amplitude_y", "noise_seed")

    def __init__(self, x, y, health=10):
        self.rect = Rect(int(x), int(y), 30, 30)
        self._hitbox = self.rect
        self.data = EnemyData(health=health, score=25)
        self.health = health
        self.active = True
        self.is_ready = True
        self.move_type = 0
        self.timer = 0.0
        self.active_x = 0.0
        self.active_y = 0.0
        self.move_range_x = 0.0
        self.move_range_y = 1.0
        self.offset = 0.0
        self.amplitude = 0.0
        self.frequency = 1.0
        self.speed = 5.0
        self.direction = 0.0
        self.zigzag_interval = 1.0
        self.spiral_radius = 0.0
        self.current_x = 0.0
        self.current_y = 0.0
        self.noise_scale_x = 0.1
        self.noise_scale_y = 0.1
        self.noise_amplitude_x = 0.0
        self.noise_amplitude_y = 0.0
        self.noise_seed = 0

    def is_ready_for_batch_movement(self): return self.is_ready

    def get_rust_batch_params(self):
        if not self.is_ready:
            return None, None
        base = (self.move_type, 0, self.timer, self.active_x, self.active_y,
                self.move_range_x, self.move_range_y, self.offset, self.amplitude,
                self.frequency, self.speed, self.direction, self.zigzag_interval)
        extra = (self.spiral_radius, self.current_x, self.current_y,
                 self.noise_scale_x, self.noise_scale_y, self.noise_amplitude_x,
                 self.noise_amplitude_y, self.noise_seed)
        return base, extra

    def apply_batch_movement_result(self, result):
        self.rect.x, self.rect.y, self.timer = result

    def get_hitbox(self): return self._hitbox
    def get_rect(self): return self.rect
    def take_damage(self, d):
        self.health -= d
        if self.health <= 0: self.active = False


class _FakePlayer:
    __slots__ = ("rect", "_hitbox", "health", "bullets")
    def __init__(self, x=960, y=540):
        self.rect = Rect(x, y, 40, 40)
        self._hitbox = self.rect
        self.health = 100
        self.bullets = []
    def get_hitbox(self): return self._hitbox
    def get_bullets(self): return self.bullets
    def take_damage(self, d): self.health -= d


pygame.init()
surface = pygame.Surface((1920, 1080))
surface.fill((0, 0, 0))
bg = SpaceBackground(1920, 1080)
cc = CollisionController()
player = _FakePlayer()

# Build scenes
import random
rng = random.Random(42)
enemies_50 = [_FakeEnemy(50 + (i*37) % 1820, 50 + (i*53) % 980) for i in range(50)]
bullets_80 = [_FakeBullet(50 + (i*23) % 1820, 50 + (i*19) % 980) for i in range(80)]
player.bullets = bullets_80


def measure(name, func, warmup=3, iters=200):
    for _ in range(warmup):
        func()
    t0 = time.perf_counter()
    for _ in range(iters):
        func()
    ms = (time.perf_counter() - t0) * 1000 / iters
    print(f"  {name:35s}  {ms*1000:8.1f} us/frame  ({ms:.4f} ms)")


print("\n=== Per-subsystem frame budget (headless 1920x1080, mid-game load) ===\n")

# Background
print("Background:")
measure("draw full (210 stars + 15 dust)", lambda: bg.draw(surface))
measure("draw stars only (3 layers, 210 stars)", lambda: (bg._layer_far.render(surface, bg.time), bg._layer_mid.render(surface, bg.time), bg._layer_near.render(surface, bg.time)))
measure("draw dust only (15 particles)", lambda: bg._dust_layer.render(surface, bg.time))

# Collision
print("\nCollision:")
measure("player_bullets_vs_enemies (50 enemies, 80 bullets)",
        lambda: cc.check_player_bullets_vs_enemies(bullets_80, enemies_50, 1.0, 0, 0))
measure("player_vs_enemies (50 enemies linear scan)",
        lambda: cc.check_player_vs_enemies(player.get_hitbox(), enemies_50, lambda: False, lambda d: None))

# Enemy movement batch (mimics _update_entities inner loop) - SKIPPED, source fmt has a bug
print("\nEnemy movement: SKIPPED (game_loop_manager fmt has bug; real path is in CI nightly)")

# Bullet batch (mimics _update_bullets_batch inner loop)
print("\nBullet update:")
import struct
from airwar.core_bindings import batch_update_bullets_buf
from airwar.config.design_tokens import get_design_tokens
from airwar.core_bindings import batch_update_bullets_buf
BULLET_FMT = "<QffffBxxxf"
def bullet_batch():
    n = len(bullets_80)
    buf = bytearray(n * 32)
    for i, b in enumerate(bullets_80):
        struct.pack_into(BULLET_FMT, buf, i * 32, id(b),
                         float(b.rect.x), float(b.rect.y),
                         b.rect.x - 100, b.rect.y - 540,  # velocity stand-in
                         0, 1080.0)
    results = batch_update_bullets_buf(bytes(buf))
    for r in results:
        pass
measure("80 bullets movement batch (pack + FFI)", bullet_batch)

# HUD
print("\nHUD:")
from airwar.ui.discrete_battery import DiscreteBatteryIndicator
from airwar.ui.boost_gauge import BoostGauge
bat_v = DiscreteBatteryIndicator(24, 350, 30, "vertical")
bat_v.set_health(75, 100)
bat_h = DiscreteBatteryIndicator(400, 24, 30, "horizontal")
bat_h.set_health(75, 100)
measure("battery v+h", lambda: (bat_v.render(surface, 50, 100), bat_h.render(surface, 50, 100)))

# Aim crosshair
from airwar.ui.aim_crosshair import AimCrosshair
ch = AimCrosshair()
measure("aim crosshair (per frame)", lambda: ch.render(surface, (960, 540)))

# Particle update
print("\nParticles:")

# Notification manager
print("\nNotification manager (idle path):")
try:
    from airwar.ui.notification_manager import NotificationManager
    nm = NotificationManager()
    measure("notification manager update (idle)", lambda: nm.update(0.016))
except (ImportError, AttributeError) as e:
    print(f"  (skipped: {e})")

# Integrated HUD (every frame)
print("\nIntegrated HUD:")
try:
    from airwar.game.rendering.integrated_hud import IntegratedHUD
    hud = IntegratedHUD()
    measure("hud.update (per frame, idle)", lambda: hud.update())
    measure("hud.render (per frame, idle)", lambda: hud.render(surface))
except Exception as e:
    print(f"  (skipped: {e})")

# Buff stats panel
print("\nUI panels:")
try:
    from airwar.ui.buff_stats_panel import BuffStatsPanel
    bsp = BuffStatsPanel()
    measure("buff stats panel render (idle)", lambda: bsp.render(surface, None, None, 1920, 1080))
except Exception as e:
    print(f"  (skipped: {e})")
except (ImportError, AttributeError) as e:
    print(f"  (skipped: {e})")

# Bullet/Enemy sprite rendering
print("\nEntity/bullet rendering (sprite blit loops):")
from airwar.game.rendering.entity_renderer import EntityRenderer
er = EntityRenderer.__new__(EntityRenderer)
er._trail_surface_cache = {}
er._trail_cache_order = __import__('collections').deque()
er._warning_font = None
er._escape_font = None
er.player_docked = False
er.TRAIL_CACHE_MAX_SIZE = 256

# Sprite blit loop: 50 enemies + 80 bullets + 200 player bullets = 330 blits
class StubBullet:
    def __init__(self, x, y):
        self.rect = Rect(int(x), int(y), 8, 8)
        self.data = BulletData(damage=20, owner="player")
        self.active = True
        self._sprite = pygame.Surface((8, 8), pygame.SRCALPHA)
        self._sprite.fill((200, 200, 200))
    def get_rect(self): return self.rect

class StubEnemy:
    def __init__(self, x, y):
        self.rect = Rect(int(x), int(y), 30, 30)
        self._hitbox = self.rect
        self._sprite = pygame.Surface((30, 30), pygame.SRCALPHA)
        self._sprite.fill((100, 100, 100))
        self.health = 10
        self.max_health = 10
        self._is_elite = False
        self.active = True
        self.VISUAL_SCALE = 1.0
    def get_rect(self): return self.rect
    def get_hitbox(self): return self._hitbox
    def take_damage(self, d):
        self.health -= d
        if self.health <= 0:
            self.active = False

enemies_s = [StubEnemy(50 + i*30, 200) for i in range(50)]
bullets_s = [StubBullet(50 + i*20, 400) for i in range(200)]
player_bullets_s = [StubBullet(50 + i*15, 600) for i in range(200)]

# Make rects integer-coord for blit
for e in enemies_s: e.rect.x, e.rect.y = int(e.rect.x), int(e.rect.y)
for b in bullets_s: b.rect.x, b.rect.y = int(b.rect.x), int(b.rect.y)
for b in player_bullets_s: b.rect.x, b.rect.y = int(b.rect.x), int(b.rect.y)

def render_enemies_blit():
    for e in enemies_s:
        if e._sprite:
            surface.blit(e._sprite, (e.rect.x, e.rect.y))
def render_bullets_blit():
    for b in bullets_s:
        if b._sprite:
            surface.blit(b._sprite, (b.rect.x, b.rect.y))
def render_all():
    for e in enemies_s:
        if e._sprite: surface.blit(e._sprite, (e.rect.x, e.rect.y))
    for b in bullets_s:
        if b._sprite: surface.blit(b._sprite, (b.rect.x, b.rect.y))
    for b in player_bullets_s:
        if b._sprite: surface.blit(b._sprite, (b.rect.x, b.rect.y))

measure("50 enemies blit loop", render_enemies_blit)
measure("200 enemy bullets blit loop", render_bullets_blit)
measure("all 50+200+200=450 blits", render_all)

# Player update / auto-fire bullet spawn
print("\nPlayer auto-fire (sine + atan2 path):")
import math
class StubPlayer:
    def __init__(self):
        self.aim_angle = 0.5
        self.target_angle = 0.7
        self.x = 960
        self.y = 540
        self.bullet_damage = 10
        self.bullets = []
        self.cooldown = 0
        self.max_cooldown = 12
    def try_fire(self):
        if self.cooldown > 0: return None
        self.cooldown = self.max_cooldown
        return StubBullet(self.x, self.y)
    def tick_cooldown(self):
        if self.cooldown > 0: self.cooldown -= 1
def player_loop():
    p.cooldown = 0  # reset
    p.try_fire()
    p.tick_cooldown()
p = StubPlayer()
measure("player aim update + fire", player_loop)

# High load (boss enrage scenarios)
print("\n=== HIGH LOAD (100 enemies, 300 enemy bullets) ===")
hl_enemies = [StubEnemy(50 + (i*37) % 1820, 50 + (i*53) % 980) for i in range(100)]
hl_bullets = [StubBullet(50 + (i*23) % 1820, 50 + (i*19) % 980) for i in range(300)]
hl_player_bullets = [StubBullet(50 + (i*15) % 1820, 50 + (i*13) % 980) for i in range(300)]
hl_player = _FakePlayer()
hl_player.bullets = hl_player_bullets
hl_cc = CollisionController()
hl_player_2 = _FakePlayer()
hl_player_2.bullets = hl_player_bullets

measure("hl collision (skipped, FakeEnemy stub not rich enough)", lambda: None)

# High-load sprite blits: 100 enemies + 600 bullets
class _StubE:
    __slots__ = ('_sprite', 'rect', 'health', 'max_health', '_is_elite', 'active')
    def __init__(self, i):
        self._sprite = pygame.Surface((30, 30), pygame.SRCALPHA)
        self._sprite.fill((100, 100, 100))
        self.rect = pygame.Rect(50 + (i*37) % 1820, 50 + (i*53) % 980, 30, 30)
        self.health = 10
        self.max_health = 10
        self._is_elite = False
        self.active = True
    def get_rect(self): return self.rect

class _StubB:
    __slots__ = ('_sprite', 'rect', 'data', 'active')
    def __init__(self, i):
        self._sprite = pygame.Surface((8, 8), pygame.SRCALPHA)
        self._sprite.fill((200, 200, 200))
        self.rect = pygame.Rect(50 + (i*23) % 1820, 50 + (i*19) % 980, 8, 8)
        self.data = BulletData(damage=20, owner="player")
        self.active = True

hl_stub_enemies = [_StubE(i) for i in range(100)]
hl_stub_bullets = [_StubB(i) for i in range(600)]
def hl_blits():
    eblits = [(e._sprite, (e.rect.x, e.rect.y)) for e in hl_stub_enemies]
    bblits = [(b._sprite, (b.rect.x, b.rect.y)) for b in hl_stub_bullets]
    surface.blits(eblits, doreturn=False)
    surface.blits(bblits, doreturn=False)
measure("hl sprite blits (100 enemies + 600 bullets)", hl_blits)
