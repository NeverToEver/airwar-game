from dataclasses import dataclass, field
from typing import List, Tuple, Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from airwar.entities.player import Player
    from airwar.entities.enemy import Enemy
    from airwar.entities.boss import Boss
    from airwar.entities.bullet import Bullet, EnemyBullet


@dataclass
class CollisionResult:
    player_damaged: bool = False
    enemies_killed: int = 0
    score_gained: int = 0
    boss_damaged: bool = False
    boss_killed: bool = False


@dataclass
class CollisionEvent:
    type: str
    source: any = None
    target: any = None
    damage: int = 0
    score: int = 0


class CollisionController:
    def __init__(self):
        self._events: List[CollisionEvent] = []
        self._explosion_callback: Optional[Callable[[float, float, int], None]] = None

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
        player_invincible: bool,
        score_multiplier: int,
        on_enemy_killed: Callable[[int], None],
        on_boss_killed: Callable[[int], None],
        on_boss_hit: Callable[[int], None],
        on_player_hit: Callable[[int, 'Player'], None],
        on_lifesteal: Callable,
        on_clear_bullets: Callable = None,
    ) -> None:
        self._events.clear()
        
        score_gained, enemies_killed = self.check_player_bullets_vs_enemies(
            player.get_bullets(),
            enemies,
            score_multiplier,
            reward_system.explosive_level
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
        explosive_level: int
    ) -> Tuple[int, int]:
        score_gained = 0
        enemies_killed = 0

        for bullet in player_bullets:
            if not bullet.active:
                continue

            for enemy in enemies:
                if not enemy.active:
                    continue

                if bullet.get_rect().colliderect(enemy.get_hitbox()):
                    damage = bullet.data.damage
                    enemy.take_damage(damage)

                    if explosive_level > 0:
                        self._handle_explosive_damage(bullet, enemies, explosive_level)

                    if not enemy.active:
                        enemies_killed += 1
                        score_gained += enemy.data.score * score_multiplier

                    if bullet.data.owner == "player":
                        bullet.active = False
                    break

        return score_gained, enemies_killed

    def _handle_explosive_damage(
        self,
        bullet: 'Bullet',
        enemies: List['Enemy'],
        explosive_level: int
    ) -> None:
        from airwar.config import EXPLOSION_RADIUS
        from airwar.game.constants import GAME_CONSTANTS

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
        if not boss or not boss.active or boss.is_entering():
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
                    on_player_hit_func(20)
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
                damage = calculate_damage_func(30)
                on_player_hit_func(damage, player)
                return True

        return False
