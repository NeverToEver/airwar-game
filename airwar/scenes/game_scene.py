import pygame
from .scene import Scene
from airwar.entities import Player, EnemySpawner, Boss, BossData
from airwar.game.systems.health_system import HealthSystem
from airwar.game.systems.reward_system import RewardSystem
from airwar.game.systems.hud_renderer import HUDRenderer
from airwar.game.systems.notification_manager import NotificationManager
from airwar.game.controllers.game_controller import GameController
from airwar.game.controllers.spawn_controller import SpawnController
from airwar.game.controllers.collision_controller import CollisionController
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
from airwar.game.constants import PlayerConstants, GAME_CONSTANTS


class GameScene(Scene):
    def __init__(self):
        self.game_controller: GameController = None
        self.game_renderer: GameRenderer = None
        self.health_system: HealthSystem = None
        self.reward_system: RewardSystem = None
        self.hud_renderer: HUDRenderer = None
        self.notification_manager: NotificationManager = None
        self.spawn_controller: SpawnController = None
        self.collision_controller: CollisionController = None
        self.player: Player = None
        self.reward_selector: RewardSelector = RewardSelector()
        self._mother_ship_integrator = None

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
        self.health_system = HealthSystem(difficulty)
        self.reward_system = self.game_controller.reward_system
        self.hud_renderer = HUDRenderer()
        self.notification_manager = self.game_controller.notification_manager

        self.spawn_controller = SpawnController(settings)
        self.spawn_controller.init_bullet_system()

        self.collision_controller = CollisionController()

        input_handler = PygameInputHandler()
        self.player = Player(
            screen_width // 2 - PlayerConstants.INITIAL_X_OFFSET,
            screen_height - PlayerConstants.SCREEN_BOTTOM_OFFSET,
            input_handler
        )
        self.player.rect.y = PlayerConstants.INITIAL_Y
        self.player.bullet_damage = settings['bullet_damage']

        self._setup_reward_selector()
        self._init_mother_ship_system(screen_width, screen_height)

    def _setup_reward_selector(self) -> None:
        self.reward_selector.show = lambda options, callback: self._show_reward_selection(options, callback)
        self.reward_selector.hide = lambda: setattr(self, 'reward_visible', False)
        self.reward_selector.visible = False

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
            if self._mother_ship_integrator:
                self._mother_ship_integrator.update()
            return

        if self._mother_ship_integrator:
            self._mother_ship_integrator.update()

            if self._mother_ship_integrator.is_docked():
                self._update_bullets_in_docked_state()
                return

            if self._mother_ship_integrator.is_player_control_disabled():
                self._update_bullets_in_docked_state()
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
            self.player.rect.y = screen_height - PlayerConstants.SCREEN_BOTTOM_OFFSET
        else:
            target_y = screen_height - PlayerConstants.SCREEN_BOTTOM_OFFSET
            start_y = PlayerConstants.INITIAL_Y
            self.player.rect.y = int(start_y + (target_y - start_y) * progress)
            self.player.rect.x = screen_width // 2 - PlayerConstants.INITIAL_X_OFFSET

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
            boss = self.spawn_controller.spawn_boss(
                self.game_controller.cycle_count,
                self.reward_system.base_bullet_damage
            )
            self.game_controller.show_notification(
                f"! BOSS APPROACHING ({int(boss.data.escape_time/60)}s) !"
            )
        
        if self.spawn_controller.boss:
            self._update_boss()

    def _update_boss(self) -> None:
        boss = self.spawn_controller.boss
        if not boss:
            return
        
        self._update_boss_movement(boss)
        self._check_boss_player_collision(boss)
        self._process_boss_damage(boss)
        self._handle_boss_escape(boss)
    
    def _update_boss_movement(self, boss) -> None:
        player_pos = (self.player.rect.centerx, self.player.rect.centery)
        boss.update(self.spawn_controller.enemies, player_pos=player_pos)
    
    def _check_boss_player_collision(self, boss) -> None:
        if boss.is_entering() or not boss.active:
            return
        
        if not boss.rect.colliderect(self.player.get_hitbox()):
            return
        
        if self.game_controller.state.player_invincible:
            return
        
        damage = self.reward_system.calculate_damage_taken(30)
        self.player.take_damage(damage)
        self._clear_enemy_bullets()
        self.game_controller.on_player_hit(damage, self.player)
    
    def _process_boss_damage(self, boss) -> None:
        if boss.is_entering() or not boss.active:
            return
        
        for bullet in self.player.get_bullets():
            if not self._is_valid_bullet_for_boss(bullet, boss):
                continue
            
            score_reward = boss.take_damage(bullet.data.damage)
            if score_reward > 0:
                self._on_boss_hit(score_reward)
    
    def _is_valid_bullet_for_boss(self, bullet, boss) -> bool:
        return (
            bullet.active and 
            boss.active and 
            not boss.is_entering() and
            bullet.get_rect().colliderect(boss.get_rect())
        )
    
    def _on_boss_hit(self, score_reward: int) -> None:
        self.game_controller.state.score += score_reward
        self.game_controller.show_notification(f"+{score_reward} BOSS SCORE!")
        
        if self.reward_system.piercing_level <= 0:
            pass
        
        if not self.spawn_controller.boss.active:
            self.game_controller.on_boss_killed(self.spawn_controller.boss.data.score)
            self.game_controller.cycle_count += 1
            self.reward_system.apply_lifesteal(self.player, self.spawn_controller.boss.data.score)
    
    def _handle_boss_escape(self, boss) -> None:
        if not boss or boss.active:
            return
        
        if boss.is_escaped():
            self.game_controller.show_notification("BOSS ESCAPED! (+0)")

    def _update_entities(self) -> None:
        for enemy in self.spawn_controller.enemies:
            enemy.update(self.spawn_controller.enemies, self.reward_system.slow_factor)
            enemy_hitbox = enemy.get_hitbox()
            player_hitbox = self.player.get_hitbox()
            if enemy_hitbox.colliderect(player_hitbox):
                if not self.reward_system.try_dodge():
                    self._clear_enemy_bullets()
                    self.game_controller.on_player_hit(20, self.player)

    def _check_collisions(self) -> None:
        if not self.collision_controller:
            self.collision_controller = CollisionController()
        
        self.collision_controller.check_all_collisions(
            player=self.player,
            enemies=self.spawn_controller.enemies,
            boss=self.spawn_controller.boss,
            enemy_bullets=self.spawn_controller.enemy_bullets,
            reward_system=self.reward_system,
            player_invincible=self.game_controller.state.player_invincible,
            score_multiplier=self.game_controller.state.score_multiplier,
            on_enemy_killed=lambda: None,
            on_boss_killed=lambda: self.game_controller.on_boss_killed(self.spawn_controller.boss.data.score if self.spawn_controller.boss else 0),
            on_boss_hit=lambda score: self._on_boss_hit(score),
            on_player_hit=lambda damage, player: self.game_controller.on_player_hit(damage, player),
            on_lifesteal=lambda player, score: self.reward_system.apply_lifesteal(player, score),
        )
    
    def _on_boss_hit(self, score: int) -> None:
        self.game_controller.state.score += score
        self.game_controller.show_notification(f"+{score} BOSS SCORE!")
        if not self.spawn_controller.boss.active:
            self.game_controller.cycle_count += 1
            self.reward_system.apply_lifesteal(self.player, self.spawn_controller.boss.data.score)
            self._clear_enemy_bullets()
    
    def _check_player_bullets_vs_enemies(self) -> None:
        if not self.collision_controller:
            self.collision_controller = CollisionController()
        
        score_gained, enemies_killed = self.collision_controller.check_player_bullets_vs_enemies(
            self.player.get_bullets(),
            self.spawn_controller.enemies,
            self.game_controller.state.score_multiplier,
            self.reward_system.explosive_level
        )
        
        for _ in range(enemies_killed):
            self.game_controller.on_enemy_killed(score_gained)
            self.reward_system.apply_lifesteal(self.player, 0)
    
    def _check_enemy_bullets_vs_player(self) -> None:
        if not self.collision_controller:
            self.collision_controller = CollisionController()
        
        self.collision_controller.check_enemy_bullets_vs_player(
            self.spawn_controller.enemy_bullets,
            self.player.get_hitbox(),
            lambda d: self.reward_system.calculate_damage_taken(d),
            lambda d: (
                self.player.take_damage(d),
                self._clear_enemy_bullets(),
                self.game_controller.on_player_hit(d, self.player)
            )
        )


    def _cleanup_bullets(self) -> None:
        for b in self.spawn_controller.enemy_bullets:
            if not b.active:
                self.spawn_controller.enemy_bullets.remove(b)

    def _update_bullets_in_docked_state(self) -> None:
        for bullet in self.player.get_bullets():
            bullet.update()
            if not bullet.active:
                self.player.remove_bullet(bullet)

    def _clear_enemy_bullets(self) -> None:
        for bullet in self.spawn_controller.enemy_bullets[:]:
            bullet.active = False
        self.spawn_controller.enemy_bullets.clear()

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

        if self._mother_ship_integrator:
            self._mother_ship_integrator.render(surface)

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
            self.game_controller.state.kill_count,
            self.game_controller.get_next_threshold(),
            self.game_controller.cycle_count,
            self.game_controller.milestone_index + self.game_controller.max_cycles,
            boss_kills=self.game_controller.state.boss_kill_count
        )

        self.game_renderer.render_notification(
            surface, self.game_controller.state.notification, self.game_controller.state.notification_timer)

        self.game_renderer.render_buff_stats_panel(
            surface, self.reward_system, self.player)

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
        return self.game_controller.cycle_count if self.game_controller else 0

    @kills.setter
    def kills(self, value: int) -> None:
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
        self.game_controller.milestone_index = save_data.cycle_count % self.game_controller.max_cycles
        self.game_controller.cycle_count = save_data.cycle_count

        self.player.health = save_data.player_health
        self.player.max_health = save_data.player_max_health

        self.reward_system.unlocked_buffs = save_data.unlocked_buffs
        self._restore_buff_levels(save_data.buff_levels)

        self.game_controller.state.difficulty = save_data.difficulty
        self.game_controller.state.username = save_data.username

        if save_data.is_in_mothership:
            self._restore_to_mothership_state()

    def _restore_buff_levels(self, buff_levels: dict) -> None:
        if not buff_levels:
            return
        self.reward_system.piercing_level = buff_levels.get('piercing_level', 0)
        self.reward_system.spread_level = buff_levels.get('spread_level', 0)
        self.reward_system.explosive_level = buff_levels.get('explosive_level', 0)
        self.reward_system.armor_level = buff_levels.get('armor_level', 0)
        self.reward_system.evasion_level = buff_levels.get('evasion_level', 0)
        self.reward_system.rapid_fire_level = buff_levels.get('rapid_fire_level', 0)

    def _restore_to_mothership_state(self) -> None:
        if self._mother_ship_integrator:
            self._mother_ship_integrator.reset_to_idle_with_mothership_visible()
        self.game_controller.state.entrance_animation = False
        self.game_controller.state.paused = False
        self.player.rect.y = PlayerConstants.MOTHERSHIP_Y_POSITION
        self.player.rect.x = self.game_controller.state.score // 2 % PlayerConstants.DEFAULT_SCREEN_WIDTH
