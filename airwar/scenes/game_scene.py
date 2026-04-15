import pygame
from .scene import Scene
from airwar.entities import Player, Enemy, EnemySpawner, EnemyData, Boss, BossData
from airwar.game.systems.health_system import HealthSystem
from airwar.game.systems.reward_system import RewardSystem
from airwar.game.systems.hud_renderer import HUDRenderer
from airwar.game.systems.notification_manager import NotificationManager
from airwar.game.controllers.game_controller import GameController, GameState
from airwar.game.rendering.game_renderer import GameRenderer, GameEntities


class RewardSelector:
    def __init__(self):
        self.visible = False
        self.selected_index = 0
        self.options = []
        self.on_select = None
        self.animation_time = 0

    def generate_options(self, cycle_count: int, unlocked_buffs: list) -> list:
        return []

    def show(self, options: list, callback) -> None:
        self.visible = True
        self.options = options
        self.selected_index = 0
        self.on_select = callback
        self.animation_time = 0

    def hide(self) -> None:
        self.visible = False
        self.options = []

    def handle_input(self, event: pygame.event.Event) -> None:
        if not self.visible:
            return

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected_index = (self.selected_index - 1) % len(self.options)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected_index = (self.selected_index + 1) % len(self.options)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._confirm_selection()

    def _confirm_selection(self) -> None:
        if self.on_select and self.options:
            selected = self.options[self.selected_index]
            self.on_select(selected)
        self.hide()

    def update(self) -> None:
        if self.visible:
            self.animation_time += 1

    def render(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return

        width, height = surface.get_size()

        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((8, 8, 25, 240))
        surface.blit(overlay, (0, 0))

        title = pygame.font.Font(None, 60).render("CHOOSE YOUR REWARD", True, (255, 255, 255))
        surface.blit(title, title.get_rect(center=(width // 2, 100)))

        box_width = 580
        box_height = 110
        start_y = 180
        start_x = width // 2 - box_width // 2

        for i, option in enumerate(self.options):
            y = start_y + i * (box_height + 35)
            x = start_x

            is_selected = i == self.selected_index
            box_color = (35, 55, 85) if is_selected else (22, 28, 48)
            border_color = (0, 255, 150) if is_selected else (70, 90, 130)

            box_rect = pygame.Rect(x, y, box_width, box_height)

            if is_selected:
                glow_rect = box_rect.inflate(8, 8)
                glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (0, 255, 150, 40), glow_surf.get_rect(), border_radius=15)
                surface.blit(glow_surf, glow_rect)

            pygame.draw.rect(surface, box_color, box_rect, border_radius=12)
            pygame.draw.rect(surface, border_color, box_rect, 3 if is_selected else 2, border_radius=12)

            icon_box_width = 85
            icon_box_rect = pygame.Rect(x + 12, y + 12, icon_box_width, box_height - 24)
            pygame.draw.rect(surface, (28, 38, 60), icon_box_rect, border_radius=8)
            pygame.draw.rect(surface, border_color, icon_box_rect, 1, border_radius=8)

            arrow = ">>> " if is_selected else "    "
            icon_text = pygame.font.Font(None, 32).render(f"{arrow}{option['icon']}", True,
                                                        (0, 255, 150) if is_selected else (140, 140, 160))
            icon_text_rect = icon_text.get_rect(center=(x + 12 + icon_box_width // 2, y + box_height // 2))
            surface.blit(icon_text, icon_text_rect)

            text_x = x + icon_box_width + 35

            name_text = pygame.font.Font(None, 38).render(option['name'], True,
                                                        (255, 255, 255) if is_selected else (200, 200, 220))
            surface.blit(name_text, (text_x, y + 22))

            desc_text = pygame.font.Font(None, 28).render(option['desc'], True,
                                                        (160, 210, 160) if is_selected else (100, 110, 140))
            surface.blit(desc_text, (text_x, y + 62))

        hint = pygame.font.Font(None, 26).render("W/S or UP/DOWN to select, ENTER to confirm", True, (90, 110, 140))
        surface.blit(hint, hint.get_rect(center=(width // 2, height - 60)))


class GameScene(Scene):
    def __init__(self):
        self.game_controller: GameController = None
        self.game_renderer: GameRenderer = None
        self.health_system: HealthSystem = None
        self.reward_system: RewardSystem = None
        self.hud_renderer: HUDRenderer = None
        self.notification_manager: NotificationManager = None
        self.player: Player = None
        self.enemies = []
        self.enemy_bullets = []
        self.boss = None
        self.reward_selector: RewardSelector = RewardSelector()

    def enter(self, **kwargs) -> None:
        from airwar.config import DIFFICULTY_SETTINGS, get_screen_width, get_screen_height
        from airwar.input import PygameInputHandler
        from airwar.game import EnemyBulletSpawner

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

        input_handler = PygameInputHandler()
        self.player = Player(screen_width // 2 - 25, screen_height - 100, input_handler)
        self.player.rect.y = -80
        self.player.bullet_damage = settings['bullet_damage']

        self.enemies = []
        self.enemy_bullets = []
        enemy_bullet_spawner = EnemyBulletSpawner(self.enemy_bullets)
        self.enemy_spawner = EnemySpawner()
        self.enemy_spawner.set_bullet_spawner(enemy_bullet_spawner)
        self.enemy_spawner.set_params(
            health=settings['enemy_health'],
            speed=settings['enemy_speed'],
            spawn_rate=settings['spawn_rate']
        )

        self.boss = None
        self.boss_spawn_timer = 0
        self.boss_spawn_interval = 1800

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
            if event.key == pygame.K_ESCAPE:
                if not self.reward_selector.visible:
                    self.game_controller.state.paused = not self.game_controller.state.paused
            elif event.key == pygame.K_SPACE:
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

        self.enemies = [e for e in self.enemies if e.active]
        self._cleanup_bullets()

        if not self.player.active:
            self.game_controller.state.running = False

    def _update_enemy_spawning(self) -> None:
        self.enemy_spawner.update(self.enemies, self.reward_system.slow_factor)

        if self.boss is None:
            self.boss_spawn_timer += 1
            spawn_interval = int(self.boss_spawn_interval * (1.0 / self.reward_system.slow_factor))
            if self.boss_spawn_timer >= spawn_interval:
                self.boss_spawn_timer = 0
                self._spawn_boss()
        else:
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
        enemy_bullet_spawner = EnemyBulletSpawner(self.enemy_bullets)
        boss = Boss(screen_width // 2 - boss_data.width // 2, -100, boss_data)
        boss.set_bullet_spawner(enemy_bullet_spawner)
        self.boss = boss
        self.game_controller.show_notification(f"! BOSS APPROACHING ({int(escape_time/60)}s) !")

    def _update_boss(self) -> None:
        self.boss.update()
        player_hitbox = self.player.get_hitbox()

        if not self.boss.is_entering() and self.boss.active:
            if self.boss.rect.colliderect(player_hitbox):
                if not self.game_controller.state.player_invincible:
                    damage = self.reward_system.calculate_damage_taken(30)
                    self.player.take_damage(damage)
                    self.game_controller.on_player_hit(damage, self.player)

        for bullet in self.player.get_bullets():
            if bullet.active and self.boss and self.boss.active and not self.boss.is_entering():
                if bullet.get_rect().colliderect(self.boss.get_rect()):
                    score_reward = self.boss.take_damage(bullet.data.damage)
                    if score_reward > 0:
                        self.game_controller.state.score += score_reward
                        self.game_controller.show_notification(f"+{score_reward} BOSS SCORE!")

                    if self.reward_system.piercing_level <= 0:
                        bullet.active = False

                    if not self.boss.active:
                        self.game_controller.cycle_count += 1
                        self.reward_system.apply_lifesteal(self.player, self.boss.data.score)
                        self.boss = None

        if self.boss and not self.boss.active:
            if self.boss.is_escaped():
                self.game_controller.show_notification("BOSS ESCAPED! (+0)")
            self.boss = None

    def _update_entities(self) -> None:
        for enemy in self.enemies:
            enemy.update()
            if enemy.rect.colliderect(self.player.get_hitbox()):
                if not self.reward_system.try_dodge():
                    self.game_controller.on_player_hit(20, self.player)

    def _check_collisions(self) -> None:
        self._check_player_bullets_vs_enemies()
        self._check_enemy_bullets_vs_player()

    def _check_player_bullets_vs_enemies(self) -> None:
        for bullet in self.player.get_bullets():
            for enemy in self.enemies:
                if bullet.active and enemy.active:
                    if bullet.get_rect().colliderect(enemy.get_rect()):
                        if self.reward_system.explosive_level > 0:
                            self.reward_system.do_explosive_damage(
                                self.enemies, enemy.rect.centerx, enemy.rect.centery, bullet.data.damage)
                        else:
                            enemy.take_damage(bullet.data.damage)

                        if self.reward_system.piercing_level <= 0:
                            bullet.active = False

                        if not enemy.active:
                            self.game_controller.state.score += enemy.data.score * self.game_controller.state.score_multiplier
                            self.reward_system.apply_lifesteal(self.player, enemy.data.score)

    def _check_enemy_bullets_vs_player(self) -> None:
        player_hitbox = self.player.get_hitbox()
        for eb in self.enemy_bullets:
            eb.update()
            if eb.active and eb.rect.colliderect(player_hitbox):
                if not self.game_controller.state.player_invincible:
                    damage = self.reward_system.calculate_damage_taken(eb.data.damage)
                    self.player.take_damage(damage)
                    self.game_controller.on_player_hit(damage, self.player)

    def _cleanup_bullets(self) -> None:
        self.enemy_bullets = [b for b in self.enemy_bullets if b.active]

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
            enemies=self.enemies,
            boss=self.boss
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
        for eb in self.enemy_bullets:
            eb.render(surface)

    def _render_hud(self, surface: pygame.Surface) -> None:
        self.game_renderer.render_hud(
            surface,
            self.game_controller.state.score,
            self.game_controller.state.difficulty,
            self.player.health,
            self.player.max_health,
            self.game_controller.cycle_count,
            self.game_controller.get_next_threshold(),
            self.game_controller.cycle_count,
            self.game_controller.milestone_index + self.game_controller.max_cycles
        )

        self.game_renderer.render_notification(
            surface, self.game_controller.state.notification, self.game_controller.state.notification_timer)

    def get_score(self) -> int:
        return self.game_controller.state.score if self.game_controller else 0

    def get_kills(self) -> int:
        return self.game_controller.cycle_count if self.game_controller else 0

    def is_game_over(self) -> bool:
        return not self.player.active if self.player else True

    def is_paused(self) -> bool:
        return self.game_controller.state.paused if self.game_controller else False

    def pause(self) -> None:
        if self.game_controller and not self.reward_selector.visible:
            self.game_controller.state.paused = True

    def resume(self) -> None:
        if self.game_controller and not self.reward_selector.visible:
            self.game_controller.state.paused = False

    @property
    def unlocked_buffs(self) -> list:
        return self.reward_system.unlocked_buffs if self.reward_system else []

    @unlocked_buffs.setter
    def unlocked_buffs(self, value: list) -> None:
        if self.reward_system:
            self.reward_system.unlocked_buffs = value
