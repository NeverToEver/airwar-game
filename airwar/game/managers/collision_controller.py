"""Collision detection between entities using spatial hashing."""
from dataclasses import dataclass
from typing import List, Tuple, Callable, Optional, TYPE_CHECKING

from ..constants import GAME_CONSTANTS

if TYPE_CHECKING:
    from ...entities.player import Player
    from ...entities.enemy import Enemy
    from ...entities.enemy import Boss
    from ...entities.bullet import Bullet, EnemyBullet

# Try to import Rust collision functions
try:
    from airwar.core_bindings import (
        batch_collide_bullets_vs_entities,
        PersistentSpatialHash,
        RUST_AVAILABLE,
    )
except ImportError:
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


@dataclass(frozen=True)
class _QueryRect:
    left: float
    right: float
    top: float
    bottom: float


class CollisionController:
    """Collision controller — detects and handles entity collisions.

        Supports spatial hashing (Rust-accelerated when available) for efficient
        collision detection between player bullets, enemy bullets, enemies,
        bosses, and the player.

        Attributes:
            _events: Registered collision event callbacks.
            _use_rust: Whether Rust spatial hash acceleration is available.
        """
    GRID_CELL_SIZE = 100

    def __init__(self):
        self._events: List[CollisionEvent] = []
        self._explosion_callback: Optional[Callable[[float, float, int], None]] = None
        # Spatial hash grid for collision optimization
        self._grid_cells = {}
        self._enemy_grid_cells = {}
        self._grid_cell_size = self.GRID_CELL_SIZE
        self._use_rust = RUST_AVAILABLE
        # Persistent spatial hash for incremental collision detection
        self._persistent_hash = None
        if self._use_rust and PersistentSpatialHash is not None:
            self._persistent_hash = PersistentSpatialHash(self._grid_cell_size)
        self._previous_enemy_ids: set = set()
        # Reusable temp containers for Rust batch collision
        self._bullet_data: List[tuple] = []
        self._bullet_map: dict = {}
        self._enemy_data: List[tuple] = []
        self._enemy_map: dict = {}

    def _clear_grid(self) -> None:
        """Clear the spatial hash grid."""
        self._grid_cells.clear()
        self._enemy_grid_cells.clear()

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
        self._add_entity_to_cells(self._grid_cells, entity, rect)

    def _add_to_enemy_grid(self, entity, rect) -> None:
        """Add enemy to the reusable enemy spatial grid."""
        self._add_entity_to_cells(self._enemy_grid_cells, entity, rect)

    def _add_entity_to_cells(self, cells: dict, entity, rect) -> None:
        left, right, top, bottom = self._get_rect_bounds(rect)
        min_x = int(left // self._grid_cell_size)
        max_x = int(right // self._grid_cell_size)
        min_y = int(top // self._grid_cell_size)
        max_y = int(bottom // self._grid_cell_size)

        for gx in range(min_x, max_x + 1):
            for gy in range(min_y, max_y + 1):
                key = (gx, gy)
                if key not in cells:
                    cells[key] = []
                cells[key].append(entity)

    def _get_potential_collisions(self, rect) -> list:
        """Get entities that might collide with the given rect."""
        return self._get_entities_in_cells(self._grid_cells, rect)

    def _get_potential_explosion_targets(self, x: float, y: float, radius: float, enemies: List['Enemy']) -> list:
        if not self._enemy_grid_cells:
            return [enemy for enemy in enemies if enemy.active]
        rect = self._make_query_rect(x, y, radius)
        return self._get_entities_in_cells(self._enemy_grid_cells, rect)

    def _get_potential_boss_bullets(self, player_bullets: List['Bullet'], boss_hitbox, active_count: int) -> list['Bullet']:
        if active_count < 32:
            return [bullet for bullet in player_bullets if bullet.active]

        grid: dict = {}
        for bullet in player_bullets:
            if bullet.active:
                self._add_entity_to_cells(grid, bullet, bullet.get_rect())
        return list(self._get_entities_in_cells(grid, boss_hitbox))

    def _get_entities_in_cells(self, cells: dict, rect) -> list:
        left, right, top, bottom = self._get_rect_bounds(rect)
        min_x = int(left // self._grid_cell_size)
        max_x = int(right // self._grid_cell_size)
        min_y = int(top // self._grid_cell_size)
        max_y = int(bottom // self._grid_cell_size)

        potential = []
        seen_ids = set()
        for gx in range(min_x, max_x + 1):
            for gy in range(min_y, max_y + 1):
                key = (gx, gy)
                if key in cells:
                    for entity in cells[key]:
                        entity_id = id(entity)
                        if entity_id not in seen_ids:
                            potential.append(entity)
                            seen_ids.add(entity_id)
        return potential

    @staticmethod
    def _make_query_rect(center_x: float, center_y: float, radius: float):
        return _QueryRect(
            left=center_x - radius,
            right=center_x + radius,
            top=center_y - radius,
            bottom=center_y + radius,
        )

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
        score_multiplier: float = 1.0,
        on_enemy_killed: Callable[[int], None] = None,
        on_boss_killed: Callable[[int], None] = None,
        on_boss_hit: Callable[[int], None] = None,
        on_player_hit: Callable[[int, 'Player'], None] = None,
        on_lifesteal: Callable = None,
        on_clear_bullets: Callable = None,
    ) -> None:
        self._events.clear()
        player_hit_handler = self._make_player_hit_handler(
            player,
            on_player_hit,
            on_clear_bullets,
        )

        # The Rust collision path builds its own spatial data from batch input.
        # Keep the Python grid only for the fallback path to avoid duplicate
        # per-frame hitbox work when the extension is available.
        self._clear_grid()
        if self._uses_rust_batch_collision():
            for enemy in enemies:
                if enemy.active:
                    self._add_to_enemy_grid(enemy, enemy.get_hitbox())
        else:
            for enemy in enemies:
                if enemy.active:
                    self._add_to_grid(enemy, enemy.get_hitbox())
                    self._add_to_enemy_grid(enemy, enemy.get_hitbox())

        score_gained, enemies_killed = self.check_player_bullets_vs_enemies(
            player.get_bullets(),
            enemies,
            score_multiplier,
            explosive_level,
            piercing_level,
        )
        
        if enemies_killed > 0:
            self._events.append(CollisionEvent(type='enemy_killed', score=score_gained))
            if on_enemy_killed:
                on_enemy_killed(score_gained)
            if on_lifesteal:
                for _ in range(enemies_killed):
                    on_lifesteal(player, score_gained)
        
        if not player_invincible and self.check_enemy_bullets_vs_player(
            enemy_bullets,
            player,
            lambda d: reward_system.calculate_damage_taken(d),
            player_hit_handler
        ):
            self._events.append(CollisionEvent(type='player_hit'))
        
        if not player_invincible and self.check_player_vs_enemies(
            player.get_hitbox(),
            enemies,
            lambda: reward_system.try_dodge(),
            player_hit_handler
        ):
            self._events.append(CollisionEvent(type='player_hit'))
        
        if boss:
            boss_score, boss_killed = self.check_player_bullets_vs_boss(
                player.get_bullets(),
                boss,
                reward_system.piercing_level
            )
            
            if boss_killed:
                self._events.append(CollisionEvent(type='boss_killed', score=boss_score))
                if on_boss_killed:
                    on_boss_killed(boss_score)
            elif boss_score > 0:
                self._events.append(CollisionEvent(type='boss_hit', score=boss_score))
                if on_boss_hit:
                    on_boss_hit(boss_score)
            
            if not player_invincible and self.check_boss_vs_player(
                boss,
                player,
                lambda d: reward_system.calculate_damage_taken(d),
                player_hit_handler
            ):
                self._events.append(CollisionEvent(type='player_hit'))

    def _make_player_hit_handler(
        self,
        player: 'Player',
        on_player_hit: Callable[[int, 'Player'], None] = None,
        on_clear_bullets: Callable = None,
    ) -> Callable[[int, 'Player'], None]:
        def handle_player_hit(damage: int, target=None) -> None:
            hit_target = target or player
            if on_player_hit:
                on_player_hit(damage, hit_target)
            if on_clear_bullets:
                on_clear_bullets()

        return handle_player_hit

    def check_player_bullets_vs_enemies(
        self,
        player_bullets: List['Bullet'],
        enemies: List['Enemy'],
        score_multiplier: float,
        explosive_level: int,
        piercing_level: int = 0,
    ) -> Tuple[int, int]:
        if self._uses_rust_batch_collision():
            return self._check_player_bullets_vs_enemies_rust(
                player_bullets,
                enemies,
                score_multiplier,
                explosive_level,
                piercing_level,
            )
        return self._check_player_bullets_vs_enemies_python(
            player_bullets,
            enemies,
            score_multiplier,
            explosive_level,
            piercing_level,
        )

    def _get_enemy_collision_id(self, enemy: 'Enemy') -> int:
        return id(enemy)

    def _bullet_has_hit_enemy(self, bullet: 'Bullet', enemy: 'Enemy') -> bool:
        enemy_id = self._get_enemy_collision_id(enemy)
        has_hit_enemy = getattr(bullet, "has_hit_enemy", None)
        return bool(has_hit_enemy and has_hit_enemy(enemy_id))

    def _record_bullet_enemy_hit(self, bullet: 'Bullet', enemy: 'Enemy') -> None:
        add_hit_enemy = getattr(bullet, "add_hit_enemy", None)
        if add_hit_enemy:
            add_hit_enemy(self._get_enemy_collision_id(enemy))

    def _check_player_bullets_vs_enemies_rust(
        self,
        player_bullets: List['Bullet'],
        enemies: List['Enemy'],
        score_multiplier: float,
        explosive_level: int,
        piercing_level: int,
    ) -> Tuple[int, int]:
        score_gained = 0
        enemies_killed = 0

        bullet_data, bullet_map = self._build_bullet_collision_data(player_bullets)
        enemy_data, enemy_map = self._build_enemy_collision_data(enemies)
        if not bullet_data or not enemy_data:
            return score_gained, enemies_killed

        hits = batch_collide_bullets_vs_entities(
            bullet_data, enemy_data, self._grid_cell_size)

        for bid, eid in hits:
            bullet = bullet_map.get(bid)
            enemy = enemy_map.get(eid)
            if bullet is None or enemy is None or not bullet.active or not enemy.active:
                continue
            if piercing_level > 0 and self._bullet_has_hit_enemy(bullet, enemy):
                continue
            killed, score = self._apply_player_bullet_hit(
                bullet,
                enemy,
                enemies,
                score_multiplier,
                explosive_level,
                piercing_level,
            )
            enemies_killed += killed
            score_gained += score

        return score_gained, enemies_killed

    def _build_bullet_collision_data(self, player_bullets: List['Bullet']) -> tuple[list[tuple], dict]:
        bullet_data = self._bullet_data
        bullet_map = self._bullet_map
        bullet_data.clear()
        bullet_map.clear()
        for i, bullet in enumerate(player_bullets):
            if bullet.active:
                r = bullet.rect
                bullet_data.append((i, float(r.left), float(r.top),
                                    float(r.width), float(r.height)))
                bullet_map[i] = bullet
        return bullet_data, bullet_map

    def _build_enemy_collision_data(self, enemies: List['Enemy']) -> tuple[list[tuple], dict]:
        enemy_data = self._enemy_data
        enemy_map = self._enemy_map
        enemy_data.clear()
        enemy_map.clear()
        for i, enemy in enumerate(enemies):
            if enemy.active:
                eid = -i - 1
                hb = enemy.get_hitbox()
                enemy_data.append((eid, float(hb.left), float(hb.top),
                                   float(hb.width), float(hb.height)))
                enemy_map[eid] = enemy
        return enemy_data, enemy_map

    def _check_player_bullets_vs_enemies_python(
        self,
        player_bullets: List['Bullet'],
        enemies: List['Enemy'],
        score_multiplier: float,
        explosive_level: int,
        piercing_level: int,
    ) -> Tuple[int, int]:
        score_gained = 0
        enemies_killed = 0

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
                    if piercing_level > 0 and self._bullet_has_hit_enemy(bullet, enemy):
                        continue
                    killed, score = self._apply_player_bullet_hit(
                        bullet,
                        enemy,
                        enemies,
                        score_multiplier,
                        explosive_level,
                        piercing_level,
                    )
                    enemies_killed += killed
                    score_gained += score
                    break

        return score_gained, enemies_killed

    def _apply_player_bullet_hit(
        self,
        bullet: 'Bullet',
        enemy: 'Enemy',
        enemies: List['Enemy'],
        score_multiplier: float,
        explosive_level: int,
        piercing_level: int,
    ) -> tuple[int, int]:
        enemy.take_damage(bullet.data.damage)
        if bullet.data.owner == "player" and piercing_level > 0:
            self._record_bullet_enemy_hit(bullet, enemy)

        if explosive_level > 0:
            self._handle_explosive_damage(bullet, enemies, explosive_level)

        enemies_killed = 0
        score_gained = 0
        if not enemy.active:
            enemies_killed = 1
            score_gained = self._scaled_score(enemy.data.score, score_multiplier)

        if bullet.data.owner == "player" and piercing_level <= 0:
            bullet.active = False

        return enemies_killed, score_gained

    def _uses_rust_batch_collision(self) -> bool:
        return bool(self._use_rust and batch_collide_bullets_vs_entities is not None)

    @staticmethod
    def _scaled_score(base_score: int, multiplier: float) -> int:
        return int(round(base_score * multiplier))

    def _handle_explosive_damage(
        self,
        bullet: 'Bullet',
        enemies: List['Enemy'],
        explosive_level: int
    ) -> None:
        bullet_x = bullet.rect.centerx
        bullet_y = bullet.rect.centery
        explosion_radius_sq = (GAME_CONSTANTS.BALANCE.EXPLOSION_RADIUS * explosive_level) ** 2
        explosion_radius = GAME_CONSTANTS.BALANCE.EXPLOSION_RADIUS * explosive_level

        explosion_triggered = False

        for enemy in self._get_potential_explosion_targets(bullet_x, bullet_y, explosion_radius, enemies):
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

        boss_hitbox = boss.get_hitbox()
        active_count = 0
        found_hit = False
        for bullet in player_bullets:
            if not bullet.active:
                continue
            active_count += 1
            if bullet.get_rect().colliderect(boss_hitbox):
                found_hit = True
                break
            if active_count >= 32:
                break
        if active_count < 32 and not found_hit:
            return 0, False

        for bullet in self._get_potential_boss_bullets(player_bullets, boss_hitbox, active_count):
            if bullet.active and bullet.get_rect().colliderect(boss_hitbox):
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
            if enemy.active and player_hitbox.colliderect(enemy.get_hitbox()) and not try_dodge_func():
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
            if eb.active and not getattr(eb, "held", False) and eb.rect.colliderect(player_hitbox):
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
            if boss.get_hitbox().colliderect(player_hitbox):
                damage = calculate_damage_func(GAME_CONSTANTS.DAMAGE.BOSS_COLLISION_DAMAGE)
                on_player_hit_func(damage, player)
                return True

        return False
