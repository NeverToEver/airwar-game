"""Collision detection between entities using spatial hashing."""
from dataclasses import dataclass, field
from typing import List, Tuple, Callable, Optional, TYPE_CHECKING
import pygame

from ..constants import GAME_CONSTANTS
from ...config import EXPLOSION_RADIUS

if TYPE_CHECKING:
    from ...entities.player import Player
    from ...entities.enemy import Enemy
    from ...entities.boss import Boss
    from ...entities.bullet import Bullet, EnemyBullet

# Try to import Rust collision functions
try:
    from airwar.core_bindings import (
        spatial_hash_collide,
        spatial_hash_collide_single,
        batch_collide_bullets_vs_entities,
        PersistentSpatialHash,
        RUST_AVAILABLE,
    )
except ImportError:
    spatial_hash_collide = None
    spatial_hash_collide_single = None
    batch_collide_bullets_vs_entities = None
    PersistentSpatialHash = None
    RUST_AVAILABLE = False


@dataclass
class CollisionResult:
    """Collision result dataclass — score gained and enemies killed."""
    player_damaged: bool = False
    enemies_killed: int = 0
    score_gained: int = 0
    boss_damaged: bool = False
    boss_killed: bool = False


@dataclass
class CollisionEvent:
    """Collision event dataclass — callback registration for collision handling."""
    type: str
    source: any = None
    target: any = None
    damage: int = 0
    score: int = 0


