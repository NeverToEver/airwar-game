import pygame
from .scene import Scene
from airwar.entities import Player, Enemy, EnemySpawner, EnemyData, Boss, BossData
from airwar.game.systems.health_system import HealthSystem
from airwar.game.systems.reward_system import RewardSystem, REWARD_POOL
from airwar.game.systems.hud_renderer import HUDRenderer


class RewardSelector:
    def __init__(self):
        self.visible = False
        self.selected_index = 0
        self.options = []
        self.on_select = None
        self.animation_time = 0

    def generate_options(self, cycle_count: int, unlocked_buffs: list) -> list:
        from airwar.game.systems.reward_system import REWARD_POOL
        import random
        options = []
        categories = list(REWARD_POOL.keys())

        for _ in range(3):
            cat = random.choice(categories)
            rewards = REWARD_POOL[cat]

            if cat == 'offense' and cycle_count > 2:
                rewards = [r for r in rewards if r['name'] not in ['Spread Shot', 'Explosive']]

            reward = random.choice(rewards)
            attempts = 0
            while reward in options and attempts < 10:
                reward = random.choice(rewards)
                attempts += 1

            options.append(reward)

        return options

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
        self.health_system = None
        self.reward_system = None
        self.hud_renderer = None

    def enter(self, **kwargs) -> None:
        from airwar.config import DIFFICULTY_SETTINGS, get_screen_width, get_screen_height
        from airwar.input import PygameInputHandler
        from airwar.game import EnemyBulletSpawner

        screen_width = get_screen_width()
        screen_height = get_screen_height()

        difficulty = kwargs.get('difficulty', 'medium')
        self.username = kwargs.get('username', 'Player')
        settings = DIFFICULTY_SETTINGS[difficulty]

        input_handler = PygameInputHandler()
        self.player = Player(screen_width // 2 - 25, screen_height - 100, input_handler)
        self.player.rect.y = -80

        self.entrance_animation = True
        self.entrance_timer = 0
        self.entrance_duration = 60
        self.player.bullet_damage = settings['bullet_damage']
        self.enemies = []
        self.enemy_bullets = []
        
        self.enemy_bullet_spawner = EnemyBulletSpawner(self.enemy_bullets)
        self.enemy_spawner = EnemySpawner()
        self.enemy_spawner.set_bullet_spawner(self.enemy_bullet_spawner)
        self.enemy_spawner.set_params(
            health=settings['enemy_health'],
            speed=settings['enemy_speed'],
            spawn_rate=settings['spawn_rate']
        )
        self.score = 0
        self.kills = 0
        self.difficulty = difficulty
        self.score_multiplier = self._get_score_multiplier(difficulty)
        self.running = True
        self.paused = False

        self.milestone_index = 0
        self.cycle_count = 0
        self.base_thresholds = [1000, 2500, 5000, 10000, 20000]
        self.max_cycles = 10
        self.cycle_multiplier = 1.5

        self.difficulty_threshold_multiplier = {'easy': 1.0, 'medium': 1.5, 'hard': 2.0}[difficulty]

        self.reward_selector = RewardSelector()
        self.notification = None
        self.notification_timer = 0

        self.player_invincible = False
        self.invincibility_timer = 0
        self.ripple_effects = []

        self.boss = None
        self.boss_spawn_timer = 0
        self.boss_spawn_interval = 1800
        self.boss_killed = False

        self.health_system = HealthSystem(difficulty)
        self.reward_system = RewardSystem()
        self.hud_renderer = HUDRenderer()

    def _get_score_multiplier(self, difficulty: str) -> int:
        return {'easy': 1, 'medium': 2, 'hard': 3}[difficulty]

    def _spawn_boss(self) -> None:
        from airwar.config import get_screen_width
        screen_width = get_screen_width()
        base_health = 500 * (1 + self.cycle_count * 0.5)
        escape_time = int(base_health / self.player.bullet_damage * 2.5)
        escape_time = max(600, min(escape_time, 1800))

        boss_data = BossData(
            health=base_health,
            speed=1.5 + self.cycle_count * 0.1,
            score=5000 + self.cycle_count * 1000,
            width=120,
            height=100,
            fire_rate=60 - self.cycle_count * 3,
            phase=1,
            escape_time=escape_time
        )
        boss = Boss(screen_width // 2 - boss_data.width // 2, -100, boss_data)
        boss.set_bullet_spawner(self.enemy_bullet_spawner)
        self.boss = boss
        self._show_notification(f"! BOSS APPROACHING ({int(escape_time/60)}s) !")

    def _show_notification(self, message: str) -> None:
        self.notification = message
        self.notification_timer = 90

    def _get_current_threshold(self, index: int) -> float:
        base = self.base_thresholds[index % len(self.base_thresholds)]
        cycle_bonus = index // len(self.base_thresholds)
        return base * (self.cycle_multiplier ** cycle_bonus) * self.difficulty_threshold_multiplier

    def _get_next_threshold(self) -> float:
        return self._get_current_threshold(self.milestone_index)

    def exit(self) -> None:
        pass

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if not self.reward_selector.visible:
                    self.paused = not self.paused
            elif event.key == pygame.K_SPACE:
                if not self.paused and not self.reward_selector.visible:
                    self.player.fire()

        self.reward_selector.handle_input(event)

    def update(self, *args, **kwargs) -> None:
        self.reward_selector.update()

        if self.entrance_animation:
            self._update_entrance_animation()
            return

        if self.paused or self.reward_selector.visible:
            return

        self._update_game_logic()

    def _update_entrance_animation(self) -> None:
        from airwar.config import get_screen_width, get_screen_height
        self.entrance_timer += 1
        screen_width = get_screen_width()
        screen_height = get_screen_height()
        progress = self.entrance_timer / self.entrance_duration
        if progress >= 1.0:
            self.entrance_animation = False
            self.player.rect.y = screen_height - 100
        else:
            target_y = screen_height - 100
            start_y = -80
            self.player.rect.y = int(start_y + (target_y - start_y) * progress)
            self.player.rect.x = screen_width // 2 - 25

    def _update_game_logic(self) -> None:
        self.health_system.update(self.player, 'Regeneration' in self.reward_system.unlocked_buffs)
        self._update_invincibility()
        self._update_ripples()

        keys = pygame.key.get_pressed()
        self.player.update()
        self.player.auto_fire()

        self.enemy_spawner.update(self.enemies, self.reward_system.slow_factor)

        if self.boss is None:
            self.boss_spawn_timer += 1
            spawn_interval = int(self.boss_spawn_interval * (1.0 / self.reward_system.slow_factor))
            if self.boss_spawn_timer >= spawn_interval:
                self.boss_spawn_timer = 0
                self._spawn_boss()
        else:
            self._update_boss()

        self._update_enemies()
        self._update_bullets()
        self._update_enemy_bullets()

        self.enemies = [e for e in self.enemies if e.active]
        self.enemy_bullets = [b for b in self.enemy_bullets if b.active]

        if self.notification_timer > 0:
            self.notification_timer -= 1

        if not self.player.active:
            self.running = False

    def _update_boss(self) -> None:
        self.boss.update()
        player_hitbox = self.player.get_hitbox()
        if not self.boss.is_entering() and self.boss.active:
            if self.boss.rect.colliderect(player_hitbox):
                if not self.player_invincible:
                    damage = self.reward_system.calculate_damage_taken(30)
                    self.player.take_damage(damage)
                    self._on_player_hit(damage)

        for bullet in self.player.get_bullets():
            if bullet.active and self.boss and self.boss.active and not self.boss.is_entering():
                if bullet.get_rect().colliderect(self.boss.get_rect()):
                    score_reward = self.boss.take_damage(bullet.data.damage)
                    if score_reward > 0:
                        self.score += score_reward
                        self._show_notification(f"+{score_reward} BOSS SCORE!")
                    if self.reward_system.piercing_level <= 0:
                        bullet.active = False
                    if not self.boss.active:
                        self.kills += 1
                        self.reward_system.apply_lifesteal(self.player, self.boss.data.score)
                        self._check_milestones()
                        self.boss = None

        if self.boss and not self.boss.active:
            if self.boss.is_escaped():
                self._show_notification("BOSS ESCAPED! (+0)")
            self.boss = None

    def _update_enemies(self) -> None:
        for enemy in self.enemies:
            enemy.update()
            if enemy.rect.colliderect(self.player.get_hitbox()):
                if not self.reward_system.try_dodge():
                    self._on_player_hit(20)

    def _update_bullets(self) -> None:
        for bullet in self.player.get_bullets():
            for enemy in self.enemies:
                if bullet.active and enemy.active:
                    if bullet.get_rect().colliderect(enemy.get_rect()):
                        damage = bullet.data.damage
                        if self.reward_system.explosive_level > 0:
                            self.reward_system.do_explosive_damage(
                                self.enemies, enemy.rect.centerx, enemy.rect.centery, damage)
                        else:
                            enemy.take_damage(damage)

                        if self.reward_system.piercing_level <= 0:
                            bullet.active = False

                        if not enemy.active:
                            self.kills += 1
                            self.score += enemy.data.score * self.score_multiplier
                            self.reward_system.apply_lifesteal(self.player, enemy.data.score)
                            self._check_milestones()

    def _update_enemy_bullets(self) -> None:
        for eb in self.enemy_bullets:
            eb.update()
            player_hitbox = self.player.get_hitbox()
            if eb.active and eb.rect.colliderect(player_hitbox):
                if not self.player_invincible:
                    damage = self.reward_system.calculate_damage_taken(eb.data.damage)
                    self.player.take_damage(damage)
                    self._on_player_hit(damage)

    def _on_player_hit(self, damage: int) -> None:
        center_x = self.player.rect.centerx
        center_y = self.player.rect.centery
        self.ripple_effects.append({'x': center_x, 'y': center_y, 'radius': 10, 'alpha': 255})
        self.enemy_bullets.clear()
        self.player_invincible = True
        self.invincibility_timer = 90

    def _update_invincibility(self) -> None:
        if self.player_invincible:
            self.invincibility_timer -= 1
            if self.invincibility_timer <= 0:
                self.player_invincible = False

    def _update_ripples(self) -> None:
        for ripple in self.ripple_effects:
            ripple['radius'] += 3
            ripple['alpha'] -= 8
        self.ripple_effects = [r for r in self.ripple_effects if r['alpha'] > 0]

    def _check_milestones(self) -> None:
        if self.cycle_count >= self.max_cycles:
            return

        threshold = self._get_next_threshold()
        if self.score >= threshold:
            options = self.reward_selector.generate_options(
                self.cycle_count, self.reward_system.unlocked_buffs)
            self.reward_selector.show(options, self._on_reward_selected)
            self.paused = True

    def _on_reward_selected(self, reward: dict) -> None:
        notification = self.reward_system.apply_reward(reward, self.player)
        self.milestone_index += 1
        if self.milestone_index % len(self.base_thresholds) == 0:
            self.cycle_count += 1

        self.notification = notification
        self.notification_timer = 90
        self.paused = False

    def render(self, surface: pygame.Surface) -> None:
        surface.fill((0, 0, 0))

        if self.entrance_animation:
            self._render_entrance_animation(surface)
        else:
            self._render_game(surface)

    def _render_entrance_animation(self, surface: pygame.Surface) -> None:
        progress = self.entrance_timer / self.entrance_duration
        zoom_scale = 1.0 + (1.5 - 1.0) * (1 - progress)

        if not self.player_invincible or (self.invincibility_timer // 5) % 2 == 0:
            self.player.render(surface)

        for enemy in self.enemies:
            enemy.render(surface)

        if self.boss:
            self.boss.render(surface)

        for eb in self.enemy_bullets:
            eb.render(surface)

        center_x = surface.get_width() // 2
        center_y = surface.get_height() // 2

        scaled_width = int(surface.get_width() * zoom_scale)
        scaled_height = int(surface.get_height() * zoom_scale)
        scaled_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        scaled_surface.blit(surface, (0, 0))
        scaled_surface = pygame.transform.scale(scaled_surface, (scaled_width, scaled_height))

        x_offset = (scaled_width - surface.get_width()) // 2
        y_offset = (scaled_height - surface.get_height()) // 2
        surface.fill((0, 0, 0))
        surface.blit(scaled_surface, (-x_offset, -y_offset))

        fade_surface = pygame.Surface((surface.get_width(), surface.get_height()))
        fade_surface.set_alpha(int(80 * (1 - progress)))
        surface.blit(fade_surface, (0, 0))

    def _render_game(self, surface: pygame.Surface) -> None:
        if not self.player_invincible or (self.invincibility_timer // 5) % 2 == 0:
            self.player.render(surface)

        for enemy in self.enemies:
            enemy.render(surface)

        if self.boss:
            self.boss.render(surface)
            self.hud_renderer.render_boss_health_bar(surface, self.boss)

        for eb in self.enemy_bullets:
            eb.render(surface)

        self.hud_renderer.render_ripples(surface, self.ripple_effects)

        self.hud_renderer.render_hud(
            surface, self.score, self.difficulty,
            self.player.health, self.player.max_health, self.kills,
            self._get_next_threshold(), self.cycle_count, self.max_cycles)

        self.hud_renderer.render_buffs(
            surface, self.reward_system.unlocked_buffs, self.reward_system.get_buff_color)

        self.hud_renderer.render_notification(surface, self.notification, self.notification_timer)

        if self.reward_selector.visible:
            self.reward_selector.render(surface)

    def get_score(self) -> int:
        return self.score

    def get_kills(self) -> int:
        return self.kills

    def is_game_over(self) -> bool:
        return not self.player.active

    def is_paused(self) -> bool:
        return self.paused

    def pause(self) -> None:
        if not self.reward_selector.visible:
            self.paused = True

    def resume(self) -> None:
        if not self.reward_selector.visible:
            self.paused = False

    @property
    def unlocked_buffs(self) -> list:
        return self.reward_system.unlocked_buffs

    @unlocked_buffs.setter
    def unlocked_buffs(self, value: list) -> None:
        self.reward_system.unlocked_buffs = value

    def _calculate_damage_taken(self, damage: int) -> int:
        return self.reward_system.calculate_damage_taken(damage)

    def _try_dodge(self) -> bool:
        return self.reward_system.try_dodge()

    def _do_explosive_damage(self, x: int, y: int, damage: int) -> None:
        self.reward_system.do_explosive_damage(self.enemies, x, y, damage)

