"""Enemy and boss spawning controller with wave management."""

import random
from typing import TYPE_CHECKING

from airwar.config import BASE_ENEMY_PARAMS, DIFFICULTY_SETTINGS, get_screen_width
from airwar.entities import Boss, BossData, Bullet, Enemy, EnemySpawner, EnemyState
from airwar.entities.interfaces import IBulletSpawner

if TYPE_CHECKING:
    from airwar.game.systems.difficulty_manager import DifficultyManager

from ..spawners.enemy_bullet_spawner import EnemyBulletSpawner


class SpawnController:
    """Enemy and boss spawn controller with wave-based spawning.

    Manages enemy wave lifecycle and boss spawn timing. Uses EnemySpawner
    for enemy creation and tracks boss state for escape/cleanup logic.

    Attributes:
        enemies: List of active Enemy entities.
        enemy_bullets: List of active enemy bullet entities.
        boss: Current Boss instance or None.
    """

    BOSS_SPAWN_INTERVAL = 1800
    ESCAPE_PENALTY_MULT = 1.5
    ENEMY_EXIT_X_OFFSETS = [-300, 300, 0, -150, 150]
    ENEMY_EXIT_END_Y = -100
    BOSS_HEALTH_TO_ELITE_RATIO = 4
    ELITE_HEALTH_MULTIPLIER = 2.5
    BOSS_HEALTH_SCALING = 0.5
    ESCAPE_TIME_SAFETY_MULTIPLIER = 2.0
    PLAYER_BULLETS_PER_SHOT = 2
    PLAYER_FIRE_INTERVAL = 8
    NORMAL_ENEMY_KILL_SECONDS = 1.2
    MIN_ESCAPE_TIME = 1200
    MAX_ESCAPE_TIME = 3600
    BOSS_BASE_SPEED = 1.5
    BOSS_SPEED_INCREMENT = 0.1
    BOSS_BASE_SCORE = 400
    BOSS_SCORE_INCREMENT = 100
    BOSS_SPRITE_WIDTH = 210
    BOSS_SPRITE_HEIGHT = 170
    BOSS_BASE_FIRE_RATE = 45
    BOSS_FIRE_RATE_DECREMENT = 2
    BOSS_SPAWN_Y = -100

    def __init__(self, settings: dict):
        self.enemy_spawner = EnemySpawner()
        self._base_enemy_health = settings["enemy_health"]
        self.enemy_spawner.set_params(
            health=settings["enemy_health"], speed=settings["enemy_speed"], spawn_rate=settings["spawn_rate"]
        )
        self.enemy_spawner.set_spread_enemy_cap(settings.get("spread_enemy_cap", 2))

        self.enemies: list[Enemy] = []
        self.enemy_bullets: list[Bullet] = []
        self.boss: Boss | None = None
        self.boss_spawn_timer = 0
        self.boss_spawn_interval = settings.get("boss_spawn_interval", self.BOSS_SPAWN_INTERVAL)
        self._base_boss_spawn_interval = self.boss_spawn_interval
        self._escape_penalty_multiplier = settings.get("escape_penalty_multiplier", self.ESCAPE_PENALTY_MULT)
        self.is_boss_killed = False
        self._bullet_spawner: IBulletSpawner | None = None
        self._difficulty_manager: DifficultyManager | None = None

    def set_bullet_spawner(self, spawner: IBulletSpawner) -> None:
        """Inject the bullet spawner used by enemies and the boss.

        Args:
            spawner: Implementation of `IBulletSpawner` that owns the
                live bullet list and creates new bullets on demand.
        """
        self._bullet_spawner = spawner
        self.enemy_spawner.set_bullet_spawner(spawner)

    def set_difficulty(self, difficulty: str) -> None:
        """Re-initialize spawn params from difficulty settings on restore."""
        settings = DIFFICULTY_SETTINGS.get(difficulty, DIFFICULTY_SETTINGS["medium"])
        self._base_enemy_health = settings["enemy_health"]
        self.enemy_spawner.set_params(
            health=settings["enemy_health"], speed=settings["enemy_speed"], spawn_rate=settings["spawn_rate"]
        )
        self.enemy_spawner.set_spread_enemy_cap(settings.get("spread_enemy_cap", 2))

    def set_difficulty_manager(self, manager: "DifficultyManager") -> None:
        """Inject the difficulty manager that produces live spawn params.

        Args:
            manager: DifficultyManager instance consulted by
                `get_current_params` for progressive scaling.
        """
        self._difficulty_manager = manager

    def get_current_params(self) -> dict:
        """Return the current spawn parameters used for enemy waves.

        Delegates to the difficulty manager when available; otherwise
        returns the static base enemy parameters from configuration.

        Returns:
            dict: Spawn parameters containing keys `speed`, `fire_rate`,
            `aggression`, `spawn_rate`, `multiplier`, `boss_kills`, and
            `complexity`.
        """
        if self._difficulty_manager:
            return self._difficulty_manager.get_current_params()

        return {
            "speed": BASE_ENEMY_PARAMS["speed"],
            "fire_rate": BASE_ENEMY_PARAMS["fire_rate"],
            "aggression": BASE_ENEMY_PARAMS["aggression"],
            "spawn_rate": BASE_ENEMY_PARAMS["spawn_rate"],
            "multiplier": 1.0,
            "boss_kills": 0,
            "complexity": 1,
        }

    def init_bullet_system(self) -> None:
        """Create and install the default enemy bullet spawner.

        Wires an `EnemyBulletSpawner` over `self.enemy_bullets` and
        forwards it through `set_bullet_spawner` so enemies and boss
        share a single bullet pool.
        """
        bullet_spawner = EnemyBulletSpawner(self.enemy_bullets)
        self.set_bullet_spawner(bullet_spawner)

    def update(self, score: int, slow_factor: float, player_pos: tuple | None = None) -> bool:
        """Advance spawn state by one frame.

        Drives the enemy spawner (only when no boss is active) and
        increments the boss spawn timer. Signals when a boss should be
        spawned by the caller.

        Args:
            score: Current player score (currently unused; reserved for
                score-based spawn gating).
            slow_factor: World time-scale factor (e.g. 0.5 during slow).
            player_pos: Optional (x, y) player position used by adaptive
                spawn strategies.

        Returns:
            bool: True if a boss should be spawned this frame, else False.
        """
        # Don't spawn new enemies when boss is active
        if self.boss is None:
            self.enemy_spawner.update(self.enemies, slow_factor, player_pos)

        self.boss_spawn_timer += 1
        if self.boss is None and self.boss_spawn_timer >= self.boss_spawn_interval / slow_factor:
            self.boss_spawn_timer = 0
            return True
        return False

    def balance_for_player_dps(self, player_dps: float) -> None:
        """Scale enemy health so kills take ~NORMAL_ENEMY_KILL_SECONDS.

        Args:
            player_dps: Player's effective damage per second. The enemy
                health is raised to keep the average kill time near the
                configured constant, but never below the base health.
        """
        target_health = int(max(self._base_enemy_health, round(player_dps * self.NORMAL_ENEMY_KILL_SECONDS)))
        if target_health == self.enemy_spawner.health:
            return
        self.enemy_spawner.health = target_health

    def spawn_boss(self, boss_kill_count: int, bullet_damage: int, player_dps: float | None = None) -> Boss:
        """Spawn the next boss with health, speed, and escape-time scaling.

        Forces all currently active enemies to begin their exit
        animation so the boss has a clear field, then constructs the
        boss from `BossData` with stats derived from boss-kill count and
        the player's DPS.

        Args:
            boss_kill_count: How many bosses the player has killed this run.
            bullet_damage: Per-shot player bullet damage used for the
                escape-time estimate when `player_dps` is not supplied.
            player_dps: Optional player DPS used for the escape-time
                estimate (preferred over `bullet_damage`).

        Returns:
            Boss: The newly spawned boss instance, also stored on
            `self.boss`.
        """
        # Force all existing enemies to exit when boss appears
        for enemy in self.enemies:
            if enemy.active and getattr(enemy, "_state", None) == EnemyState.ACTIVE:
                enemy.begin_exit(enemy.rect.x + random.choice(self.ENEMY_EXIT_X_OFFSETS), self.ENEMY_EXIT_END_Y)

        screen_width = get_screen_width()
        base_health = self._calculate_boss_health(boss_kill_count)
        escape_time = self._calculate_escape_time(base_health, bullet_damage, player_dps)
        escape_time = max(self.MIN_ESCAPE_TIME, min(escape_time, self.MAX_ESCAPE_TIME))

        boss_data = BossData(
            health=base_health,
            speed=self.BOSS_BASE_SPEED + boss_kill_count * self.BOSS_SPEED_INCREMENT,
            score=self.BOSS_BASE_SCORE + boss_kill_count * self.BOSS_SCORE_INCREMENT,
            width=self.BOSS_SPRITE_WIDTH,
            height=self.BOSS_SPRITE_HEIGHT,
            fire_rate=self.BOSS_BASE_FIRE_RATE - boss_kill_count * self.BOSS_FIRE_RATE_DECREMENT,
            phase=1,
            escape_time=escape_time,
        )

        boss = Boss(screen_width // 2 - boss_data.width // 2, self.BOSS_SPAWN_Y, boss_data)
        if self._bullet_spawner:
            boss.set_bullet_spawner(self._bullet_spawner)
        self.boss = boss
        self.boss_spawn_interval = self._base_boss_spawn_interval
        return boss

    def _calculate_boss_health(self, boss_kill_count: int) -> int:
        elite_health = int(self.enemy_spawner.health * self.ELITE_HEALTH_MULTIPLIER)
        base_health = elite_health * self.BOSS_HEALTH_TO_ELITE_RATIO
        return int(base_health * (1 + boss_kill_count * self.BOSS_HEALTH_SCALING))

    def _calculate_escape_time(self, boss_health: int, bullet_damage: int, player_dps: float | None = None) -> int:
        if boss_health <= 0:
            boss_health = 1
        if bullet_damage <= 0:
            bullet_damage = 1
        damage_per_frame = (
            max(1.0, abs(float(player_dps))) / 60
            if player_dps is not None
            else max(1, bullet_damage) * self.PLAYER_BULLETS_PER_SHOT / self.PLAYER_FIRE_INTERVAL
        )
        kill_frames = boss_health / damage_per_frame
        return round(kill_frames * self.ESCAPE_TIME_SAFETY_MULTIPLIER + Boss.ENRAGE_DURATION)

    def reset_boss_timer(self, penalty: bool = False) -> None:
        """Reset the boss spawn timer, optionally applying escape penalty.

        Args:
            penalty: If True, lengthen `boss_spawn_interval` by the
                configured escape penalty multiplier so the next boss
                takes longer to appear after a boss escape.
        """
        self.boss_spawn_timer = 0
        if penalty:
            self.boss_spawn_interval = int(self._base_boss_spawn_interval * self._escape_penalty_multiplier)

    def cleanup(self) -> None:
        """Prune inactive enemies and clear the boss reference if needed.

        Convenience entry point that delegates to `cleanup_enemies` and
        the internal `_handle_boss_cleanup` helper. Safe to call once
        per frame after enemy/boss updates complete.
        """
        self.cleanup_enemies()
        self._handle_boss_cleanup()

    def cleanup_enemies(self) -> None:
        """Remove inactive enemy entities from the active list.

        Performs an O(n) scan with a fast-path early-out when every
        enemy is still active, so the cleanup cost is negligible on
        dense enemy frames.
        """
        if not self.enemies:
            return
        if not any(not e.active for e in self.enemies):
            return
        self.enemies = [e for e in self.enemies if e.active]

    def _handle_boss_cleanup(self) -> None:
        if self.boss and not self.boss.active:
            self.reset_boss_timer(penalty=self.boss.is_escaped)
            self.boss = None

    def clear_boss(self) -> None:
        """F7: encapsulate direct ``self.boss = None`` writes from scene layer.

        Returns:
            bool: True if a boss was actually cleared; False if there was none.
        """
        if self.boss is None:
            return False
        self.boss = None
        self.reset_boss_timer(penalty=False)
        return True
