import pygame
pygame.init()
pygame.display.set_mode((800, 600))

from airwar.scenes.game_scene import GameScene
from airwar.entities import Enemy, EnemyData

scene = GameScene()
scene.enter(difficulty='easy', username='TestPlayer')

enemy = Enemy(400, 300, EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight"))
scene.spawn_controller.enemies.append(enemy)

print(f"Enemy position: x={enemy.rect.x}, y={enemy.rect.y}")
print(f"Enemy size: w={enemy.rect.width}, h={enemy.rect.height}")
print(f"Enemy hitbox: {enemy.get_hitbox()}")

bullet = scene.player.fire()
print(f"\nBullet position: x={bullet.rect.x}, y={bullet.rect.y}")
print(f"Bullet size: w={bullet.rect.width}, h={bullet.rect.height}")

bullet.rect.x = enemy.rect.centerx - 4
bullet.rect.y = enemy.rect.y - 10
print(f"Adjusted bullet position: x={bullet.rect.x}, y={bullet.rect.y}")

print(f"\nBullet rect: {bullet.get_rect()}")
print(f"Enemy hitbox: {enemy.get_hitbox()}")

initial_health = enemy.health
scene._check_player_bullets_vs_enemies()
print(f"\nInitial health: {initial_health}")
print(f"Current health: {enemy.health}")
print(f"Damage dealt: {initial_health - enemy.health}")
