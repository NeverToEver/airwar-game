import pygame
from .scene import Scene
from airwar.entities import Player, EnemySpawner, Boss, BossData
from airwar.game.systems.health_system import HealthSystem
from airwar.game.systems.reward_system import RewardSystem
from airwar.game.systems.hud_renderer import HUDRenderer
from airwar.game.systems.notification_manager import NotificationManager
from airwar.game.controllers.game_controller import GameController
from airwar.game.controllers.spawn_controller import SpawnController
from airwar.game.rendering.game_renderer import GameRenderer, GameEntities
from airwar.ui.reward_selector import RewardSelector


class GameScene(Scene):
    def __init__(self):
        self.game_controller: GameController = None
        self.game_renderer: GameRenderer = None
        self.health_system: HealthSystem = None
        self.reward_system: RewardSystem = None
        self.hud_renderer: HUDRenderer = None
        self.notification_manager: NotificationManager = None
        self.spawn_controller: SpawnController = None
        self.player: Player = None
        self.reward_selector: RewardSelector = RewardSelector()
        self._kill_count = 0
        self._boss_kill_count = 0
        self._total_score_gained = 0

    def enter(self, **kwargs) -> None:
        from airwar.config import DIFFICULTY_SETTINGS, get_screen_width, get_screen_height
        from airwar.input import PygameInputHandler

        screen_width = get_screen_width()
        screen_height = get_screen_height()

        difficulty = kwargs.get('difficulty', 'medium')
        username = kwargs.get('username', 'Player')
        settings = DIFFICULTY_SETTINGS[difficulty]

        self.game_controller = GameController(difficulty, username)
        self.game_renderer = GameRenderer()
        self.health_system = HealthSystem(difficulty)
        self.reward_system = self.game_controller.reward_system
        self.hud_renderer = HUDRenderer()
        self.notification_manager = self.game_controller.notification_manager

        self.spawn_controller = SpawnController(settings)
        self.spawn_controller.init_bullet_system()
        
        self.enemy_bullets = []

        input_handler = PygameInputHandler()
        self.player = Player(screen_width // 2 - 25, screen_height - 100, input_handler)
        self.player.rect.y = -80
        self.player.bullet_damage = settings['bullet_damage']

        self._setup_reward_selector()

    def _setup_reward_selector(self) -> None:
        self.reward_selector.show = lambda options, callback: self._show_reward_selection(options, callback)
        self.reward_selector.hide = lambda: setattr(self, 'reward_visible', False)
        self.reward_selector.visible = False

    def _show_reward_selection(self, options: list, callback) -> None:
        self.reward_selector.visible = True
        self.reward_selector.options = options
        self.reward_selector.selected_index = 0
        self.reward_selector.on_select = callback

    def exit(self) -> None:
        pass

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                if not self.game_controller.state.paused and not self.reward_selector.visible:
                    self.player.fire()

        self.reward_selector.handle_input(event)

    def update(self, *args, **kwargs) -> None:
        self.reward_selector.update()

        if self.game_controller.state.entrance_animation:
            self._update_entrance()
            return

        if self.game_controller.state.paused or self.reward_selector.visible:
            return

        self._update_game()

    def _update_entrance(self) -> None:
        from airwar.config import get_screen_width, get_screen_height
        screen_width = get_screen_width()
        screen_height = get_screen_height()

        self.game_controller.state.entrance_timer += 1
        progress = self.game_controller.state.entrance_timer / self.game_controller.state.entrance_duration

        if progress >= 1.0:
            self.game_controller.state.entrance_animation = False
            self.player.rect.y = screen_height - 100
        else:
            target_y = screen_height - 100
            start_y = -80
            self.player.rect.y = int(start_y + (target_y - start_y) * progress)
            self.player.rect.x = screen_width // 2 - 25

    def _update_game(self) -> None:
        has_regen = 'Regeneration' in self.reward_system.unlocked_buffs
        self.game_controller.update(self.player, has_regen)

        self.player.update()
        self.player.auto_fire()

        self._update_enemy_spawning()
        self._update_entities()
        self._check_collisions()
        self._check_milestones()

        self.spawn_controller.cleanup()
        self._cleanup_bullets()

        if not self.player.active:
            self.game_controller.state.running = False

    def _update_enemy_spawning(self) -> None:
        spawn_needed = self.spawn_controller.update(
            self.game_controller.state.score,
            self.reward_system.slow_factor
        )
        
        if spawn_needed:
            self.spawn_controller.spawn_boss(
                self.game_controller.cycle_count,
                self.player.bullet_damage
            )
        
        if self.spawn_controller.boss:
            self._update_boss()

    def _spawn_boss(self) -> None:
        from airwar.config import get_screen_width
        screen_width = get_screen_width()
        cycle_count = self.game_controller.cycle_count

        base_health = 500 * (1 + cycle_count * 0.5)
        escape_time = int(base_health / self.player.bullet_damage * 2.5)
        escape_time = max(600, min(escape_time, 1800))

        boss_data = BossData(
            health=base_health,
            speed=1.5 + cycle_count * 0.1,
            score=5000 + cycle_count * 1000,
            width=120,
            height=100,
            fire_rate=60 - cycle_count * 3,
            phase=1,
            escape_time=escape_time
        )

        from airwar.game import EnemyBulletSpawner
        bullet_spawner = EnemyBulletSpawner(self.spawn_controller.enemy_bullets)
        boss = Boss(screen_width // 2 - boss_data.width // 2, -100, boss_data)
        boss.set_bullet_spawner(bullet_spawner)
        self.spawn_controller.boss = boss
        self.game_controller.show_notification(f"! BOSS APPROACHING ({int(escape_time/60)}s) !")

    def _update_boss(self) -> None:
        boss = self.spawn_controller.boss
        boss.update()
        player_hitbox = self.player.get_hitbox()

        if not boss.is_entering() and boss.active:
            if boss.rect.colliderect(player_hitbox):
                if not self.game_controller.state.player_invincible:
                    damage = self.reward_system.calculate_damage_taken(30)
                    self.player.take_damage(damage)
                    self.game_controller.on_player_hit(damage, self.player)

        for bullet in self.player.get_bullets():
            if bullet.active and boss and boss.active and not boss.is_entering():
                if bullet.get_rect().colliderect(boss.get_rect()):
                    score_reward = boss.take_damage(bullet.data.damage)
                    if score_reward > 0:
                        self._total_score_gained += score_reward
                        self.game_controller.state.score += score_reward
                        self.game_controller.show_notification(f"+{score_reward} BOSS SCORE!")

                    if self.reward_system.piercing_level <= 0:
                        bullet.active = False

                    if not boss.active:
                        self._kill_count += 1
                        self._boss_kill_count += 1
                        self._total_score_gained += boss.data.score
                        self.game_controller.state.score += boss.data.score
                        self.game_controller.cycle_count += 1
                        self.reward_system.apply_lifesteal(self.player, boss.data.score)
                        self.spawn_controller.boss = None

        if boss and not boss.active:
            if boss.is_escaped():
                self.game_controller.show_notification("BOSS ESCAPED! (+0)")
            self.spawn_controller.boss = None

    def _update_entities(self) -> None:
        for enemy in self.spawn_controller.enemies:
            enemy.update()
            if enemy.rect.colliderect(self.player.get_hitbox()):
                if not self.reward_system.try_dodge():
                    self.game_controller.on_player_hit(20, self.player)

    def _check_collisions(self) -> None:
        self._check_player_bullets_vs_enemies()
        self._check_enemy_bullets_vs_player()

    def _check_player_bullets_vs_enemies(self) -> None:
        enemies = self.spawn_controller.enemies
        for bullet in self.player.get_bullets():
            for enemy in enemies:
                if bullet.active and enemy.active:
                    if bullet.get_rect().colliderect(enemy.get_rect()):
                        if self.reward_system.explosive_level > 0:
                            self.reward_system.do_explosive_damage(
                                enemies, enemy.rect.centerx, enemy.rect.centery, bullet.data.damage)
                        else:
                            enemy.take_damage(bullet.data.damage)

                        if self.reward_system.piercing_level <= 0:
                            bullet.active = False

                        if not enemy.active:
                            score_gained = enemy.data.score * self.game_controller.state.score_multiplier
                            self._total_score_gained += score_gained
                            self.game_controller.state.score += score_gained
                            self._kill_count += 1
                            self.reward_system.apply_lifesteal(self.player, enemy.data.score)

    def _check_enemy_bullets_vs_player(self) -> None:
        player_hitbox = self.player.get_hitbox()
        for eb in self.spawn_controller.enemy_bullets:
            eb.update()
            if eb.active and eb.rect.colliderect(player_hitbox):
                if not self.game_controller.state.player_invincible:
                    damage = self.reward_system.calculate_damage_taken(eb.data.damage)
                    self.player.take_damage(damage)
                    self.game_controller.on_player_hit(damage, self.player)

    def _cleanup_bullets(self) -> None:
        self.enemy_bullets = [b for b in self.spawn_controller.enemy_bullets if b.active]

    def _check_milestones(self) -> None:
        threshold = self.game_controller.get_next_threshold()
        if self.game_controller.state.score >= threshold:
            options = self.reward_system.generate_options(
                self.game_controller.cycle_count, self.reward_system.unlocked_buffs)
            self._show_reward_selection(options, self._on_reward_selected)
            self.game_controller.state.paused = True

    def _on_reward_selected(self, reward: dict) -> None:
        self.game_controller.on_reward_selected(reward, self.player)
        self.reward_selector.visible = False

    def render(self, surface: pygame.Surface) -> None:
        entities = GameEntities(
            player=self.player,
            enemies=self.spawn_controller.enemies,
            boss=self.spawn_controller.boss
        )
        self.game_renderer.render(surface, self.game_controller.state, entities)

        self._render_player_bullets(surface)
        self._render_enemy_bullets(surface)
        self._render_hud(surface)

        if self.reward_selector.visible:
            self.reward_selector.render(surface)

    def _render_player_bullets(self, surface: pygame.Surface) -> None:
        for bullet in self.player.get_bullets():
            bullet.render(surface)

    def _render_enemy_bullets(self, surface: pygame.Surface) -> None:
        for eb in self.spawn_controller.enemy_bullets:
            eb.render(surface)

    def _render_hud(self, surface: pygame.Surface) -> None:
        self.game_renderer.render_hud(
            surface,
            self.game_controller.state.score,
            self.game_controller.state.difficulty,
            self.player.health,
            self.player.max_health,
            self._kill_count,
            self.game_controller.get_next_threshold(),
            self.game_controller.cycle_count,
            self.game_controller.milestone_index + self.game_controller.max_cycles,
            boss_kills=self._boss_kill_count
        )

        self.game_renderer.render_notification(
            surface, self.game_controller.state.notification, self.game_controller.state.notification_timer)

    def get_score(self) -> int:
        return self.game_controller.state.score if self.game_controller else 0

    def get_kills(self) -> int:
        return self.game_controller.cycle_count if self.game_controller else 0

    @property
    def enemies(self) -> list:
        return self.spawn_controller.enemies if self.spawn_controller else []

    @property
    def enemy_spawner(self):
        return self.spawn_controller.enemy_spawner if self.spawn_controller else None

    @property
    def boss(self):
        return self.spawn_controller.boss if self.spawn_controller else None

    @property
    def score(self) -> int:
        return self.game_controller.state.score if self.game_controller else 0

    @score.setter
    def score(self, value: int) -> None:
        if self.game_controller:
            self.game_controller.state.score = value

    @property
    def kills(self) -> int:
        return self.game_controller.cycle_count if self.game_controller else 0

    @kills.setter
    def kills(self, value: int) -> None:
        if self.game_controller:
            self.game_controller.cycle_count = value

    def is_game_over(self) -> bool:
        return not self.player.active if self.player else True

    def is_paused(self) -> bool:
        return self.game_controller.state.paused if self.game_controller else False

    def pause(self) -> None:
        if self.game_controller and not self.reward_selector.visible:
            self.game_controller.state.paused = True

    def resume(self) -> None:
        if self.game_controller:
            self.game_controller.state.paused = False

    @property
    def unlocked_buffs(self) -> list:
        return self.reward_system.unlocked_buffs if self.reward_system else []

    @unlocked_buffs.setter
    def unlocked_buffs(self, value: list) -> None:
        if self.reward_system:
            self.reward_system.unlocked_buffs = value

    @property
    def cycle_count(self) -> int:
        return self.game_controller.cycle_count if self.game_controller else 0

    @cycle_count.setter
    def cycle_count(self, value: int) -> None:
        if self.game_controller:
            self.game_controller.cycle_count = value

    @property
    def milestone_index(self) -> int:
        return self.game_controller.milestone_index if self.game_controller else 0

    @milestone_index.setter
    def milestone_index(self, value: int) -> None:
        if self.game_controller:
            self.game_controller.milestone_index = value

    @property
    def entrance_animation(self) -> bool:
        return self.game_controller.state.entrance_animation if self.game_controller else False

    @entrance_animation.setter
    def entrance_animation(self, value: bool) -> None:
        if self.game_controller:
            self.game_controller.state.entrance_animation = value

    @property
    def entrance_timer(self) -> int:
        return self.game_controller.state.entrance_timer if self.game_controller else 0

    @entrance_timer.setter
    def entrance_timer(self, value: int) -> None:
        if self.game_controller:
            self.game_controller.state.entrance_timer = value

    @property
    def entrance_duration(self) -> int:
        return self.game_controller.state.entrance_duration if self.game_controller else 60

    @property
    def running(self) -> bool:
        return self.game_controller.state.running if self.game_controller else False

    @running.setter
    def running(self, value: bool) -> None:
        if self.game_controller:
            self.game_controller.state.running = value

    @property
    def paused(self) -> bool:
        return self.game_controller.state.paused if self.game_controller else False

    @paused.setter
    def paused(self, value: bool) -> None:
        if self.game_controller:
            self.game_controller.state.paused = value

    @property
    def notification(self) -> str:
        return self.game_controller.state.notification if self.game_controller else None

    @notification.setter
    def notification(self, value: str) -> None:
        if self.game_controller:
            self.game_controller.state.notification = value

    @property
    def notification_timer(self) -> int:
        return self.game_controller.state.notification_timer if self.game_controller else 0

    @notification_timer.setter
    def notification_timer(self, value: int) -> None:
        if self.game_controller:
            self.game_controller.state.notification_timer = value

    @property
    def player_invincible(self) -> bool:
        return self.game_controller.state.player_invincible if self.game_controller else False

    @player_invincible.setter
    def player_invincible(self, value: bool) -> None:
        if self.game_controller:
            self.game_controller.state.player_invincible = value

    def _calculate_damage_taken(self, damage: int) -> int:
        return self.reward_system.calculate_damage_taken(damage)

    def _try_dodge(self) -> bool:
        return self.reward_system.try_dodge()

    def _get_current_threshold(self, index: int) -> float:
        return self.game_controller.get_current_threshold(index)

    @property
    def difficulty(self) -> str:
        return self.game_controller.state.difficulty if self.game_controller else 'medium'

    @difficulty.setter
    def difficulty(self, value: str) -> None:
        if self.game_controller:
            self.game_controller.state.difficulty = value

    def _get_next_threshold(self) -> float:
        return self.game_controller.get_next_threshold()
