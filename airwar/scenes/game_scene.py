import pygame
from .scene import Scene
from airwar.entities import Player, Enemy, EnemySpawner, EnemyData, Boss, BossData


REWARD_POOL = {
    'health': [
        {'name': 'Extra Life', 'desc': '+50 Max HP, +30 HP', 'icon': 'HP'},
        {'name': 'Regeneration', 'desc': 'Passively heal 2 HP/sec', 'icon': 'REG'},
        {'name': 'Lifesteal', 'desc': '+10% lifesteal on kill', 'icon': 'LST'},
    ],
    'offense': [
        {'name': 'Power Shot', 'desc': '+25% bullet damage', 'icon': 'DMG'},
        {'name': 'Rapid Fire', 'desc': '+20% fire rate', 'icon': 'RPD'},
        {'name': 'Piercing', 'desc': 'Bullets pierce 1 enemy', 'icon': 'PIR'},
        {'name': 'Spread Shot', 'desc': 'Fire 3 bullets at once', 'icon': 'SPD'},
        {'name': 'Explosive', 'desc': 'Bullets deal 30 AoE damage', 'icon': 'EXP'},
    ],
    'defense': [
        {'name': 'Shield', 'desc': 'Block next hit', 'icon': 'SHD'},
        {'name': 'Armor', 'desc': '-15% damage taken', 'icon': 'ARM'},
        {'name': 'Evasion', 'desc': '+20% dodge chance', 'icon': 'EVD'},
        {'name': 'Barrier', 'desc': 'Gain 50 temporary HP', 'icon': 'BAR'},
    ],
    'utility': [
        {'name': 'Speed Boost', 'desc': '+15% move speed', 'icon': 'SPD'},
        {'name': 'Magnet', 'desc': '+30% score pickup range', 'icon': 'MAG'},
        {'name': 'Slow Field', 'desc': 'Slow enemies by 20%', 'icon': 'SLO'},
    ],
}


