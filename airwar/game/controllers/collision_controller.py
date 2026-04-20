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
    
    @property
    def events(self) -> List[CollisionEvent]:
        return self._events.copy()
    
    def clear_events(self) -> None:
        self._events.clear()
    
    def check_all_collisions(
        self,
        player: 'Player',
        enemies: List['Enemy'],
        boss: Optional['Boss'],
        enemy_bullets: List['EnemyBullet'],
        reward_system: any,
        player_invincible: bool,
        score_multiplier: int,
        on_enemy_killed: Callable,
        on_boss_killed: Callable,
        on_boss_hit: Callable,
        on_player_hit: Callable,
        on_lifesteal: Callable,
    ) -> None:
        self._events.clear()
        
        score_gained, enemies_killed = self.check_player_bullets_vs_enemies(
            player.get_bullets(),
            enemies,
            score_multiplier,
            reward_system.explosive_level
        )
        
        for i in range(enemies_killed):
            self._events.append(CollisionEvent(type='enemy_killed'))
            if on_enemy_killed:
                on_enemy_killed()
        
        if self.check_enemy_bullets_vs_player(
            enemy_bullets,
            player.get_hitbox(),
            lambda d: reward_system.calculate_damage_taken(d),
            on_player_hit
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
                self._events.append(CollisionEvent(type='boss_killed'))
                if on_boss_killed:
                    on_boss_killed()
            
            if self.check_boss_vs_player(
                boss,
                player.get_hitbox(),
                lambda d: reward_system.calculate_damage_taken(d),
                on_player_hit
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
            bullet.update()
            for enemy in enemies:
                if bullet.active and enemy.active:
                    if bullet.get_rect().colliderect(enemy.get_rect()):
                        damage = bullet.data.damage
                        enemy.take_damage(damage)

                        if explosive_level > 0:
                            pass

                        if not enemy.active:
                            enemies_killed += 1
                            score_gained += enemy.data.score * score_multiplier

                        if bullet.data.owner == "player":
                            bullet.active = False
                        break

        return score_gained, enemies_killed

    def check_player_bullets_vs_boss(
        self,
        player_bullets: List['Bullet'],
        boss: 'Boss',
        piercing_level: int
    ) -> Tuple[int, bool]:
        score_gained = 0
        boss_killed = False

        if boss and boss.active and not boss.is_entering():
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
        player_damaged = False

        for enemy in enemies:
            if enemy.active and player_hitbox.colliderect(enemy.get_rect()):
                if not try_dodge_func():
                    on_player_hit_func(20)
                    player_damaged = True
                    break

        return player_damaged

    def check_enemy_bullets_vs_player(
        self,
        enemy_bullets: List['Bullet'],
        player_hitbox,
        calculate_damage_func: Callable,
        on_player_hit_func: Callable
    ) -> bool:
        player_damaged = False

        for eb in enemy_bullets:
            eb.update()
            if eb.active and eb.rect.colliderect(player_hitbox):
                damage = calculate_damage_func(eb.data.damage)
                on_player_hit_func(damage)
                player_damaged = True
                break

        return player_damaged

    def check_boss_vs_player(
        self,
        boss: 'Boss',
        player_hitbox,
        calculate_damage_func: Callable,
        on_player_hit_func: Callable
    ) -> bool:
        player_damaged = False

        if boss and boss.active and not boss.is_entering():
            if boss.get_rect().colliderect(player_hitbox):
                damage = calculate_damage_func(30)
                on_player_hit_func(damage)
                player_damaged = True

        return player_damaged
