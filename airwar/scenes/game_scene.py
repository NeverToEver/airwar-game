import pygame
from typing import Tuple
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
from airwar.game.give_up import GiveUpDetector, GiveUpUI


class GameScene(Scene):
    """游戏场景主控制器
    
    职责:
    - 管理游戏主循环 (update/render)
    - 协调各游戏子系统 (GameController, SpawnController, CollisionController等)
    - 处理游戏入口/退出/暂停/恢复
    - 管理游戏存档和恢复
    
    依赖子系统:
    - GameController: 游戏逻辑和状态管理
    - SpawnController: 敌人生成和Bullet管理
    - CollisionController: 碰撞检测
    - RewardSystem: 奖励和Buff系统
    - HealthSystem: 生命值管理
    - GameRenderer: 游戏渲染
    - MotherShip系统: 母舰交互
    
    不直接暴露内部状态，通过属性和方法提供受控的访问接口。
    """
    
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
        self._give_up_detector = None
        self._give_up_ui = None

    def enter(self, **kwargs) -> None:
        """初始化游戏场景
        
        Args:
            difficulty: 游戏难度 ('easy', 'medium', 'hard')
            username: 玩家名称
            
        初始化所有游戏子系统:
        - GameController: 游戏状态和逻辑
        - SpawnController: 敌人生成系统
        - CollisionController: 碰撞检测
        - Player: 玩家飞船
        - MotherShip系统: 母舰交互系统
        """
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
        self._init_give_up_system(screen_width, screen_height)

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

    def _init_give_up_system(self, screen_width: int, screen_height: int) -> None:
        self._give_up_detector = GiveUpDetector(self._on_give_up_complete)
        self._give_up_ui = GiveUpUI(screen_width, screen_height)

    def _show_reward_selection(self, options: list, callback) -> None:
        self.reward_selector.visible = True
        self.reward_selector.options = options
        self.reward_selector.selected_index = 0
        self.reward_selector.on_select = callback

    def exit(self) -> None:
        pass

    def handle_events(self, event: pygame.event.Event) -> None:
        """处理输入事件
        
        Args:
            event: pygame事件对象
            
        处理:
        - 空格键发射子弹
        - 奖励选择器输入
        """
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                if not self.game_controller.state.paused and not self.reward_selector.visible:
                    self.player.fire()

        self.reward_selector.handle_input(event)

    def update(self, *args, **kwargs) -> None:
        """游戏主更新循环
        
        游戏更新顺序:
        1. 入口动画 (如果正在播放)
        2. 母舰系统更新
        3. 停靠状态处理
        4. 游戏逻辑更新 (如果未暂停)
        """
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

        if self._can_use_give_up():
            self._give_up_detector.update(1/60)
            if self._give_up_detector.is_active():
                self._give_up_ui.show()
                self._give_up_ui.update_progress(self._give_up_detector.get_progress())
            else:
                self._give_up_ui.hide()
        else:
            self._give_up_ui.hide()

        self._update_game()

    def _update_entrance(self) -> None:
        """更新入口动画
        
        控制玩家飞船从屏幕顶部移动到屏幕底部的动画效果。
        使用线性插值计算飞船位置。
        """
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
        """更新游戏逻辑
        
        游戏主更新流程:
        1. 更新游戏控制器 (生命值再生等)
        2. 更新玩家 (移动、射击)
        3. 更新所有子弹（玩家子弹 + 敌人子弹）
        4. 更新敌人生成
        5. 更新所有实体
        6. 碰撞检测
        7. 检查里程碑奖励
        8. 清理无效实体
        """
        try:
            has_regen = 'Regeneration' in self.reward_system.unlocked_buffs
            self.game_controller.update(self.player, has_regen)

            self.player.update()
            self.player.auto_fire()

            self._update_all_bullets()
            self._update_enemy_spawning()
            self._update_entities()
            self._check_collisions()
            self._check_milestones()

            self.spawn_controller.cleanup()
            self._cleanup_bullets()

            if not self.player.active:
                self.game_controller.state.running = False
        except Exception as e:
            import logging
            logging.error(f"Game update error: {e}", exc_info=True)
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

    def _update_all_bullets(self) -> None:
        for bullet in self.player.get_bullets():
            bullet.update()
        for bullet in self.spawn_controller.enemy_bullets:
            bullet.update()

    def _update_boss(self) -> None:
        boss = self.spawn_controller.boss
        if not boss:
            return
        
        self._update_boss_movement(boss)
        self._handle_boss_escape(boss)
    
    def _update_boss_movement(self, boss) -> None:
        player_pos = (self.player.rect.centerx, self.player.rect.centery)
        boss.update(self.spawn_controller.enemies, player_pos=player_pos)
    
    def _handle_boss_escape(self, boss) -> None:
        if not boss or boss.active:
            return
        
        if boss.is_escaped():
            self.game_controller.show_notification("BOSS ESCAPED! (+0)")

    def _update_entities(self) -> None:
        for enemy in self.spawn_controller.enemies:
            enemy.update(self.spawn_controller.enemies, self.reward_system.slow_factor)

    def _check_collisions(self) -> None:
        try:
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
                on_enemy_killed=lambda score: self.game_controller.on_enemy_killed(score),
                on_boss_killed=lambda score: self.game_controller.on_boss_killed(score),
                on_boss_hit=lambda score: self._on_boss_hit(score),
                on_player_hit=lambda damage, player: self.game_controller.on_player_hit(damage, player),
                on_lifesteal=lambda player, score: self.reward_system.apply_lifesteal(player, score),
                on_clear_bullets=lambda: self._clear_enemy_bullets(),
            )
        except Exception as e:
            import logging
            logging.error(f"Collision detection error: {e}", exc_info=True)
    
    def _on_boss_hit(self, score: int) -> None:
        self.game_controller.state.score += score
        self.game_controller.show_notification(f"+{score} BOSS SCORE!")
        if not self.spawn_controller.boss.active:
            self.game_controller.cycle_count += 1
            self.reward_system.apply_lifesteal(self.player, self.spawn_controller.boss.data.score)
            self._clear_enemy_bullets()

    def _can_use_give_up(self) -> bool:
        from airwar.game.controllers.game_controller import GameplayState
        return (
            self.game_controller.state.gameplay_state == GameplayState.PLAYING
            and not self.game_controller.state.paused
            and not self.reward_selector.visible
        )

    def _on_give_up_complete(self) -> None:
        self.game_controller.on_player_hit(9999, self.player)

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
        """处理奖励选择回调
        
        Args:
            reward: 选择的奖励配置字典
        """
        self.game_controller.on_reward_selected(reward, self.player)
        self.reward_selector.visible = False

    def render(self, surface: pygame.Surface) -> None:
        """渲染游戏场景
        
        Args:
            surface: pygame渲染表面
            
        渲染顺序:
        1. 游戏背景和实体 (玩家、敌人、Boss)
        2. 玩家子弹
        3. 敌人子弹
        4. HUD (分数、生命值等)
        5. 奖励选择器 (如果可见)
        6. 母舰 (如果激活)
        """
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

        if self._give_up_detector and self._give_up_detector.is_active():
            self._give_up_ui.render(surface)

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
    def score(self) -> int:
        """获取当前分数
        
        Returns:
            int: 当前游戏分数
        """
        return self.game_controller.state.score if self.game_controller else 0

    @score.setter
    def score(self, value: int) -> None:
        """设置当前分数
        
        Args:
            value: 新的分数值
        """
        if self.game_controller:
            self.game_controller.state.score = value

    @property
    def cycle_count(self) -> int:
        """获取当前周期计数
        
        Returns:
            int: 已完成的Boss周期数
        """
        return self.game_controller.cycle_count if self.game_controller else 0

    @cycle_count.setter
    def cycle_count(self, value: int) -> None:
        """设置周期计数
        
        Args:
            value: 新的周期计数
        """
        if self.game_controller:
            self.game_controller.cycle_count = value

    @property
    def boss(self):
        """获取当前Boss实例
        
        Returns:
            Boss对象，如果不存在则返回None
        """
        return self.spawn_controller.boss if self.spawn_controller else None

    def is_game_over(self) -> bool:
        """判断游戏是否结束
        
        Returns:
            bool: True表示游戏结束
        """
        if not self.player:
            return True
        if not self.game_controller:
            return True
        from airwar.game.controllers.game_controller import GameplayState
        return self.game_controller.state.gameplay_state == GameplayState.GAME_OVER

    def is_paused(self) -> bool:
        """判断游戏是否暂停
        
        Returns:
            bool: True表示游戏已暂停
        """
        return self.game_controller.state.paused if self.game_controller else False

    def pause(self) -> None:
        """暂停游戏
        
        如果奖励选择器可见则不会暂停。
        """
        if self.game_controller and not self.reward_selector.visible:
            self.game_controller.state.paused = True

    def resume(self) -> None:
        """继续游戏"""
        if self.game_controller:
            self.game_controller.state.paused = False

    @property
    def paused(self) -> bool:
        """获取游戏暂停状态
        
        Returns:
            bool: True表示游戏暂停
        """
        return self.game_controller.state.paused if self.game_controller else False

    @paused.setter
    def paused(self, value: bool) -> None:
        """设置游戏暂停状态
        
        Args:
            value: True暂停游戏，False继续游戏
        """
        if self.game_controller:
            self.game_controller.state.paused = value

    @property
    def unlocked_buffs(self) -> list:
        """获取已解锁的Buff列表
        
        Returns:
            list: 已解锁的Buff名称列表
        """
        return self.reward_system.unlocked_buffs if self.reward_system else []

    @unlocked_buffs.setter
    def unlocked_buffs(self, value: list) -> None:
        """设置已解锁的Buff列表
        
        Args:
            value: Buff名称列表
        """
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
    def difficulty(self) -> str:
        """获取游戏难度
        
        Returns:
            str: 游戏难度 ('easy', 'medium', 'hard')
        """
        return self.game_controller.state.difficulty if self.game_controller else 'medium'

    @difficulty.setter
    def difficulty(self, value: str) -> None:
        """设置游戏难度
        
        Args:
            value: 游戏难度 ('easy', 'medium', 'hard')
        """
        if self.game_controller:
            self.game_controller.state.difficulty = value

    def restore_from_save(self, save_data) -> None:
        """从存档数据恢复游戏状态
        
        Args:
            save_data: 存档数据对象，包含:
                - score: 当前分数
                - kill_count: 击杀数
                - cycle_count: 当前周期数
                - player_health: 玩家生命值
                - player_max_health: 玩家最大生命值
                - unlocked_buffs: 已解锁的buff列表
                - buff_levels: buff等级字典
                - difficulty: 游戏难度
                - username: 玩家名称
                - is_in_mothership: 是否在母舰状态
        """
        if not save_data or not self.game_controller or not self.player:
            return

        self.game_controller.state.score = save_data.score
        self.game_controller.state.kill_count = save_data.kill_count
        self.game_controller.milestone_index = save_data.cycle_count * 5
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
        """恢复Buff等级
        
        Args:
            buff_levels: Buff等级字典
        """
        if not buff_levels:
            return
        self.reward_system.piercing_level = buff_levels.get('piercing_level', 0)
        self.reward_system.spread_level = buff_levels.get('spread_level', 0)
        self.reward_system.explosive_level = buff_levels.get('explosive_level', 0)
        self.reward_system.armor_level = buff_levels.get('armor_level', 0)
        self.reward_system.evasion_level = buff_levels.get('evasion_level', 0)
        self.reward_system.rapid_fire_level = buff_levels.get('rapid_fire_level', 0)

    def _restore_to_mothership_state(self) -> None:
        """恢复母舰状态"""
        if self._mother_ship_integrator:
            self._mother_ship_integrator.reset_to_idle_with_mothership_visible()
        self.game_controller.state.entrance_animation = False
        self.game_controller.state.paused = False
        self.player.rect.y = PlayerConstants.MOTHERSHIP_Y_POSITION
        self.player.rect.x = self.game_controller.state.score // 2 % PlayerConstants.DEFAULT_SCREEN_WIDTH