class RewardSelector:
    def __init__(self):
        self.visible = False
        self.selected_index = 0
        self.options = []
        self.on_select = None
        self.animation_time = 0

    def generate_options(self, cycle_count: int, unlocked_buffs: list) -> list:
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
    def enter(self, **kwargs) -> None:
        from airwar.config import SCREEN_WIDTH, SCREEN_HEIGHT, DIFFICULTY_SETTINGS

        difficulty = kwargs.get('difficulty', 'medium')
        self.username = kwargs.get('username', 'Player')
        settings = DIFFICULTY_SETTINGS[difficulty]

        self.player = Player(SCREEN_WIDTH // 2 - 25, SCREEN_HEIGHT - 100)
        self.player.rect.y = -80

        self.entrance_animation = True
        self.entrance_timer = 0
        self.entrance_duration = 60
        self.player.bullet_damage = settings['bullet_damage']
        self.enemies = []
        self.enemy_bullets = []
        self.enemy_spawner = EnemySpawner()
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

        self.unlocked_buffs = []
        self.pending_reward = None

        self.piercing_level = 0
        self.spread_level = 0
        self.explosive_level = 0
        self.armor_level = 0
        self.evasion_level = 0
        self.regen_timer = 0
        self.lifesteal_total = 0
        self.magnet_range = 0
        self.slow_factor = 1.0

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

        pygame.font.init()
        self.hud_font = pygame.font.Font(None, 26)
        self.buff_font = pygame.font.Font(None, 20)
        self.notif_font = pygame.font.Font(None, 32)

    def _get_score_multiplier(self, difficulty: str) -> int:
        return {'easy': 1, 'medium': 2, 'hard': 3}[difficulty]

    def _spawn_boss(self) -> None:
        from airwar.config import SCREEN_WIDTH
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
        boss = Boss(SCREEN_WIDTH // 2 - boss_data.width // 2, -100, boss_data)
        boss.set_game_scene(self)
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
            self.entrance_timer += 1
            from airwar.config import SCREEN_HEIGHT, SCREEN_WIDTH
            progress = self.entrance_timer / self.entrance_duration
            if progress >= 1.0:
                self.entrance_animation = False
                self.player.rect.y = SCREEN_HEIGHT - 100
            else:
                target_y = SCREEN_HEIGHT - 100
                start_y = -80
                self.player.rect.y = int(start_y + (target_y - start_y) * progress)
                self.player.rect.x = SCREEN_WIDTH // 2 - 25
            return

        if self.paused or self.reward_selector.visible:
            return

        self._update_regeneration()
        self._update_invincibility()
        self._update_ripples()

        keys = pygame.key.get_pressed()
        self.player.update(keys=keys)
        self.player.auto_fire()

        self.enemy_spawner.update(self.enemies, self.slow_factor, self)

        if self.boss is None:
            self.boss_spawn_timer += 1
            spawn_interval = int(self.boss_spawn_interval * (1.0 / self.slow_factor))
            if self.boss_spawn_timer >= spawn_interval:
                self.boss_spawn_timer = 0
                self._spawn_boss()
        else:
            self.boss.update()
            player_hitbox = self.player.get_hitbox()
            if not self.boss.is_entering() and self.boss.active:
                if self.boss.rect.colliderect(player_hitbox):
                    if not self.player_invincible:
                        damage = 30
                        damage = self._calculate_damage_taken(damage)
                        self.player.take_damage(damage)
                        self._on_player_hit(damage)

            for bullet in self.player.get_bullets():
                if bullet.active and self.boss and self.boss.active and not self.boss.is_entering():
                    if bullet.get_rect().colliderect(self.boss.get_rect()):
                        bullet_damage = bullet.data.damage
                        score_reward = self.boss.take_damage(bullet_damage)
                        if score_reward > 0:
                            self.score += score_reward
                            self._show_notification(f"+{score_reward} BOSS SCORE!")
                        if self.piercing_level <= 0:
                            bullet.active = False
                        if not self.boss.active:
                            self.kills += 1
                            self._on_enemy_killed()
                            self._check_milestones()
                            self.boss = None

            if self.boss and not self.boss.active:
                if self.boss.is_escaped():
                    self._show_notification("BOSS ESCAPED! (+0)")
                self.boss = None

        for enemy in self.enemies:
            enemy.update()

            if enemy.rect.colliderect(self.player.get_hitbox()):
                if self._try_dodge():
                    pass
                else:
                    self._on_player_hit(20)

        for bullet in self.player.get_bullets():
            for enemy in self.enemies:
                if bullet.active and enemy.active:
                    if bullet.get_rect().colliderect(enemy.get_rect()):
                        damage = bullet.data.damage
                        if self.explosive_level > 0:
                            self._do_explosive_damage(enemy.rect.centerx, enemy.rect.centery, damage)
                        else:
                            enemy.take_damage(damage)

                        if self.piercing_level <= 0:
                            bullet.active = False

                        if not enemy.active:
                            self.kills += 1
                            self.score += enemy.data.score * self.score_multiplier
                            self._on_enemy_killed()
                            self._check_milestones()

        for eb in self.enemy_bullets:
            eb.update()
            player_hitbox = self.player.get_hitbox()
            if eb.active and eb.rect.colliderect(player_hitbox):
                if not self.player_invincible:
                    damage = eb.data.damage
                    damage = self._calculate_damage_taken(damage)
                    self.player.take_damage(damage)
                    self._on_player_hit(damage)

        self.enemies = [e for e in self.enemies if e.active]
        self.enemy_bullets = [b for b in self.enemy_bullets if b.active]

        if self.notification_timer > 0:
            self.notification_timer -= 1

        if not self.player.active:
            self.running = False

    def _update_regeneration(self) -> None:
        from airwar.config import HEALTH_REGEN
        regen_settings = HEALTH_REGEN[self.difficulty]

        if 'Regeneration' not in self.unlocked_buffs:
            self.regen_timer += 1
            if self.regen_timer >= regen_settings['delay']:
                self.regen_timer = regen_settings['delay']
                self.regen_active = True

            if getattr(self, 'regen_active', False):
                self.regen_interval_timer = getattr(self, 'regen_interval_timer', 0) + 1
                if self.regen_interval_timer >= regen_settings['interval']:
                    self.regen_interval_timer = 0
                    self.player.health = min(self.player.health + regen_settings['rate'], self.player.max_health)
        else:
            self.regen_timer += 1
            if self.regen_timer >= 60:
                self.regen_timer = 0
                self.player.health = min(self.player.health + 2, self.player.max_health)

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

    def _on_enemy_killed(self) -> None:
        if 'Lifesteal' in self.unlocked_buffs:
            heal = int(self.player.max_health * 0.1)
            self.player.health = min(self.player.health + heal, self.player.max_health)

    def _try_dodge(self) -> bool:
        if 'Evasion' in self.unlocked_buffs:
            import random
            dodge_chance = 0.2
            if random.random() < dodge_chance:
                return True
        return False

    def _calculate_damage_taken(self, damage: int) -> int:
        if 'Armor' in self.unlocked_buffs:
            return int(damage * 0.85)
        return damage

    def _do_explosive_damage(self, x: int, y: int, damage: int) -> None:
        for enemy in self.enemies:
            if enemy.active:
                dist = ((enemy.rect.centerx - x) ** 2 + (enemy.rect.centery - y) ** 2) ** 0.5
                if dist < 60:
                    enemy.take_damage(int(damage * 0.5))

    def _check_milestones(self) -> None:
        if self.cycle_count >= self.max_cycles:
            return

        threshold = self._get_next_threshold()
        if self.score >= threshold:
            options = self.reward_selector.generate_options(self.cycle_count, self.unlocked_buffs)
            self.reward_selector.show(options, self._on_reward_selected)
            self.paused = True

    def _on_reward_selected(self, reward: dict) -> None:
        name = reward['name']
        self.unlocked_buffs.append(name)

        if name == 'Extra Life':
            self.player.max_health += 50
            self.player.health += 30

        elif name == 'Regeneration':
            pass

        elif name == 'Lifesteal':
            pass

        elif name == 'Power Shot':
            self.player.bullet_damage = int(self.player.bullet_damage * 1.25)

        elif name == 'Rapid Fire':
            self.player.fire_cooldown = max(1, int(self.player.fire_cooldown * 0.8))

        elif name == 'Piercing':
            self.piercing_level += 1

        elif name == 'Spread Shot':
            self.spread_level += 1

        elif name == 'Explosive':
            self.explosive_level += 1

        elif name == 'Shield':
            pass

        elif name == 'Armor':
            self.armor_level += 1

        elif name == 'Evasion':
            self.evasion_level += 1

        elif name == 'Barrier':
            self.player.max_health += 50
            self.player.health += 50

        elif name == 'Speed Boost':
            self.player.rect.x = self.player.rect.x

        elif name == 'Magnet':
            pass

        elif name == 'Slow Field':
            self.slow_factor = 0.8

        self.milestone_index += 1
        if self.milestone_index % len(self.base_thresholds) == 0:
            self.cycle_count += 1

        self.notification = f"REWARD: {name}"
        self.notification_timer = 90
        self.paused = False

    def render(self, surface: pygame.Surface) -> None:
        surface.fill((0, 0, 0))

        if self.entrance_animation:
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
        else:
            if not self.player_invincible or (self.invincibility_timer // 5) % 2 == 0:
                self.player.render(surface)

            for enemy in self.enemies:
                enemy.render(surface)

            if self.boss:
                self.boss.render(surface)
                self._render_boss_health_bar(surface)

            for eb in self.enemy_bullets:
                eb.render(surface)

            for ripple in self.ripple_effects:
                from airwar.utils.sprites import draw_ripple
                draw_ripple(surface, ripple['x'], ripple['y'], ripple['radius'], ripple['alpha'])

            self._render_hud(surface)
            self._render_buffs(surface)
            self._render_notification(surface)

            if self.reward_selector.visible:
                self.reward_selector.render(surface)

    def _render_boss_health_bar(self, surface: pygame.Surface) -> None:
        if not self.boss:
            return

        bar_width = 400
        bar_height = 28
        x = (surface.get_width() - bar_width) // 2
        y = 15

        pygame.draw.rect(surface, (40, 40, 60), (x - 3, y - 3, bar_width + 6, bar_height + 6), border_radius=8)
        pygame.draw.rect(surface, (55, 55, 75), (x, y, bar_width, bar_height), border_radius=6)

        health_ratio = self.boss.health / self.boss.max_health
        bar_color = (150, 50, 200) if health_ratio > 0.5 else (180, 100, 50) if health_ratio > 0.25 else (200, 50, 50)
        pygame.draw.rect(surface, bar_color, (x, y, int(bar_width * health_ratio), bar_height), border_radius=6)

        font = pygame.font.Font(None, 24)
        boss_text = font.render("BOSS", True, (255, 255, 255))
        text_rect = boss_text.get_rect(center=(x + bar_width // 2, y + bar_height // 2))
        surface.blit(boss_text, text_rect)

        time_remaining = self.boss.get_time_remaining()
        time_text = font.render(f"{time_remaining:.1f}s", True, (255, 220, 100))
        time_rect = time_text.get_rect(right=x + bar_width - 8, centery=y + bar_height // 2)
        surface.blit(time_text, time_rect)

        progress = self.boss.get_survival_progress()
        if progress > 0.7:
            warning_text = font.render("HURRY!", True, (255, 100, 100))
            warning_rect = warning_text.get_rect(left=x + 8, centery=y + bar_height // 2)
            surface.blit(warning_text, warning_rect)

    def _render_hud(self, surface: pygame.Surface) -> None:
        score_text = self.hud_font.render(f"SCORE: {self.score}", True, (255, 255, 255))
        surface.blit(score_text, (15, 15))

        next_ms = self._get_next_threshold()
        progress = min(100, int(self.score / next_ms * 100)) if next_ms > 0 else 0
        progress_text = self.hud_font.render(f"NEXT: {progress}%", True, (200, 200, 100))
        surface.blit(progress_text, (15, 45))

        cycle_text = self.hud_font.render(f"CYCLE: {self.cycle_count}/{self.max_cycles}", True, (150, 150, 200))
        surface.blit(cycle_text, (15, 75))

        diff_text = self.hud_font.render(f"{self.difficulty.upper()}", True, (200, 200, 100))
        surface.blit(diff_text, (surface.get_width() - 110, 15))

        health_text = self.hud_font.render(f"HP: {self.player.health}/{self.player.max_health}", True, (100, 255, 150))
        surface.blit(health_text, (surface.get_width() - 160, 45))

        if self.player.health < self.player.max_health * 0.3:
            health_text = self.hud_font.render(f"HP: {self.player.health}/{self.player.max_health}", True, (255, 80, 80))
            surface.blit(health_text, (surface.get_width() - 160, 45))

        kills_text = self.hud_font.render(f"KILLS: {self.kills}", True, (180, 180, 180))
        surface.blit(kills_text, (surface.get_width() - 120, 75))

    def _render_buffs(self, surface: pygame.Surface) -> None:
        if not self.unlocked_buffs:
            return
        
        x = 15
        y = surface.get_height() - 50
        shown = set()

        pygame.draw.rect(surface, (20, 20, 40), (x - 8, y - 8, 180, 36), border_radius=8)
        
        for buff in reversed(list(self.unlocked_buffs)[:8]):
            if buff in shown:
                continue
            shown.add(buff)

            color = self._get_buff_color(buff)
            text = self.buff_font.render(buff[:4].upper(), True, color)
            rect = text.get_rect(x=x, y=y)
            pygame.draw.rect(surface, color, rect, 1, border_radius=4)
            surface.blit(text, (x + 4, y + 4))
            x += text.get_width() + 14

            if x > 200:
                break

    def _get_buff_color(self, name: str) -> tuple:
        colors = {
            'Extra Life': (100, 255, 150),
            'Regeneration': (150, 255, 100),
            'Lifesteal': (255, 100, 150),
            'Power Shot': (255, 80, 80),
            'Rapid Fire': (255, 200, 100),
            'Piercing': (200, 200, 100),
            'Spread Shot': (255, 150, 100),
            'Explosive': (255, 100, 50),
            'Shield': (200, 100, 255),
            'Armor': (150, 150, 180),
            'Evasion': (100, 200, 255),
            'Barrier': (100, 150, 200),
            'Speed Boost': (100, 255, 200),
            'Magnet': (255, 255, 100),
            'Slow Field': (150, 150, 255),
        }
        return colors.get(name, (255, 255, 255))

    def _render_notification(self, surface: pygame.Surface) -> None:
        if self.notification_timer > 0 and self.notification:
            alpha = min(255, self.notification_timer * 4)
            color = (0, 255, 150) if alpha > 150 else (150, 255, 200)
            text = self.notif_font.render(self.notification, True, color)
            text.set_alpha(alpha)
            x = surface.get_width() // 2 - text.get_width() // 2
            y = 100
            surface.blit(text, (x, y))

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
