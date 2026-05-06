"""Base-side talent loadout console."""

from dataclasses import dataclass
import math

import pygame

from airwar.ui.chamfered_panel import draw_chamfered_panel
from airwar.ui.scene_rendering_utils import fit_text_to_width
from airwar.utils.fonts import get_cjk_font


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
            {"name": "歼灭先锋", "desc": "击杀5个敌人", "target": "kills", "goal": 5, "progress": 0, "done": False, "claimed": False},
            {"name": "战场生存", "desc": "存活180秒", "target": "survival_time", "goal": 180, "progress": 0, "done": False, "claimed": False},
            {"name": "主宰之战", "desc": "击杀Boss", "target": "boss_kills", "goal": 1, "progress": 0, "done": False, "claimed": False},
        ]

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
            self._draw_loadout_module(surface, inner, manager)
        elif self._active_module == "supply":
            self._draw_supply_module(surface, inner, status, requisition_points)
        elif self._active_module == "mission":
            self._draw_mission_module(surface, inner, status, requisition_points)
        else:
            self._draw_hangar_module(surface, inner, status, requisition_points)

    def _draw_loadout_module(self, surface: pygame.Surface, rect: pygame.Rect, manager) -> None:
        compact = rect.h < 250
        intro_h = 46 if compact else 54
        intro = pygame.Rect(rect.x, rect.y, rect.w, intro_h)
        draw_chamfered_panel(surface, intro.x, intro.y, intro.w, intro.h, (10, 25, 36), (58, 126, 142, 150), None, 6)
        title = self._font.render("武器挂载台", True, (224, 244, 244))
        body = "选择同一路线内的主模式；未选中的互斥能力会被基地临时关闭。"
        title_y = intro.y + (9 if compact else 13)
        surface.blit(title, (intro.x + 18, title_y))
        surface.blit(
            fit_text_to_width(self._font_small, body, (142, 170, 186), intro.w - 260),
            (intro.x + 190, intro.y + (13 if compact else 17)),
        )
        route_gap = 10 if compact else 14
        route_top_gap = 14 if compact else 18
        route_h = max(58, min(124, (rect.h - intro_h - route_top_gap - route_gap) // 2))
        self._draw_routes(
            surface,
            rect.x,
            intro.bottom + route_top_gap,
            rect.w,
            manager,
            route_h=route_h,
            route_gap=route_gap,
        )

    def _draw_routes(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        width: int,
        manager,
        route_h: int = 124,
        route_gap: int = 14,
    ) -> None:
        for index, view in enumerate(manager.route_views()):
            rect = pygame.Rect(x, y + index * (route_h + route_gap), width, route_h)
            border = (84, 230, 210, 180) if view.is_unlocked else (80, 96, 112, 145)
            draw_chamfered_panel(surface, rect.x, rect.y, rect.w, rect.h, (11, 21, 34), border, None, 8)

            label = self._font.render(view.label, True, (218, 238, 238))
            budget = self._font_small.render(f"路线点数 {view.budget}", True, (146, 174, 190))
            surface.blit(label, (rect.x + 22, rect.y + 18))
            surface.blit(budget, (rect.x + 24, rect.y + 52))

            button_w = min(250, max(190, rect.w // 4))
            button_y_pad = 16 if route_h < 86 else 24
            button_rect = pygame.Rect(rect.right - button_w - 26, rect.y + button_y_pad, button_w, max(44, route_h - button_y_pad * 2))
            self._button_rects[f"route:{view.route}"] = button_rect
            selected = view.selected or "未解锁"
            selected_label = BUFF_LABELS.get(selected, selected)
            is_hover = self._hovered_button == f"route:{view.route}"
            self._draw_route_button(surface, button_rect, selected_label, view.is_unlocked, is_hover)

            detail = self._route_detail(view.selected, view.locked_buffs)
            detail_width = max(80, button_rect.left - rect.x - 46)
            detail_text = fit_text_to_width(self._font_small, detail, (150, 176, 194), detail_width)
            surface.blit(detail_text, (rect.x + 24, rect.bottom - (28 if route_h < 86 else 34)))

    def _draw_hangar_module(self, surface: pygame.Surface, rect: pygame.Rect, status: dict, requisition_points: int = 0) -> None:
        left_w = int(rect.w * 0.46)
        left = pygame.Rect(rect.x, rect.y, left_w, rect.h)
        right = pygame.Rect(left.right + 18, rect.y, rect.w - left_w - 18, rect.h)

        draw_chamfered_panel(surface, left.x, left.y, left.w, left.h, (10, 24, 34), (58, 118, 138, 150), None, 7)
        title = self._font_section.render("战机库状态", True, (225, 242, 240))
        surface.blit(title, (left.x + 18, left.y + 16))
        rows = [
            ("机体完整", f"{status['health']}/{status['max_health']}", status["health_ratio"], (112, 206, 142)),
            ("加速燃料", f"{int(status['boost'])}/{int(status['boost_max'])}", status["boost_ratio"], (96, 192, 232)),
            ("火力指数", f"{status['damage']} DMG", status["damage_ratio"], (222, 184, 92)),
            ("射控冷却", f"{status['fire_interval']} F", status["fire_ratio"], (184, 128, 214)),
        ]
        ship_y = left.y + min(116, max(74, int(left.h * 0.34)))
        self._draw_ship_silhouette(surface, (left.centerx, ship_y), min(1.0, left.w / 420))

        row_step = 30 if left.h < 260 else 34
        bar_y = min(left.y + 188, left.bottom - len(rows) * row_step - 8)
        bar_y = max(left.y + 72, bar_y)
        for index, row in enumerate(rows):
            self._draw_status_row(surface, left.x + 20, bar_y + index * row_step, left.w - 40, *row)

        # Right side: actionable repair/recharge buttons + info cards
        from airwar.game.constants import GAME_CONSTANTS
        rp = requisition_points
        repair_cost = GAME_CONSTANTS.REQUISITION.REPAIR_COST
        recharge_cost = GAME_CONSTANTS.REQUISITION.RECHARGE_COST
        can_repair = rp >= repair_cost and status["health_ratio"] < 1.0
        can_recharge = rp >= recharge_cost and status["boost_ratio"] < 1.0

        btn_h = 50
        btn_gap = 8
        top_btn_y = right.y
        # Repair button
        repair_rect = pygame.Rect(right.x, top_btn_y, right.w, btn_h)
        self._button_rects["hangar:repair"] = repair_rect
        repair_hover = self._hovered_button == "hangar:repair"
        repair_label = f"维修机体 (-{repair_cost}RP)    HP → 100%"
        self._draw_action_button(surface, repair_rect, repair_label, can_repair, repair_hover, (112, 206, 142))

        # Recharge button
        recharge_rect = pygame.Rect(right.x, top_btn_y + btn_h + btn_gap, right.w, btn_h)
        self._button_rects["hangar:recharge"] = recharge_rect
        recharge_hover = self._hovered_button == "hangar:recharge"
        recharge_label = f"补给燃料 (-{recharge_cost}RP)   能量 → 100%"
        self._draw_action_button(surface, recharge_rect, recharge_label, can_recharge, recharge_hover, (96, 192, 232))

        # Requisition points display
        rp_text = self._font_small.render(f"征用点数: {rp} RP", True, (222, 224, 110))
        rp_rect = rp_text.get_rect(midright=(right.right, top_btn_y + btn_h * 2 + btn_gap + 14))
        surface.blit(rp_text, rp_rect)

        # Facility info cards below
        card_top = top_btn_y + btn_h * 2 + btn_gap * 2 + 38
        card_h_avail = right.bottom - card_top
        cards = [
            ("武器舱", "可切换", f"当前有效能力 {status['active_buff_count']} 项。", (222, 184, 92)),
            ("母舰链路", "已同步", f"冷却减免 {status['cooldown_reduction_pct']}%。", (94, 226, 210)),
        ]
        card_gap = 6
        card_h = max(44, (card_h_avail - card_gap * (len(cards) - 1)) // len(cards))
        for index, (title_text, state_text, detail, accent) in enumerate(cards):
            card = pygame.Rect(right.x, card_top + index * (card_h + card_gap), right.w, min(card_h, card_h_avail))
            if card.bottom > rect.bottom:
                card.h = max(1, rect.bottom - card.y)
            if card.h > 8:
                self._draw_facility_card(surface, card, title_text, state_text, detail, accent)

    def _draw_supply_module(self, surface: pygame.Surface, rect: pygame.Rect, status: dict, requisition_points: int = 0) -> None:
        rp = requisition_points
        title = self._font_section.render("维修补给站", True, (225, 242, 240))
        surface.blit(title, (rect.x, rect.y))
        rp_display = self._font_small.render(f"征用点数: {rp} RP", True, (222, 224, 110))
        surface.blit(rp_display, rp_display.get_rect(topright=(rect.right, rect.y + 4)))
        subtitle = fit_text_to_width(
            self._font_small,
            "击败Boss获得征用点数，在此消耗点数进行补给。",
            (142, 170, 186),
            rect.w - 260,
        )
        surface.blit(subtitle, (rect.x, rect.y + 36))

        button_rect = pygame.Rect(rect.right - 218, rect.y + 8, 190, 52)
        self._button_rects["supply:resupply"] = button_rect
        self._draw_resupply_button(surface, button_rect, self._hovered_button == "supply:resupply")

        card_y = rect.y + (74 if rect.h < 250 else 82)
        card_gap = 16
        card_w = (rect.w - card_gap * 2) // 3
        available_h = max(80, rect.bottom - card_y)
        log_gap = 12
        log_min_h = 58
        card_h = max(66, min(138, available_h - log_min_h - log_gap))
        cards = [
            ("机体维修", f"{status['health']}/{status['max_health']}", status["health_ratio"], (112, 206, 142)),
            ("燃料补能", f"{int(status['boost'])}/{int(status['boost_max'])}", status["boost_ratio"], (96, 192, 232)),
            (
                "母舰弹匣",
                f"{status['ammo_count']:.0f}/{status['ammo_max']:.0f}",
                status["ammo_ratio"],
                (222, 184, 92),
            ),
        ]
        for index, (label, value, ratio, color) in enumerate(cards):
            card = pygame.Rect(rect.x + index * (card_w + card_gap), card_y, card_w, card_h)
            draw_chamfered_panel(surface, card.x, card.y, card.w, card.h, (10, 24, 34), (*color, 165), None, 7)
            surface.blit(fit_text_to_width(self._font, label, (224, 242, 240), card.w - 36), (card.x + 18, card.y + 14))
            surface.blit(self._font_small.render(value, True, (190, 210, 218)), (card.x + 20, card.y + 42))
            meter_y = max(card.y + 62, card.bottom - 30)
            self._draw_meter(surface, pygame.Rect(card.x + 20, meter_y, card.w - 40, 14), ratio, color)

        log_y = card_y + card_h + log_gap
        log_rect = pygame.Rect(rect.x, log_y, rect.w, max(0, rect.bottom - log_y))
        draw_chamfered_panel(surface, log_rect.x, log_rect.y, log_rect.w, log_rect.h, (8, 18, 28), (64, 98, 118, 150), None, 7)
        logs = [
            "补给完成后会立刻写入当前基地配置。",
            "母舰弹匣随战斗冷却与驻留时间变化，基地会显示当前链路状态。",
            "离开基地后恢复战斗控制，并获得短暂无敌窗口。",
        ]
        visible_lines = min(len(logs), max(0, (log_rect.h - 18) // 22))
        for index, text in enumerate(logs[:visible_lines]):
            y = log_rect.y + 14 + index * 22
            surface.blit(fit_text_to_width(self._font_small, text, (150, 176, 194), log_rect.w - 38), (log_rect.x + 18, y))

    def _draw_mission_module(self, surface: pygame.Surface, rect: pygame.Rect, status: dict, requisition_points: int = 0) -> None:
        draw_chamfered_panel(surface, rect.x, rect.y, rect.w, rect.h, (10, 24, 34), (58, 118, 138, 150), None, 7)
        title = self._font_section.render("任务规划台", True, (225, 242, 240))
        surface.blit(title, (rect.x + 18, rect.y + 16))

        # Draw all active missions with progress bars
        missions = getattr(self, '_missions', [])
        if not missions:
            empty_text = self._font.render("暂无任务", True, (150, 176, 194))
            surface.blit(empty_text, empty_text.get_rect(center=rect.center))
            return

        mission_y = rect.y + 56
        available_h = rect.h - 72
        mission_h = min(64, (available_h - 12 * (len(missions) - 1)) // len(missions))
        for i, mission in enumerate(missions):
            my = mission_y + i * (mission_h + 12)
            if my + mission_h > rect.bottom:
                break
            mr = pygame.Rect(rect.x + 22, my, rect.w - 44, mission_h)
            draw_chamfered_panel(surface, mr.x, mr.y, mr.w, mr.h, (12, 22, 32), (62, 104, 124, 120), None, 5)
            # Mission name + description
            name_text = self._font.render(mission["name"], True, (225, 242, 240))
            surface.blit(name_text, (mr.x + 14, mr.y + 8))
            desc_text = self._font_small.render(mission["desc"], True, (150, 176, 194))
            surface.blit(desc_text, (mr.x + 18, mr.y + 32))
            # Progress bar
            ratio = min(1.0, mission["progress"] / max(1, mission["goal"]))
            bar_color = (112, 206, 142) if mission["done"] else (222, 184, 92)
            bar_x = mr.right - 190
            bar_rect = pygame.Rect(bar_x, mr.y + mr.h // 2 - 7, 168, 14)
            self._draw_meter(surface, bar_rect, ratio, bar_color)
            prog_text = self._font_small.render(
                f"{min(mission['progress'], mission['goal'])}/{mission['goal']}" + (" ✓" if mission["done"] else ""),
                True, (180, 210, 218) if not mission["done"] else (112, 206, 142))
            surface.blit(prog_text, (bar_x - prog_text.get_width() - 10, mr.y + mr.h // 2 - prog_text.get_height() // 2))

    def _draw_facility_card(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        title: str,
        status: str,
        detail: str,
        accent: tuple[int, int, int],
    ) -> None:
        draw_chamfered_panel(surface, rect.x, rect.y, rect.w, rect.h, (10, 21, 31), (*accent, 145), None, 7)
        pygame.draw.rect(surface, accent, pygame.Rect(rect.x + 16, rect.y + 17, 4, max(30, rect.h - 34)))
        title_y = rect.y + (10 if rect.h < 64 else 14)
        surface.blit(fit_text_to_width(self._font, title, (226, 242, 240), rect.w - 160), (rect.x + 32, title_y))
        status_surf = fit_text_to_width(self._font_small, status, accent, 100)
        surface.blit(status_surf, status_surf.get_rect(topright=(rect.right - 18, rect.y + (14 if rect.h < 64 else 18))))
        if rect.h >= 52:
            surface.blit(
                fit_text_to_width(self._font_small, detail, (145, 170, 188), rect.w - 50),
                (rect.x + 32, rect.y + (36 if rect.h < 64 else 46)),
            )

    def _draw_big_metric(self, surface: pygame.Surface, x: int, y: int, label: str, value: str, max_width: int) -> None:
        value_surf = fit_text_to_width(self._font_section, value, (104, 238, 220), max_width)
        label_surf = self._font_tiny.render(label, True, (126, 150, 168))
        surface.blit(value_surf, (x, y))
        surface.blit(label_surf, (x, y + 34))

    def _draw_status_row(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        width: int,
        label: str,
        value: str,
        ratio: float,
        color: tuple[int, int, int],
    ) -> None:
        label_surf = fit_text_to_width(self._font_small, label, (164, 186, 198), max(80, width // 3))
        value_surf = fit_text_to_width(self._font_small, value, (218, 234, 232), max(70, width // 4))
        surface.blit(label_surf, (x, y))
        surface.blit(value_surf, value_surf.get_rect(topright=(x + width, y)))
        meter = pygame.Rect(x, y + 22, width, 10)
        self._draw_meter(surface, meter, ratio, color)

    def _draw_meter(self, surface: pygame.Surface, rect: pygame.Rect, ratio: float, color: tuple[int, int, int]) -> None:
        ratio = max(0.0, min(1.0, ratio))
        pygame.draw.rect(surface, (18, 28, 36), rect)
        pygame.draw.rect(surface, (62, 82, 94), rect, 1)
        if rect.w > 4 and ratio > 0:
            fill = rect.inflate(-4, -4)
            fill.w = max(1, int(fill.w * ratio))
            pygame.draw.rect(surface, color, fill)

    def _draw_action_button(self, surface: pygame.Surface, rect: pygame.Rect, label: str, enabled: bool, hovered: bool, accent: tuple[int, int, int]) -> None:
        """Draw an actionable base button (repair/recharge)."""
        if enabled:
            bg = (min(255, accent[0] // 3 + 12), min(255, accent[1] // 3 + 8), min(255, accent[2] // 3 + 6))
            border = (*accent, 210)
            if hovered:
                bg = (min(255, accent[0] // 2 + 20), min(255, accent[1] // 2 + 16), min(255, accent[2] // 2 + 12))
                border = (*accent, 255)
        else:
            bg = (18, 22, 28)
            border = (52, 58, 68, 120)
        draw_chamfered_panel(surface, rect.x, rect.y, rect.w, rect.h, bg, border, None, 6)
        color = (220, 236, 242) if enabled else (92, 98, 108)
        text = fit_text_to_width(self._font_small, label, color, rect.w - 16)
        surface.blit(text, text.get_rect(center=rect.center))

    def _draw_ship_silhouette(self, surface: pygame.Surface, center: tuple[int, int], scale: float) -> None:
        cx, cy = center
        pulse = 0.5 + 0.5 * math.sin(self._frame * 0.08)
        points = [
            (cx, cy - int(62 * scale)),
            (cx + int(34 * scale), cy + int(34 * scale)),
            (cx + int(13 * scale), cy + int(23 * scale)),
            (cx, cy + int(58 * scale)),
            (cx - int(13 * scale), cy + int(23 * scale)),
            (cx - int(34 * scale), cy + int(34 * scale)),
        ]
        pygame.draw.polygon(surface, (42, 60, 70), points)
        pygame.draw.polygon(surface, (112, 190, 198), points, 2)
        pygame.draw.circle(surface, (92, 226, 210), (cx, cy - int(18 * scale)), max(5, int(8 * scale)))
        glow_radius = int((14 + 5 * pulse) * scale)
        for ex in (cx - int(18 * scale), cx + int(18 * scale)):
            pygame.draw.circle(surface, (222, 184, 92), (ex, cy + int(38 * scale)), max(3, glow_radius), 1)

    def _draw_resupply_button(self, surface: pygame.Surface, rect: pygame.Rect, hovered: bool) -> None:
        bg = (34, 68, 50) if hovered else (24, 50, 40)
        border = (148, 234, 158, 230) if hovered else (104, 198, 128, 180)
        draw_chamfered_panel(surface, rect.x, rect.y, rect.w, rect.h, bg, border, None, 8)
        label = fit_text_to_width(self._font, "执行补给", (232, 252, 238), rect.w - 28)
        surface.blit(label, label.get_rect(center=rect.center))

    def _draw_route_button(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        text: str,
        enabled: bool,
        hovered: bool,
    ) -> None:
        if enabled:
            bg = (18, 42, 55) if hovered else (14, 32, 44)
            border = (115, 250, 232, 220) if hovered else (78, 220, 204, 170)
            color = (224, 248, 246)
        else:
            bg = (20, 24, 30)
            border = (76, 86, 98, 150)
            color = (110, 124, 138)
        draw_chamfered_panel(surface, rect.x, rect.y, rect.w, rect.h, bg, border, None, 8)
        text_surface = self._font.render(text, True, color)
        surface.blit(text_surface, text_surface.get_rect(center=rect.center))

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
        surface.blit(
            fit_text_to_width(self._font_small, MODULE_HINTS.get(self._active_module, hint), (132, 154, 172), text_width),
            (rect.x + 20, rect.y + 52),
        )
        self._draw_continue_button(surface, button_rect, self._hovered_button == "continue")

    def _draw_continue_button(self, surface: pygame.Surface, rect: pygame.Rect, hovered: bool) -> None:
        bg = (24, 62, 70) if hovered else (18, 44, 54)
        border = (126, 255, 233, 235) if hovered else (82, 224, 204, 180)
        draw_chamfered_panel(surface, rect.x, rect.y, rect.w, rect.h, bg, border, None, 8)
        label = fit_text_to_width(self._font, "继续出击", (232, 252, 248), rect.w - 28)
        surface.blit(label, label.get_rect(center=rect.center))

    def _route_detail(self, selected: str | None, locked_buffs: tuple[str, ...]) -> str:
        if not selected:
            return "尚未获得该路线天赋，暂不可切换。"
        if locked_buffs:
            locked = "、".join(BUFF_LABELS.get(name, name) for name in locked_buffs)
            return f"强化 {BUFF_LABELS.get(selected, selected)}，关闭 {locked}。"
        return f"保持 {BUFF_LABELS.get(selected, selected)} 生效。"

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
