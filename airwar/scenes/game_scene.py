import pygame
from typing import Tuple
from .scene import Scene
from airwar.entities import Player, EnemySpawner, Boss, BossData
from airwar.game.systems.health_system import HealthSystem
from airwar.game.systems.reward_system import RewardSystem
from airwar.game.systems.hud_renderer import HUDRenderer
from airwar.game.systems.notification_manager import NotificationManager
from airwar.game.controllers.game_controller import GameController, GameplayState
from airwar.game.controllers.spawn_controller import SpawnController
from airwar.game.controllers.collision_controller import CollisionController
from airwar.game.rendering.game_renderer import GameRenderer
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
from airwar.game.managers import (
    BulletManager,
    BossManager,
    MilestoneManager,
    InputCoordinator,
    UIManager,
    GameLoopManager,
)
from airwar.config import DIFFICULTY_SETTINGS, get_screen_width, get_screen_height
from airwar.input import PygameInputHandler


class GameScene(Scene):
    """游戏场景主控制器，协调游戏主循环和各子系统。"""
    
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
        self._bullet_manager: BulletManager = None
        self._boss_manager: BossManager = None
        self._milestone_manager: MilestoneManager = None
        self._input_coordinator: InputCoordinator = None
        self._ui_manager: UIManager = None
        self._game_loop_manager: GameLoopManager = None

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
        self._bullet_manager = BulletManager(self.player, self.spawn_controller)
        self._boss_manager = BossManager(
            self.spawn_controller,
            self.game_controller,
            self.reward_system,
            self._bullet_manager
        )
        self._milestone_manager = MilestoneManager(
            self.game_controller,
            self.reward_system
        )
        self._milestone_manager.set_reward_selector(self.reward_selector)
        self._input_coordinator = InputCoordinator(
            self.player,
            self.game_controller,
            self.reward_selector,
            self._give_up_detector,
            self._give_up_ui,
        )
        self._ui_manager = UIManager(
            self.game_renderer,
            self.game_controller,
            self.reward_system,
        )
        self._game_loop_manager = GameLoopManager(
            self.game_controller,
            self.game_renderer,
            self.spawn_controller,
            self.reward_system,
            self._bullet_manager,
            self._boss_manager,
            self.collision_controller,
        )

    def _setup_reward_selector(self) -> None:
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

    def exit(self) -> None:
        pass

    def handle_events(self, event: pygame.event.Event) -> None:
        """处理输入事件
        
        Args:
            event: pygame事件对象
        """
        self._input_coordinator.handle_events(event)

    def update(self, *args, **kwargs) -> None:
        """游戏主更新循环
        
        游戏更新顺序:
        1. 入口动画 (如果正在播放)
        2. 母舰系统更新
        3. 停靠状态处理
        4. 游戏逻辑更新 (如果未暂停)
        """
        self.reward_selector.update()

        if self._game_loop_manager.is_entrance_playing():
            self._game_loop_manager.update_entrance(self.player)
            if self._mother_ship_integrator:
                self._mother_ship_integrator.update()
            return

        is_dying = self.game_controller.state.gameplay_state == GameplayState.DYING

        if is_dying:
            self._game_loop_manager.update_game(self.player)
            if self._mother_ship_integrator:
                self._mother_ship_integrator.update()
            return

        if self._mother_ship_integrator:
            self._mother_ship_integrator.update()

            if self._mother_ship_integrator.is_docked():
                self._bullet_manager.update_with_cleanup()
                return

            if self._mother_ship_integrator.is_player_control_disabled():
                self._bullet_manager.update_with_cleanup()
                return

        if self.game_controller.state.paused or self.reward_selector.visible:
            return

        self._input_coordinator.update_give_up()
        self._game_loop_manager.update_game(self.player)
        self._game_loop_manager.check_collisions(
            self.player,
            self.spawn_controller.enemy_bullets,
            lambda damage, player: self.game_controller.on_player_hit(damage, player),
        )
        self._milestone_manager.check_and_trigger(self.player)

    def _on_give_up_complete(self) -> None:
        self.game_controller.on_player_hit(GAME_CONSTANTS.DAMAGE.INSTANT_KILL, self.player)

    def _can_use_give_up(self) -> bool:
        return (
            self.game_controller.is_playing()
            and not self.game_controller.state.paused
            and not self.reward_selector.visible
        )

    def _on_reward_selected(self, reward: dict) -> None:
        """处理奖励选择回调 (兼容层)

        Args:
            reward: 选择的奖励配置字典
        """
        self._milestone_manager._on_reward_selected(reward, self.player)

    def _check_milestones(self) -> None:
        self._milestone_manager.check_and_trigger(self.player)

    def render(self, surface: pygame.Surface) -> None:
        """渲染游戏场景
        
        Args:
            surface: pygame渲染表面
        """
        self._ui_manager.render_game(
            surface,
            self.player,
            self.spawn_controller.enemies,
            self.spawn_controller.boss
        )

        self._ui_manager.render_bullets(
            surface,
            self.player,
            self.spawn_controller.enemy_bullets
        )
        self._ui_manager.render_hud(surface, self.player)
        self._ui_manager.render_notification(surface)
        self._ui_manager.render_buff_stats_panel(surface, self.player)

        if self.reward_selector.visible:
            self.reward_selector.render(surface)

        if self._mother_ship_integrator:
            self._mother_ship_integrator.render(surface)

        self._input_coordinator.render_give_up(surface)

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
        return self.game_controller.is_game_over()

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
