"""Base-side talent loadout console.

Phase 4 Wave beta + Phase 5-δ thin orchestrator. The class holds four
widgets (hangar panel, talent switcher, resupply panel, mission list)
and forwards per-module render calls to the right widget. The class
also keeps a small amount of state (active module, missions, button
rects, frame counter) and mouse dispatch logic.

Public API (unchanged from pre-split):
    - ``BaseTalentConsole(width, height)``
    - ``render(surface, manager, reward_system, player=None,
      game_controller=None, mothership_status=None,
      requisition_points=0, missions=None)``
    - ``handle_mouse_motion(pos)``, ``handle_mouse_click(pos)``
    - ``get_missions()``, ``update()``
    - ``BaseTalentConsoleAction`` dataclass (continued module/level
      actions: CONTINUE, SELECT_ROUTE, SELECT_MODULE, RESUPPLY,
      REPAIR, RECHARGE)
"""

import math
from dataclasses import dataclass

import pygame

from airwar.utils.fonts import get_cjk_font

from .chamfered_panel import draw_chamfered_panel
from .hangar_panel import HangarPanel
from .scene_rendering_utils import fit_text_to_width
from .talent import MissionList, ResupplyPanel, TalentSwitcher

BASE_MODULES = ("hangar", "loadout", "supply", "mission")
BUFF_LABELS = {
    "Spread Shot": "散射弹幕",
    "Laser": "激光模式",
    "Phase Dash": "相位突进",
    "Mothership Recall": "母舰冷却",
}
MODULE_LABELS = {
    "hangar": "战机库",
    "loadout": "武器挂载",
    "supply": "维修补给",
    "mission": "任务规划",
}
MODULE_HINTS = {
    "hangar": "检查机体状态、母舰链路与已解锁设施。",
    "loadout": "切换互斥路线会立即重算当前有效天赋。",
    "supply": "补满机体生命与加速燃料，并保存当前整备状态。",
    "mission": "确认下一奖励阈值、敌情压力和返航后的出击目标。",
}


@dataclass(frozen=True)
class BaseTalentConsoleAction:
    """Semantic action requested by the base console."""

    CONTINUE = "continue"
    SELECT_ROUTE = "select_route"
    SELECT_MODULE = "select_module"
    RESUPPLY = "resupply"
    REPAIR = "repair"
    RECHARGE = "recharge"

    kind: str
    route: str | None = None
    module: str | None = None

    @classmethod
    def continue_sortie(cls) -> "BaseTalentConsoleAction":
        return cls(cls.CONTINUE)

    @classmethod
    def select_route(cls, route: str) -> "BaseTalentConsoleAction":
        return cls(cls.SELECT_ROUTE, route)

    @classmethod
    def select_module(cls, module: str) -> "BaseTalentConsoleAction":
        return cls(cls.SELECT_MODULE, module=module)

    @classmethod
    def resupply(cls) -> "BaseTalentConsoleAction":
        return cls(cls.RESUPPLY)

    @classmethod
    def repair(cls) -> "BaseTalentConsoleAction":
        return cls(cls.REPAIR)

    @classmethod
    def recharge(cls) -> "BaseTalentConsoleAction":
        return cls(cls.RECHARGE)


