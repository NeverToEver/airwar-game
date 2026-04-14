from dataclasses import dataclass
from typing import List, Tuple
from airwar.entities import Player, Enemy, Boss, Bullet


@dataclass
class CollisionResult:
    player_damaged: bool = False
    enemies_killed: int = 0
    score_gained: int = 0
    boss_damaged: bool = False
    boss_killed: bool = False


class CollisionController:
    def __init__(self):
        pass

    def check_player_bullets_vs_enemies(
        self,
        player_bullets: List[Bullet],
        enemies: List[Enemy],
        score_multiplier: int,
        explosive_level: int
    ) -> Tuple[int, int]:
        score_gained = 0
        enemies_killed = 0

        for bullet in player_bullets:
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
        player_bullets: List[Bullet],
        boss: Boss,
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
        enemies: List[Enemy],
        try_dodge_func,
        on_player_hit_func
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
        enemy_bullets: List[Bullet],
        player_hitbox,
        calculate_damage_func,
        on_player_hit_func
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
        boss: Boss,
        player_hitbox,
        calculate_damage_func,
        on_player_hit_func
    ) -> bool:
        player_damaged = False

        if boss and boss.active and not boss.is_entering():
            if boss.get_rect().colliderect(player_hitbox):
                damage = calculate_damage_func(30)
                on_player_hit_func(damage)
                player_damaged = True

        return player_damaged
