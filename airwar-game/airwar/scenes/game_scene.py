import pygame
from .scene import Scene
from airwar.entities import Player
from airwar.game.controllers.game_controller import GameController
from airwar.game.controllers.spawn_controller import SpawnController
from airwar.game.rendering.game_renderer import GameRenderer, GameEntities
from airwar.ui.reward_selector import RewardSelector
from airwar.game.mother_ship import (
    EventBus,
    InputDetector,
    MotherShipStateMachine,
    PersistenceManager,
    ProgressBarUI,
    MotherShip,
    GameIntegrator,
)


class GameScene(Scene):
    def __init__(self):
        self.game_controller: GameController = None
        self.game_renderer: GameRenderer = None
        self.health_system = None
        self.reward_system = None
        self.hud_renderer = None
        self.notification_manager = None
        self.spawn_controller: SpawnController = None
        self.player: Player = None
        self.reward_selector: RewardSelector = RewardSelector()
        self._mother_ship_integrator: GameIntegrator | None = None

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
        self.game_renderer.init_background(screen_width, screen_height)
        self.health_system = self.game_controller.health_system
        self.reward_system = self.game_controller.reward_system
        self.hud_renderer = self.game_renderer.hud_renderer
        self.notification_manager = self.game_controller.notification_manager

        self.spawn_controller = SpawnController(settings)
        self.spawn_controller.init_bullet_system()

        input_handler = PygameInputHandler()
        self.player = Player(screen_width // 2 - 25, screen_height - 100, input_handler)
        self.player.rect.y = -80
        self.player.bullet_damage = settings['bullet_damage']

        self.reward_selector.hide()
        self._init_mother_ship_system(screen_width, screen_height)

    def _init_mother_ship_system(self, screen_width: int, screen_height: int) -> None:
        event_bus = EventBus()
        input_detector = InputDetector(event_bus)
        state_machine = MotherShipStateMachine(event_bus)
        persistence_manager = PersistenceManager()
        progress_bar_ui = ProgressBarUI(screen_width, screen_height)
        mother_ship = MotherShip(screen_width, screen_height)

        self._mother_ship_integrator = GameIntegrator(
            event_bus=event_bus,
            input_detector=input_detector,
            state_machine=state_machine,
            persistence_manager=persistence_manager,
            progress_bar_ui=progress_bar_ui,
            mother_ship=mother_ship,
        )
        self._mother_ship_integrator.attach_game_scene(self)

    def exit(self) -> None:
        pass

    def on_resize(self, width: int, height: int) -> None:
        if self.game_renderer and self.game_renderer.background_renderer:
            self.game_renderer.background_renderer.resize(width, height)
        if self._mother_ship_integrator:
            self._mother_ship_integrator.resize(width, height)

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE and self._can_accept_combat_input():
            self.player.fire()
        self.reward_selector.handle_input(event)

    def _can_accept_combat_input(self) -> bool:
        if not self.game_controller or not self.player:
            return False
        if self.game_controller.state.entrance_animation:
            return False
        if self.game_controller.state.paused or self.reward_selector.visible:
            return False
        if self._mother_ship_integrator:
            if self._mother_ship_integrator.is_docked():
                return False
            if self._mother_ship_integrator.is_player_control_disabled():
                return False
        return True

    def update(self, *args, **kwargs) -> None:
        self.reward_selector.update()

        if self._mother_ship_integrator:
            self._mother_ship_integrator.update()

        if self.game_controller.state.entrance_animation:
            self._update_entrance()
            return

        if self._mother_ship_integrator:
            if self._mother_ship_integrator.is_docked():
                self._update_bullets_in_stasis()
                return
            if self._mother_ship_integrator.is_player_control_disabled():
                self._update_bullets_in_stasis()
                return

        if self.game_controller.state.paused or self.reward_selector.visible:
            return

        self._update_gameplay()

    def _update_entrance(self) -> None:
        from airwar.config import get_screen_width, get_screen_height

        screen_width = get_screen_width()
        screen_height = get_screen_height()

        self.game_controller.state.entrance_timer += 1
        progress = self.game_controller.state.entrance_timer / self.game_controller.state.entrance_duration

        if progress >= 1.0:
            self.game_controller.state.entrance_animation = False
            self.player.rect.x = screen_width // 2 - 25
            self.player.rect.y = screen_height - 100
            return

        target_y = screen_height - 100
        start_y = -80
        self.player.rect.y = int(start_y + (target_y - start_y) * progress)
        self.player.rect.x = screen_width // 2 - 25

    def _update_gameplay(self) -> None:
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
            boss = self.spawn_controller.spawn_boss(
                self.game_controller.cycle_count,
                max(1, self.player.bullet_damage)
            )
            self.game_controller.show_notification(
                f"! BOSS APPROACHING ({int(boss.data.escape_time / 60)}s) !"
            )

        if self.spawn_controller.boss:
            self._update_boss()

    def _damage_player(self, damage: int) -> bool:
        if self.game_controller.state.player_invincible:
            return False

        actual_damage = self.reward_system.calculate_damage_taken(damage)
        self.player.take_damage(actual_damage)
        self._clear_enemy_bullets()
        self.game_controller.on_player_hit(actual_damage, self.player)
        return True

    def _update_boss(self) -> None:
        boss = self.spawn_controller.boss
        if not boss:
            return

        player_pos = (self.player.rect.centerx, self.player.rect.centery)
        boss.update(self.spawn_controller.enemies, player_pos=player_pos)

        if boss.active and not boss.is_entering() and boss.rect.colliderect(self.player.get_hitbox()):
            self._damage_player(30)

        for bullet in self.player.get_bullets():
            if not bullet.active or not boss.active or boss.is_entering():
                continue
            if not bullet.get_rect().colliderect(boss.get_rect()):
                continue

            boss.take_damage(bullet.data.damage)
            if self.reward_system.piercing_level <= 0:
                bullet.active = False

            if not boss.active:
                self.game_controller.on_boss_killed(boss.data.score)
                self.game_controller.cycle_count += 1
                self.reward_system.apply_lifesteal(self.player, boss.data.score)
                self.game_controller.show_notification(f"+{boss.data.score} BOSS SCORE!")
                self.spawn_controller.boss = None
                break

        if boss and not boss.active:
            if boss.is_escaped():
                self.game_controller.show_notification("BOSS ESCAPED! (+0)")
            self.spawn_controller.boss = None

    def _update_entities(self) -> None:
        for enemy in self.spawn_controller.enemies:
            enemy.update(self.spawn_controller.enemies, self.reward_system.slow_factor)
            if enemy.active and enemy.rect.colliderect(self.player.get_hitbox()):
                if not self.reward_system.try_dodge():
                    self._damage_player(20)
                    break

    def _check_collisions(self) -> None:
        self._check_player_bullets_vs_enemies()
        self._check_enemy_bullets_vs_player()

    def _check_player_bullets_vs_enemies(self) -> None:
        enemies = self.spawn_controller.enemies
        for bullet in self.player.get_bullets():
            bullet.update()
            if not bullet.active:
                continue

            for enemy in enemies:
                if not enemy.active:
                    continue
                if not bullet.get_rect().colliderect(enemy.get_rect()):
                    continue

                enemy.take_damage(bullet.data.damage)
                if self.reward_system.explosive_level > 0:
                    self.reward_system.do_explosive_damage(
                        enemies,
                        enemy.rect.centerx,
                        enemy.rect.centery,
                        bullet.data.damage,
                    )

                if self.reward_system.piercing_level <= 0:
                    bullet.active = False

                if not enemy.active:
                    score_gained = enemy.data.score * self.game_controller.state.score_multiplier
                    self.game_controller.on_enemy_killed(score_gained)
                    self.reward_system.apply_lifesteal(self.player, enemy.data.score)

                if not bullet.active:
                    break

    def _check_enemy_bullets_vs_player(self) -> None:
        player_hitbox = self.player.get_hitbox()
        for bullet in self.spawn_controller.enemy_bullets:
            bullet.update()
            if bullet.active and bullet.rect.colliderect(player_hitbox):
                self._damage_player(bullet.data.damage)

    def _cleanup_bullets(self) -> None:
        self.player.cleanup_bullets()
        self.spawn_controller.enemy_bullets = [
            bullet for bullet in self.spawn_controller.enemy_bullets if bullet.active
        ]

    def _update_bullets_in_stasis(self) -> None:
        for bullet in self.player.get_bullets():
            bullet.update()
        self.player.cleanup_bullets()

    def _clear_enemy_bullets(self) -> None:
        for bullet in self.spawn_controller.enemy_bullets:
            bullet.active = False
        self.spawn_controller.enemy_bullets.clear()

    def _check_milestones(self) -> None:
        if self.game_controller.cycle_count >= self.game_controller.max_cycles:
            return

        threshold = self.game_controller.get_next_threshold()
        if self.game_controller.state.score >= threshold:
            options = self.reward_system.generate_options(
                self.game_controller.cycle_count,
                self.reward_system.unlocked_buffs,
            )
            self.reward_selector.show(options, self._on_reward_selected)
            self.game_controller.state.paused = True

    def _on_reward_selected(self, reward: dict) -> None:
        self.game_controller.on_reward_selected(reward, self.player)
        self.reward_selector.hide()

    def render(self, surface: pygame.Surface) -> None:
        entities = GameEntities(
            player=self.player,
            enemies=self.spawn_controller.enemies,
            boss=self.spawn_controller.boss,
        )
        self.game_renderer.render(surface, self.game_controller.state, entities)

        self._render_player_bullets(surface)
        self._render_enemy_bullets(surface)
        self._render_hud(surface)

        if self.reward_selector.visible:
            self.reward_selector.render(surface)

        if self._mother_ship_integrator:
            self._mother_ship_integrator.render(surface)

    def _render_player_bullets(self, surface: pygame.Surface) -> None:
        for bullet in self.player.get_bullets():
            bullet.render(surface)

    def _render_enemy_bullets(self, surface: pygame.Surface) -> None:
        for bullet in self.spawn_controller.enemy_bullets:
            bullet.render(surface)

    def _render_hud(self, surface: pygame.Surface) -> None:
        self.game_renderer.render_hud(
            surface,
            self.game_controller.state.score,
            self.game_controller.state.difficulty,
            self.player.health,
            self.player.max_health,
            self.game_controller.state.kill_count,
            self.game_controller.get_next_threshold(),
            self.game_controller.cycle_count,
            self.game_controller.milestone_index + self.game_controller.max_cycles,
            boss_kills=self.game_controller.state.boss_kill_count,
        )

        self.game_renderer.render_notification(
            surface,
            self.game_controller.state.notification,
            self.game_controller.state.notification_timer,
        )
        self.game_renderer.render_buff_stats_panel(surface, self.reward_system, self.player)

    @property
    def enemies(self) -> list:
        return self.spawn_controller.enemies if self.spawn_controller else []

    @property
    def score(self) -> int:
        return self.game_controller.state.score if self.game_controller else 0

    @score.setter
    def score(self, value: int) -> None:
        if self.game_controller:
            self.game_controller.state.score = value

    @property
    def cycle_count(self) -> int:
        return self.game_controller.cycle_count if self.game_controller else 0

    @cycle_count.setter
    def cycle_count(self, value: int) -> None:
        if self.game_controller:
            self.game_controller.cycle_count = value

    @property
    def kills(self) -> int:
        return self.game_controller.state.kill_count if self.game_controller else 0

    @kills.setter
    def kills(self, value: int) -> None:
        if self.game_controller:
            self.game_controller.state.kill_count = value

    @property
    def milestone_index(self) -> int:
        return self.game_controller.milestone_index if self.game_controller else 0

    @milestone_index.setter
    def milestone_index(self, value: int) -> None:
        if self.game_controller:
            self.game_controller.milestone_index = value

    @property
    def boss(self):
        return self.spawn_controller.boss if self.spawn_controller else None

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
    def paused(self) -> bool:
        return self.game_controller.state.paused if self.game_controller else False

    @paused.setter
    def paused(self, value: bool) -> None:
        if self.game_controller:
            self.game_controller.state.paused = value

    @property
    def unlocked_buffs(self) -> list:
        return self.reward_system.unlocked_buffs if self.reward_system else []

    @unlocked_buffs.setter
    def unlocked_buffs(self, value: list) -> None:
        if self.reward_system:
            self.reward_system.unlocked_buffs = value

    def _calculate_damage_taken(self, damage: int) -> int:
        return self.reward_system.calculate_damage_taken(damage)

    def _try_dodge(self) -> bool:
        return self.reward_system.try_dodge()

    def _get_current_threshold(self, index: int) -> float:
        return self.game_controller.get_current_threshold(index)

    def _get_next_threshold(self) -> float:
        return self.game_controller.get_next_threshold()

    @property
    def entrance_animation(self) -> bool:
        return self.game_controller.state.entrance_animation if self.game_controller else False

    @entrance_animation.setter
    def entrance_animation(self, value: bool) -> None:
        if self.game_controller:
            self.game_controller.state.entrance_animation = value

    @property
    def enemy_spawner(self):
        return self.spawn_controller.enemy_spawner if self.spawn_controller else None

    @property
    def notification(self) -> str:
        return self.game_controller.state.notification if self.game_controller else None

    @notification.setter
    def notification(self, value: str) -> None:
        if self.game_controller:
            self.game_controller.state.notification = value

    @property
    def difficulty(self) -> str:
        return self.game_controller.state.difficulty if self.game_controller else 'medium'

    @difficulty.setter
    def difficulty(self, value: str) -> None:
        if self.game_controller:
            self.game_controller.state.difficulty = value

    @property
    def entrance_timer(self) -> int:
        return self.game_controller.state.entrance_timer if self.game_controller else 0

    @entrance_timer.setter
    def entrance_timer(self, value: int) -> None:
        if self.game_controller:
            self.game_controller.state.entrance_timer = value

    @property
    def running(self) -> bool:
        return self.game_controller.state.running if self.game_controller else False

    @running.setter
    def running(self, value: bool) -> None:
        if self.game_controller:
            self.game_controller.state.running = value

    @property
    def notification_timer(self) -> int:
        return self.game_controller.state.notification_timer if self.game_controller else 0

    @notification_timer.setter
    def notification_timer(self, value: int) -> None:
        if self.game_controller:
            self.game_controller.state.notification_timer = value

    @property
    def entrance_duration(self) -> int:
        return self.game_controller.state.entrance_duration if self.game_controller else 60

    def restore_from_save(self, save_data) -> None:
        if not save_data or not self.game_controller or not self.player:
            return

        self.game_controller.state.score = save_data.score
        self.game_controller.state.kill_count = save_data.kill_count
        self.game_controller.state.boss_kill_count = save_data.boss_kill_count
        self.game_controller.milestone_index = save_data.milestone_index
        self.game_controller.cycle_count = save_data.cycle_count

        self.player.max_health = save_data.player_max_health
        self.player.health = min(save_data.player_health, save_data.player_max_health)

        self.reward_system.restore_runtime_state(
            self.player,
            save_data.unlocked_buffs,
            save_data.buff_levels,
            {
                'player_bullet_damage': save_data.player_bullet_damage,
                'player_fire_interval': save_data.player_fire_interval,
                'player_shot_mode': save_data.player_shot_mode,
                'player_speed': save_data.player_speed,
            },
        )

        self.game_controller.state.difficulty = save_data.difficulty
        self.game_controller.state.username = save_data.username
        self.game_controller.state.entrance_animation = False
        self.game_controller.state.entrance_timer = 0
        self.game_controller.state.paused = False

        if save_data.is_in_mothership:
            self._restore_to_mothership_state()
        else:
            self._restore_to_active_flight_state(save_data.player_x, save_data.player_y)

        self._cleanup_bullets()
        self._clear_enemy_bullets()

    def _restore_to_active_flight_state(self, player_x: int, player_y: int) -> None:
        from airwar.config import get_screen_width, get_screen_height

        screen_width = get_screen_width()
        screen_height = get_screen_height()
        if player_x == 0 and player_y == 0:
            player_x = screen_width // 2 - self.player.rect.width // 2
            player_y = screen_height - 100
        clamped_x = max(0, min(int(player_x), screen_width - self.player.rect.width))
        clamped_y = max(0, min(int(player_y), screen_height - self.player.rect.height))

        self.player.rect.x = clamped_x
        self.player.rect.y = clamped_y

    def _restore_to_mothership_state(self) -> None:
        if self._mother_ship_integrator:
            self._mother_ship_integrator.restore_docked_state()
        self.game_controller.state.entrance_animation = False
        self.game_controller.state.paused = False
