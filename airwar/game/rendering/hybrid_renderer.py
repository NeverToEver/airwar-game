"""混合渲染器 - 支持 pygame 和 GPU 双后端，逐步迁移到 GPU"""
import pygame
from typing import Optional, Tuple

from airwar.game.gpu import GPUComposer
from airwar.game.rendering.game_renderer import GameRenderer
from airwar.game.rendering.hud_renderer import HUDRenderer
from airwar.game.managers.game_controller import GameState
from airwar.entities.player import Player
from airwar.entities.enemy import Enemy
from airwar.entities.bullet import Bullet
from airwar.utils.sprites import get_player_sprite, get_enemy_sprite, get_boss_sprite


class HybridRenderer:
    """混合渲染器，支持 pygame (CPU) 和 GPU (ModernGL) 双后端

    迁移策略：
    1. 默认使用 pygame 后端（稳定）
    2. GPU 后端可选启用
    3. 逐步将组件迁移到 GPU
    4. GPU 失败时自动 fallback 到 pygame
    """

    def __init__(self, screen_width: int = 1400, screen_height: int = 800, use_gpu: bool = False):
        self._screen_size = (screen_width, screen_height)
        self._use_gpu = use_gpu

        # pygame 后端
        self._pygame_renderer = GameRenderer()
        self._pygame_renderer.init_background(screen_width, screen_height)
        self._pygame_hud = HUDRenderer()

        # GPU 后端
        self._gpu_composer: Optional[GPUComposer] = None
        self._gpu_surfaces_uploaded = False

        # 纹理名称映射
        self._texture_names = {
            'player': 'player_ship',
            'enemy': 'enemy_ship',
            'boss': 'boss_ship',
        }

        if use_gpu:
            self._init_gpu_backend()

    def _init_gpu_backend(self) -> bool:
        """初始化 GPU 后端"""
        try:
            self._gpu_composer = GPUComposer(*self._screen_size)
            self._upload_surfaces()
            return True
        except Exception as e:
            print(f"GPU backend init failed: {e}")
            self._gpu_composer = None
            return False

    def _upload_surfaces(self) -> None:
        """上传所有精灵 Surface 到 GPU"""
        if not self._gpu_composer or self._gpu_surfaces_uploaded:
            return

        # 预渲染精灵 Surface
        player_surf = get_player_sprite(50, 60)
        enemy_surf = get_enemy_sprite(50, 50, 1.0)
        boss_surf = get_boss_sprite(120, 100, 1.0)

        # 上传到 GPU
        self._gpu_composer.upload_surface(self._texture_names['player'], player_surf)
        self._gpu_composer.upload_surface(self._texture_names['enemy'], enemy_surf)
        self._gpu_composer.upload_surface(self._texture_names['boss'], boss_surf)

        self._gpu_composer.upload_all_surfaces()
        self._gpu_surfaces_uploaded = True

    def enable_gpu(self) -> bool:
        """启用 GPU 后端"""
        if self._use_gpu:
            return True
        self._use_gpu = True
        return self._init_gpu_backend()

    def test_gpu(self) -> bool:
        """测试 GPU 是否可用（不改变当前状态）"""
        try:
            test_composer = GPUComposer(*self._screen_size)
            test_composer.release()
            return True
        except Exception as e:
            print(f"GPU test failed: {e}")
            return False

    def disable_gpu(self) -> None:
        """禁用 GPU 后端，切换到 pygame"""
        if self._gpu_composer:
            self._gpu_composer.release()
            self._gpu_composer = None
        self._use_gpu = False
        self._gpu_surfaces_uploaded = False

    @property
    def is_gpu_enabled(self) -> bool:
        return self._use_gpu and self._gpu_composer is not None

    def render_game(
        self,
        surface: pygame.Surface,
        state: GameState,
        player: Player,
        enemies: list,
        boss
    ) -> None:
        """渲染游戏主画面"""
        if self.is_gpu_enabled:
            self._render_game_gpu(surface, state, player, enemies, boss)
        else:
            from airwar.game.rendering.game_renderer import GameEntities
            entities = GameEntities(player, enemies, boss)
            self._pygame_renderer.render(surface, state, entities)

    def _render_game_gpu(
        self,
        surface: pygame.Surface,
        state,
        player: Player,
        enemies: list,
        boss
    ) -> None:
        """使用 GPU 渲染游戏画面"""
        if not self._gpu_composer:
            return

        self._gpu_composer.clear_sprites()

        # 更新背景
        self._gpu_composer.update_background(1.0)

        # 添加玩家精灵
        if player:
            health_ratio = player.health / player.max_health if player.max_health > 0 else 1.0
            self._gpu_composer.add_sprite(
                self._texture_names['player'],
                player.rect.centerx,
                player.rect.centery,
                player.rect.width,
                player.rect.height,
                layer='entities'
            )

        # 添加敌机精灵
        for enemy in enemies:
            if hasattr(enemy, 'rect') and enemy.active:
                health_ratio = 1.0
                if hasattr(enemy, 'health') and hasattr(enemy, 'max_health'):
                    if enemy.max_health > 0:
                        health_ratio = enemy.health / enemy.max_health
                self._gpu_composer.add_sprite(
                    self._texture_names['enemy'],
                    enemy.rect.centerx,
                    enemy.rect.centery,
                    enemy.rect.width,
                    enemy.rect.height,
                    layer='entities'
                )

        # 添加 Boss 精灵
        if boss and hasattr(boss, 'rect'):
            self._gpu_composer.add_sprite(
                self._texture_names['boss'],
                boss.rect.centerx,
                boss.rect.centery,
                boss.rect.width,
                boss.rect.height,
                layer='entities'
            )

        # 执行 GPU 渲染
        self._gpu_composer.render()

        # 将 GPU 渲染结果 blit 到 pygame surface
        gpu_surface = self._gpu_composer.get_surface()
        surface.blit(gpu_surface, (0, 0))

    def render_hud(
        self,
        surface: pygame.Surface,
        score: int,
        difficulty: str,
        player_health: int,
        player_max_health: int,
        kills: int,
        next_progress: int,
        boss_kills: int = 0,
        unlocked_buffs=None,
        get_buff_color=None,
        current_coefficient: float = None,
        initial_coefficient: float = None
    ) -> None:
        """渲染 HUD（保留 pygame 后端）"""
        self._pygame_hud.render_hud(
            surface, score, difficulty,
            player_health, player_max_health, kills,
            next_progress,
            boss_kills=boss_kills
        )

    def render_notification(self, surface: pygame.Surface, notification: str, timer: int) -> None:
        """渲染通知"""
        self._pygame_hud.render_notification(surface, notification, timer)

    def render_buff_stats_panel(self, surface, reward_system, player) -> None:
        """渲染 buff 状态面板"""
        self._pygame_hud.render_buff_stats_panel(surface, reward_system, player)

    def render_attack_mode_panel(self, surface, reward_system) -> None:
        """渲染攻击模式面板"""
        self._pygame_hud.render_attack_mode_panel(surface, reward_system)

    def resize(self, screen_width: int, screen_height: int) -> None:
        """调整渲染器尺寸"""
        self._screen_size = (screen_width, screen_height)
        self._pygame_renderer.init_background(screen_width, screen_height)
        if self._gpu_composer:
            self._gpu_composer.resize(screen_width, screen_height)

    def release(self) -> None:
        """释放资源"""
        if self._gpu_composer:
            self._gpu_composer.release()
            self._gpu_composer = None