class BaseTalentConsole:
    """Renders and handles the base command surface."""

    def __init__(self, screen_width: int, screen_height: int):
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._font_title = get_cjk_font(34)
        self._font_section = get_cjk_font(26)
        self._font = get_cjk_font(22)
        self._font_small = get_cjk_font(17)
        self._font_tiny = get_cjk_font(14)
        self._button_rects: dict[str, pygame.Rect] = {}
        self._hovered_button: str | None = None
        self._active_module = "hangar"
        self._frame = 0
        self._requisition_points: int = 0
        self._missions: list[dict] = [
            {
                "name": "歼灭先锋",
                "desc": "击杀5个敌人",
                "target": "kills",
                "goal": 5,
                "progress": 0,
                "done": False,
                "claimed": False,
            },
            {
                "name": "战场生存",
                "desc": "存活180秒",
                "target": "survival_time",
                "goal": 180,
                "progress": 0,
                "done": False,
                "claimed": False,
            },
            {
                "name": "主宰之战",
                "desc": "击杀Boss",
                "target": "boss_kills",
                "goal": 1,
                "progress": 0,
                "done": False,
                "claimed": False,
            },
        ]
        # Build per-widget font dict (used by the split components).
        fonts = {
            "font_title": self._font_title,
            "font_section": self._font_section,
            "font": self._font,
            "font_small": self._font_small,
            "font_tiny": self._font_tiny,
        }
        self._hangar_panel = HangarPanel(self._button_rects, lambda: self._hovered_button, fonts)
        self._talent_switcher = TalentSwitcher(self._button_rects, lambda: self._hovered_button, fonts)
        self._resupply_panel = ResupplyPanel(self._button_rects, lambda: self._hovered_button, fonts)
        self._mission_list = MissionList(lambda: self._missions, fonts)

    def get_missions(self) -> list[dict]:
        """Return the mission list (read-only view for external consumers)."""
        return self._missions

    def update(self) -> None:
        self._frame += 1

    def handle_mouse_motion(self, pos: tuple[int, int]) -> None:
        self._hovered_button = self._button_at(pos)

    def handle_mouse_click(self, pos: tuple[int, int]) -> BaseTalentConsoleAction | None:
        button = self._button_at(pos)
        if not button:
            return None
        if button == "continue":
            return BaseTalentConsoleAction.continue_sortie()
        if button == "supply:resupply":
            return BaseTalentConsoleAction.resupply()
        if button == "hangar:repair":
            return BaseTalentConsoleAction.repair()
        if button == "hangar:recharge":
            return BaseTalentConsoleAction.recharge()
        module = self._module_from_button(button)
        if module:
            self._active_module = module
            return BaseTalentConsoleAction.select_module(module)
        route = self._route_from_button(button)
        if route:
            return BaseTalentConsoleAction.select_route(route)
        return None

    def render(
        self,
        surface: pygame.Surface,
        manager,
        reward_system,
        player=None,
        game_controller=None,
        mothership_status: dict | None = None,
        requisition_points: int = 0,
        missions: list[dict] | None = None,
    ) -> None:
        self._button_rects.clear()
        self._requisition_points = requisition_points
        if missions is not None:
            self._missions = missions
        sw, sh = surface.get_size()
        self._render_backdrop(surface)

        panel_w = min(1180, max(720, sw - 96))
        panel_h = min(690, max(520, sh - 80))
        panel_w = min(panel_w, sw - 40)
        panel_h = min(panel_h, sh - 40)
        x = (sw - panel_w) // 2
        y = (sh - panel_h) // 2
        draw_chamfered_panel(
            surface,
            x,
            y,
            panel_w,
            panel_h,
            (7, 14, 24),
            (72, 214, 202, 190),
            (64, 210, 194, 115),
            10,
        )

        self._draw_header(surface, x, y, panel_w, manager)
        nav_y = y + 104
        content_y = y + 168
        footer_h = 92
        footer_y = y + panel_h - footer_h - 22
        content_h = max(180, footer_y - content_y - 16)
        content_rect = pygame.Rect(x + 34, content_y, panel_w - 68, content_h)

        self._draw_module_nav(surface, x + 34, nav_y, panel_w - 68)
        self._draw_active_module(
            surface,
            content_rect,
            manager,
            reward_system,
            player,
            game_controller,
            mothership_status,
            self._requisition_points,
        )
        self._draw_summary(surface, x + 34, footer_y, panel_w - 68, reward_system)

    def _render_backdrop(self, surface: pygame.Surface) -> None:
        sw, sh = surface.get_size()
        surface.fill((8, 11, 14))
        deck = pygame.Surface((sw, sh), pygame.SRCALPHA)

        horizon_y = int(sh * 0.34)
        pygame.draw.rect(deck, (10, 15, 19), pygame.Rect(0, 0, sw, horizon_y))
        pygame.draw.rect(deck, (21, 25, 28), pygame.Rect(0, horizon_y, sw, sh - horizon_y))

        back_wall = pygame.Rect(int(sw * 0.08), int(sh * 0.08), int(sw * 0.84), int(sh * 0.25))
        pygame.draw.rect(deck, (15, 22, 28, 230), back_wall)
        pygame.draw.line(deck, (72, 88, 98, 160), back_wall.bottomleft, back_wall.bottomright, 2)
        for index in range(9):
            x = back_wall.x + index * back_wall.w // 8
            pygame.draw.line(deck, (42, 54, 62, 130), (x, back_wall.y), (x, back_wall.bottom), 1)

        ramp_top = (sw // 2, horizon_y + 18)
        ramp_left = (int(sw * 0.16), sh)
        ramp_right = (int(sw * 0.84), sh)
        pygame.draw.polygon(deck, (31, 35, 37, 245), [ramp_top, ramp_right, ramp_left])

        center_x = sw // 2
        pad_center_y = int(sh * 0.68)
        pad_outer = pygame.Rect(0, 0, int(sw * 0.46), int(sh * 0.22))
        pad_outer.center = (center_x, pad_center_y)
        pad_inner = pad_outer.inflate(-int(sw * 0.09), -int(sh * 0.055))
        pygame.draw.ellipse(deck, (24, 30, 32, 255), pad_outer)
        pygame.draw.ellipse(deck, (92, 104, 104, 190), pad_outer, 3)
        pygame.draw.ellipse(deck, (12, 18, 21, 255), pad_inner)
        pygame.draw.line(deck, (118, 132, 132, 150), (pad_outer.left, pad_center_y), (pad_outer.right, pad_center_y), 2)
        pygame.draw.line(deck, (118, 132, 132, 120), (center_x, pad_outer.top), (center_x, pad_outer.bottom), 2)

        for offset in (-0.34, -0.2, 0.2, 0.34):
            start_x = int(center_x + sw * offset * 0.24)
            end_x = int(center_x + sw * offset)
            pygame.draw.line(deck, (58, 72, 76, 150), (start_x, horizon_y + 24), (end_x, sh), 2)

        for index in range(8):
            y = horizon_y + 42 + index * max(18, (sh - horizon_y) // 9)
            width = max(1, int(1 + index * 0.45))
            pygame.draw.line(deck, (44, 54, 57, 130), (0, y), (sw, y), width)

        stripe_y = int(sh * 0.83)
        stripe_h = max(26, int(sh * 0.035))
        for index, x in enumerate(range(0, sw, stripe_h)):
            color = (178, 142, 52, 205) if index % 2 == 0 else (18, 20, 22, 230)
            points = [
                (x, stripe_y),
                (x + stripe_h, stripe_y),
                (x + stripe_h - stripe_h // 2, stripe_y + stripe_h),
                (x - stripe_h // 2, stripe_y + stripe_h),
            ]
            pygame.draw.polygon(deck, color, points)

        pulse = 0.5 + 0.5 * math.sin(self._frame * 0.06)
        for side in (-1, 1):
            rail_x = int(center_x + side * sw * 0.28)
            pygame.draw.line(deck, (70, 84, 88, 150), (rail_x, horizon_y + 18), (rail_x + side * int(sw * 0.17), sh), 3)
            for index in range(7):
                t = index / 6
                x = int(rail_x + side * sw * 0.17 * t)
                y = int(horizon_y + 30 + (sh - horizon_y - 80) * t)
                alpha = 95 + int(80 * pulse)
                pygame.draw.circle(deck, (94, 226, 210, alpha), (x, y), 4 + index // 3)

        shadow = pygame.Surface((sw, sh), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 84))
        pygame.draw.ellipse(shadow, (0, 0, 0, 0), pad_outer.inflate(120, 70))
        deck.blit(shadow, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
        surface.blit(deck, (0, 0))

    def _draw_header(self, surface: pygame.Surface, x: int, y: int, panel_w: int, manager) -> None:
        title = self._font_title.render("基地指挥中心", True, (226, 246, 244))
        subtitle = self._font_small.render(
            "返航后完成机库检查、武器挂载、维修补给和下一轮任务规划。",
            True,
            (145, 170, 188),
        )
        points = self._font.render(f"可分配点数 {manager.total_points()}", True, (104, 238, 220))
        surface.blit(title, (x + 34, y + 28))
        surface.blit(subtitle, (x + 36, y + 78))
        surface.blit(points, points.get_rect(topright=(x + panel_w - 34, y + 34)))

    def _draw_module_nav(self, surface: pygame.Surface, x: int, y: int, width: int) -> None:
        gap = 12
        tab_w = (width - gap * (len(BASE_MODULES) - 1)) // len(BASE_MODULES)
        for index, module in enumerate(BASE_MODULES):
            rect = pygame.Rect(x + index * (tab_w + gap), y, tab_w, 48)
            self._button_rects[f"module:{module}"] = rect
            active = module == self._active_module
            hovered = self._hovered_button == f"module:{module}"
            bg = (18, 48, 58) if active else (12, 24, 34)
            if hovered and not active:
                bg = (15, 34, 46)
            border = (120, 252, 232, 220) if active else (62, 104, 124, 165)
            draw_chamfered_panel(surface, rect.x, rect.y, rect.w, rect.h, bg, border, None, 7)
            color = (232, 252, 248) if active else (158, 182, 196)
            label = fit_text_to_width(self._font, MODULE_LABELS[module], color, rect.w - 24)
            surface.blit(label, label.get_rect(center=rect.center))

    def _draw_active_module(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        manager,
        reward_system,
        player,
        game_controller,
        mothership_status: dict | None,
        requisition_points: int = 0,
    ) -> None:
        draw_chamfered_panel(surface, rect.x, rect.y, rect.w, rect.h, (8, 16, 26), (48, 84, 104, 150), None, 8)
        inner = rect.inflate(-28, -24)
        status = self._collect_base_status(player, game_controller, reward_system, mothership_status)
        if self._active_module == "loadout":
            self._talent_switcher.render_loadout_module(surface, inner, manager)
        elif self._active_module == "supply":
            self._resupply_panel.render_supply_module(surface, inner, status, requisition_points)
        elif self._active_module == "mission":
            self._mission_list.render_mission_module(surface, inner)
        else:
            self._hangar_panel.render_hangar_module(surface, inner, status, requisition_points, self._frame)

    def _draw_summary(self, surface: pygame.Surface, x: int, y: int, width: int, reward_system) -> None:
        rect = pygame.Rect(x, y, width, 92)
        draw_chamfered_panel(surface, rect.x, rect.y, rect.w, rect.h, (9, 18, 28), (64, 98, 118, 170), None, 7)
        button_rect = pygame.Rect(rect.right - 190, rect.y + 20, 166, 52)
        self._button_rects["continue"] = button_rect
        locked = sorted(getattr(reward_system, "locked_buffs", set()))
        if locked:
            locked_text = "已关闭: " + " / ".join(BUFF_LABELS.get(name, name) for name in locked)
        else:
            locked_text = "当前没有互斥关闭项"
        hint = "点击右侧模块切换路线；当前配置立即生效。"
        text_width = max(0, button_rect.x - rect.x - 38)
        surface.blit(
            fit_text_to_width(self._font_small, locked_text, (210, 178, 138), text_width),
            (rect.x + 20, rect.y + 20),
        )
        hint_text = MODULE_HINTS.get(self._active_module, hint)
        hint_surf = fit_text_to_width(self._font_small, hint_text, (132, 154, 172), text_width)
        surface.blit(hint_surf, (rect.x + 20, rect.y + 52))
        self._draw_continue_button(surface, button_rect, self._hovered_button == "continue")

    def _draw_continue_button(self, surface: pygame.Surface, rect: pygame.Rect, hovered: bool) -> None:
        bg = (24, 62, 70) if hovered else (18, 44, 54)
        border = (126, 255, 233, 235) if hovered else (82, 224, 204, 180)
        draw_chamfered_panel(surface, rect.x, rect.y, rect.w, rect.h, bg, border, None, 8)
        label = fit_text_to_width(self._font, "继续出击", (232, 252, 248), rect.w - 28)
        surface.blit(label, label.get_rect(center=rect.center))

    def _button_at(self, pos: tuple[int, int]) -> str | None:
        for name, rect in self._button_rects.items():
            if rect.collidepoint(pos):
                return name
        return None

    def _module_from_button(self, button: str) -> str | None:
        if button.startswith("module:"):
            module = button.split(":", 1)[1]
            if module in BASE_MODULES:
                return module
        return None

    def _route_from_button(self, button: str) -> str | None:
        if button.startswith("route:"):
            return button.split(":", 1)[1]
        return None

    def _collect_base_status(self, player, game_controller, reward_system, mothership_status: dict | None) -> dict:
        health = int(getattr(player, "health", 0) or 0)
        max_health = max(1, int(getattr(player, "max_health", health or 1) or 1))
        boost_status = player.get_boost_status() if player and hasattr(player, "get_boost_status") else {}
        boost = float(boost_status.get("current", getattr(player, "boost_current", 0.0) or 0.0))
        boost_max = max(1.0, float(boost_status.get("max", getattr(player, "boost_max", 1.0) or 1.0)))
        damage = int(getattr(player, "bullet_damage", 0) or 0)
        base_damage = max(1, int(getattr(reward_system, "base_bullet_damage", damage or 1) or 1))
        fire_interval = int(getattr(player, "fire_interval", getattr(player, "fire_cooldown", 0)) or 0)
        base_fire_interval = max(1, int(getattr(reward_system, "base_fire_cooldown", fire_interval or 1) or 1))
        state = getattr(game_controller, "state", None)
        milestone_progress = 0
        next_threshold = 0
        if game_controller:
            milestone_progress = int(game_controller.get_next_progress())
            next_threshold = int(game_controller.get_next_threshold())
        mothership_status = mothership_status or {}
        ammo_max = max(1.0, float(mothership_status.get("ammo_max", 10.0) or 10.0))
        ammo_count = max(0.0, float(mothership_status.get("ammo_count", ammo_max) or 0.0))
        cooldown_reduction = float(mothership_status.get("cooldown_reduction", 0.0) or 0.0)
        active_buff_count = len(getattr(reward_system, "unlocked_buffs", []) or [])

        return {
            "health": health,
            "max_health": max_health,
            "health_ratio": health / max_health,
            "boost": boost,
            "boost_max": boost_max,
            "boost_ratio": boost / boost_max,
            "damage": damage,
            "damage_ratio": min(1.0, damage / max(base_damage * 2.5, 1.0)),
            "fire_interval": fire_interval,
            "fire_ratio": min(1.0, base_fire_interval / max(fire_interval, 1)),
            "score": int(getattr(state, "score", 0) or 0),
            "kills": int(getattr(state, "kill_count", 0) or 0),
            "boss_kills": int(getattr(state, "boss_kill_count", 0) or 0),
            "difficulty": getattr(state, "difficulty", "medium"),
            "milestone_progress": milestone_progress,
            "milestone_ratio": milestone_progress / 100,
            "next_threshold": next_threshold,
            "ammo_count": min(ammo_count, ammo_max),
            "ammo_max": ammo_max,
            "ammo_ratio": min(ammo_count / ammo_max, 1.0),
            "cooldown_reduction_pct": int(cooldown_reduction * 100),
            "active_buff_count": active_buff_count,
        }