class CollisionController:
    """Collision controller — detects and handles entity collisions.
    
        Supports spatial hashing (Rust-accelerated when available) for efficient
        collision detection between player bullets, enemy bullets, enemies,
        bosses, and the player.
    
        Attributes:
            _events: Registered collision event callbacks.
            _use_rust: Whether Rust spatial hash acceleration is available.
        """
    def __init__(self):
        self._events: List[CollisionEvent] = []
        self._explosion_callback: Optional[Callable[[float, float, int], None]] = None
        # Spatial hash grid for collision optimization
        self._grid_cells = {}
        self._grid_cell_size = 100
        self._use_rust = RUST_AVAILABLE
        # Persistent spatial hash for incremental collision detection
        self._persistent_hash = None
        if self._use_rust and PersistentSpatialHash is not None:
            self._persistent_hash = PersistentSpatialHash(self._grid_cell_size)
        self._previous_enemy_ids: set = set()

    def _clear_grid(self) -> None:
        """Clear the spatial hash grid."""
        self._grid_cells.clear()

    def _get_rect_bounds(self, rect) -> Tuple[int, int, int, int]:
        """Get (left, right, top, bottom) from rect, supporting both pygame.Rect and MockRect."""
        if hasattr(rect, 'left'):
            return rect.left, rect.right, rect.top, rect.bottom
        else:
            # MockRect uses centerx, centery, width, height
            left = rect.centerx - rect.width // 2
            top = rect.centery - rect.height // 2
            return left, left + rect.width, top, top + rect.height

    def _get_cell_key(self, x: int, y: int) -> Tuple[int, int]:
        """Get grid cell key for a position."""
        return (x // self._grid_cell_size, y // self._grid_cell_size)

    def _add_to_grid(self, entity, rect) -> None:
        """Add entity to spatial hash grid based on its rect."""
        left, right, top, bottom = self._get_rect_bounds(rect)
        min_x = int(left // self._grid_cell_size)
        max_x = int(right // self._grid_cell_size)
        min_y = int(top // self._grid_cell_size)
        max_y = int(bottom // self._grid_cell_size)

        for gx in range(min_x, max_x + 1):
            for gy in range(min_y, max_y + 1):
                key = (gx, gy)
                if key not in self._grid_cells:
                    self._grid_cells[key] = []
                self._grid_cells[key].append(entity)

    def _get_potential_collisions(self, rect) -> set:
        """Get entities that might collide with the given rect."""
        left, right, top, bottom = self._get_rect_bounds(rect)
        min_x = int(left // self._grid_cell_size)
        max_x = int(right // self._grid_cell_size)
        min_y = int(top // self._grid_cell_size)
        max_y = int(bottom // self._grid_cell_size)

        potential = set()
        for gx in range(min_x, max_x + 1):
            for gy in range(min_y, max_y + 1):
                key = (gx, gy)
                if key in self._grid_cells:
                    potential.update(self._grid_cells[key])
        return potential

    @property
    def events(self) -> List[CollisionEvent]:
        return self._events.copy()

    def clear_events(self) -> None:
        self._events.clear()

    def set_explosion_callback(
        self,
        callback: Callable[[float, float, int], None]
    ) -> None:
        """Set explosion callback function

        Args:
            callback: Callback function with signature (x, y, radius) -> None
        """
        self._explosion_callback = callback
    
    def check_all_collisions(
        self,
        player: 'Player',
        enemies: List['Enemy'],
        boss: Optional['Boss'],
        enemy_bullets: List['EnemyBullet'],
        reward_system: any,
        explosive_level: int = 0,
        piercing_level: int = 0,
        player_invincible: bool = False,
        score_multiplier: int = 1,
        on_enemy_killed: Callable[[int], None] = None,
        on_boss_killed: Callable[[int], None] = None,
        on_boss_hit: Callable[[int], None] = None,
        on_player_hit: Callable[[int, 'Player'], None] = None,
        on_lifesteal: Callable = None,
        on_clear_bullets: Callable = None,
    ) -> None:
        self._events.clear()

        # Build spatial hash grid for enemies
        self._clear_grid()
        for enemy in enemies:
            if enemy.active:
                self._add_to_grid(enemy, enemy.get_hitbox())

        score_gained, enemies_killed = self.check_player_bullets_vs_enemies(
            player.get_bullets(),
            enemies,
            score_multiplier,
            explosive_level,
            piercing_level,
        )
        
        if enemies_killed > 0 and on_enemy_killed:
            self._events.append(CollisionEvent(type='enemy_killed', score=score_gained))
            on_enemy_killed(score_gained)
        
        if not player_invincible and self.check_enemy_bullets_vs_player(
            enemy_bullets,
            player,
            lambda d: reward_system.calculate_damage_taken(d),
            on_player_hit
        ):
            self._events.append(CollisionEvent(type='player_hit'))
        
        if not player_invincible and self.check_player_vs_enemies(
            player.get_hitbox(),
            enemies,
            lambda: reward_system.try_dodge(),
            lambda d: (
                on_player_hit(d, player),
                on_clear_bullets() if on_clear_bullets else None
            )
        ):
            self._events.append(CollisionEvent(type='player_hit'))
        
        if boss:
            boss_score, boss_killed = self.check_player_bullets_vs_boss(
                player.get_bullets(),
                boss,
                reward_system.piercing_level
            )
            
            if boss_score > 0:
                self._events.append(CollisionEvent(type='boss_hit', score=boss_score))
                if on_boss_hit:
                    on_boss_hit(boss_score)
            
            if boss_killed:
                self._events.append(CollisionEvent(type='boss_killed', score=boss_score))
                if on_boss_killed:
                    on_boss_killed(boss_score)
            
            if not player_invincible and self.check_boss_vs_player(
                boss,
                player,
                lambda d: reward_system.calculate_damage_taken(d),
                lambda d, p: (
                    on_player_hit(d, p),
                    on_clear_bullets() if on_clear_bullets else None
                )
            ):
                self._events.append(CollisionEvent(type='player_hit'))

    def check_player_bullets_vs_enemies(
        self,
        player_bullets: List['Bullet'],
        enemies: List['Enemy'],
        score_multiplier: int,
        explosive_level: int,
        piercing_level: int = 0,
    ) -> Tuple[int, int]:
        score_gained = 0
        enemies_killed = 0

        # Use Rust batch collision — single FFI call for all bullet-enemy pairs
        if self._use_rust and batch_collide_bullets_vs_entities is not None:
            bullet_data = []
            bullet_map = {}
            for i, bullet in enumerate(player_bullets):
                if bullet.active:
                    r = bullet.rect
                    bullet_data.append((i, float(r.centerx), float(r.centery),
                                       float(max(r.width, r.height)) / 2.0))
                    bullet_map[i] = bullet

            enemy_data = []
            enemy_map = {}
            for i, enemy in enumerate(enemies):
                if enemy.active:
                    eid = -i - 1
                    hb = enemy.get_hitbox()
                    enemy_data.append((eid, float(hb.centerx), float(hb.centery),
                                      float(max(hb.width, hb.height)) / 2.0))
                    enemy_map[eid] = enemy

            if bullet_data and enemy_data:
                hits = batch_collide_bullets_vs_entities(
                    bullet_data, enemy_data, self._grid_cell_size)

                for bid, eid in hits:
                    if bid not in bullet_map or eid not in enemy_map:
                        continue
                    bullet = bullet_map[bid]
                    enemy = enemy_map[eid]
                    if not bullet.active or not enemy.active:
                        continue
                    enemy.take_damage(bullet.data.damage)
                    if explosive_level > 0:
                        self._handle_explosive_damage(bullet, enemies, explosive_level)
                    if not enemy.active:
                        enemies_killed += 1
                        score_gained += enemy.data.score * score_multiplier
                    if bullet.data.owner == "player" and piercing_level <= 0:
                        bullet.active = False
            return score_gained, enemies_killed

        # Fallback to Python implementation
        use_spatial_hash = bool(self._grid_cells)

        for bullet in player_bullets:
            if not bullet.active:
                continue

            bullet_rect = bullet.rect

            if use_spatial_hash:
                potential_enemies = self._get_potential_collisions(bullet_rect)
            else:
                potential_enemies = [e for e in enemies if e.active]

            for enemy in potential_enemies:
                if not enemy.active:
                    continue

                if bullet_rect.colliderect(enemy.get_hitbox()):
                    damage = bullet.data.damage
                    enemy.take_damage(damage)

                    if explosive_level > 0:
                        self._handle_explosive_damage(bullet, enemies, explosive_level)

                    if not enemy.active:
                        enemies_killed += 1
                        score_gained += enemy.data.score * score_multiplier

                    if bullet.data.owner == "player":
                        if piercing_level <= 0:
                            bullet.active = False
                    break

        return score_gained, enemies_killed

    def _handle_explosive_damage(
        self,
        bullet: 'Bullet',
        enemies: List['Enemy'],
        explosive_level: int
    ) -> None:
        bullet_x = bullet.rect.centerx
        bullet_y = bullet.rect.centery
        explosion_radius_sq = (EXPLOSION_RADIUS * explosive_level) ** 2
        explosion_radius = EXPLOSION_RADIUS * explosive_level

        explosion_triggered = False

        for enemy in enemies:
            if enemy.active:
                dx = bullet_x - enemy.rect.centerx
                dy = bullet_y - enemy.rect.centery
                distance_sq = dx * dx + dy * dy

                if distance_sq <= explosion_radius_sq:
                    explosion_damage = GAME_CONSTANTS.DAMAGE.EXPLOSIVE_DAMAGE * explosive_level
                    enemy.take_damage(explosion_damage)

                    if not explosion_triggered and self._explosion_callback:
                        self._explosion_callback(bullet_x, bullet_y, explosion_radius)
                        explosion_triggered = True

    def check_player_bullets_vs_boss(
        self,
        player_bullets: List['Bullet'],
        boss: 'Boss',
        piercing_level: int
    ) -> Tuple[int, bool]:
        if not boss or not boss.active:
            return 0, False

        score_gained = 0
        boss_killed = False

        for bullet in player_bullets:
            if bullet.active and bullet.get_rect().colliderect(boss.get_rect()):
                score_reward = boss.take_damage(bullet.data.damage)
                if score_reward > 0:
                    score_gained += score_reward
                    boss_killed = True
                if piercing_level <= 0:
                    bullet.active = False

        return score_gained, boss_killed

    def check_player_vs_enemies(
        self,
        player_hitbox,
        enemies: List['Enemy'],
        try_dodge_func: Callable,
        on_player_hit_func: Callable
    ) -> bool:
        for enemy in enemies:
            if enemy.active and player_hitbox.colliderect(enemy.get_rect()):
                if not try_dodge_func():
                    on_player_hit_func(GAME_CONSTANTS.DAMAGE.ENEMY_COLLISION_DAMAGE)
                    return True

        return False

    def check_enemy_bullets_vs_player(
        self,
        enemy_bullets: List['Bullet'],
        player,
        calculate_damage_func: Callable,
        on_player_hit_func: Callable
    ) -> bool:
        player_hitbox = player.get_hitbox()

        for eb in enemy_bullets:
            if eb.active and eb.rect.colliderect(player_hitbox):
                damage = calculate_damage_func(eb.data.damage)
                on_player_hit_func(damage, player)
                return True

        return False

    def check_boss_vs_player(
        self,
        boss: 'Boss',
        player,
        calculate_damage_func: Callable,
        on_player_hit_func: Callable
    ) -> bool:
        if boss and boss.active and not boss.is_entering():
            player_hitbox = player.get_hitbox()
            if boss.get_rect().colliderect(player_hitbox):
                damage = calculate_damage_func(GAME_CONSTANTS.DAMAGE.BOSS_COLLISION_DAMAGE)
                on_player_hit_func(damage, player)
                return True

        return False
