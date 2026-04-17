import pygame
pygame.init()
pygame.display.set_mode((800, 600))

from airwar.scenes.game_scene import GameScene
from airwar.entities import Enemy, EnemyData

scene = GameScene()
scene.enter(difficulty='easy', username='TestPlayer')

scene.player.health = 100
scene.player.max_health = 100
scene.game_controller.state.player_invincible = False
scene.game_controller.state.entrance_animation = False
scene.unlocked_buffs = []

scene.player.rect.y = 400
print(f"Player position after setting: x={scene.player.rect.x}, y={scene.player.rect.y}")
print(f"Player hitbox: {scene.player.get_hitbox()}")

enemy = Enemy(scene.player.rect.x, scene.player.rect.y,
             EnemyData(health=100, speed=1.0, bullet_type="single", fire_rate=120, enemy_type="straight"))
scene.spawn_controller.enemies.append(enemy)

print(f"\nEnemy position: x={enemy.rect.x}, y={enemy.rect.y}")
print(f"Enemy hitbox: {enemy.get_hitbox()}")

print(f"\nCollision detection:")
enemy_hitbox = enemy.get_hitbox()
player_hitbox = scene.player.get_hitbox()
print(f"Enemy hitbox: {enemy_hitbox}")
print(f"Player hitbox: {player_hitbox}")
print(f"Collision: {enemy_hitbox.colliderect(player_hitbox)}")

initial_health = scene.player.health

print(f"\nInitial player health: {initial_health}")
print(f"Player invincible: {scene.game_controller.state.player_invincible}")

scene._update_entities()

print(f"Final player health: {scene.player.health}")
print(f"Damage taken: {initial_health - scene.player.health}")
