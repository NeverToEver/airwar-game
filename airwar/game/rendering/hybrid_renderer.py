"""渲染器 - pygame CPU 后端"""
import pygame

from airwar.game.rendering.game_renderer import GameRenderer, GameEntities
from airwar.game.rendering.hud_renderer import HUDRenderer
from airwar.game.managers.game_controller import GameState
from airwar.entities.player import Player


class HybridRenderer:
    """游戏渲染器（pygame 后端）"""

    def __init__(self, screen_width: int = 1400, screen_height: int = 800):
        self._screen_size = (screen_width, screen_height)

        self._pygame_renderer = GameRenderer()
        self._pygame_renderer.init_background(screen_width, screen_height)
        self._pygame_hud = HUDRenderer()

    def render_game(
        self,
        surface: pygame.Surface,
        state: GameState,
        player: Player,
        enemies: list,
        boss
    ) -> None:
        """渲染游戏主画面"""
        entities = GameEntities(player, enemies, boss)
        self._pygame_renderer.render(surface, state, entities)

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
        """渲染 HUD"""
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

    def release(self) -> None:
        """释放资源"""
        pass
