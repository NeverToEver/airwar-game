"""Base-side talent loadout console."""

from dataclasses import dataclass
import math

import pygame

from airwar.game.systems.talent_balance_manager import BUFF_LABELS, TalentBalanceManager
from airwar.ui.chamfered_panel import draw_chamfered_panel
from airwar.ui.scene_rendering_utils import fit_text_to_width
from airwar.utils.fonts import get_cjk_font


@dataclass(frozen=True)
class BaseTalentConsoleAction:
    """Semantic action requested by the base console."""

    CONTINUE = "continue"
    SELECT_ROUTE = "select_route"

    kind: str
    route: str | None = None

    @classmethod
    def continue_sortie(cls) -> "BaseTalentConsoleAction":
        return cls(cls.CONTINUE)

    @classmethod
    def select_route(cls, route: str) -> "BaseTalentConsoleAction":
        return cls(cls.SELECT_ROUTE, route)


class BaseTalentConsole:
    """Renders and handles the first base interaction surface."""

    def __init__(self, screen_width: int, screen_height: int):
        self._screen_width = screen_width
        self._screen_height = screen_height
        self._font_title = get_cjk_font(34)
        self._font = get_cjk_font(22)
        self._font_small = get_cjk_font(17)
        self._button_rects: dict[str, pygame.Rect] = {}
        self._hovered_button: str | None = None
        self._frame = 0

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
        route = self._route_from_button(button)
        if route:
            return BaseTalentConsoleAction.select_route(route)
        return None

    def render(self, surface: pygame.Surface, manager: TalentBalanceManager, reward_system) -> None:
        self._button_rects.clear()
        sw, sh = surface.get_size()
        self._render_backdrop(surface)

        panel_w = min(1080, sw - 120)
        panel_h = min(650, sh - 110)
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
        self._draw_routes(surface, x + 34, y + 128, panel_w - 68, manager)
        self._draw_summary(surface, x + 34, y + panel_h - 132, panel_w - 68, reward_system)

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

    def _draw_header(self, surface: pygame.Surface, x: int, y: int, panel_w: int, manager: TalentBalanceManager) -> None:
        title = self._font_title.render("基地整备: 天赋重分配", True, (226, 246, 244))
        subtitle = self._font_small.render(
            "总天赋点保持不变；切换路线会关闭互斥能力，并把该路线点数集中到当前选择。",
            True,
            (145, 170, 188),
        )
        points = self._font.render(f"可分配点数 {manager.total_points()}", True, (104, 238, 220))
        surface.blit(title, (x + 34, y + 28))
        surface.blit(subtitle, (x + 36, y + 78))
        surface.blit(points, points.get_rect(topright=(x + panel_w - 34, y + 34)))

    def _draw_routes(self, surface: pygame.Surface, x: int, y: int, width: int, manager: TalentBalanceManager) -> None:
        route_gap = 26
        route_h = 138
        for index, view in enumerate(manager.route_views()):
            rect = pygame.Rect(x, y + index * (route_h + route_gap), width, route_h)
            border = (84, 230, 210, 180) if view.is_unlocked else (80, 96, 112, 145)
            draw_chamfered_panel(surface, rect.x, rect.y, rect.w, rect.h, (11, 21, 34), border, None, 8)

            label = self._font.render(view.label, True, (218, 238, 238))
            budget = self._font_small.render(f"路线点数 {view.budget}", True, (146, 174, 190))
            surface.blit(label, (rect.x + 22, rect.y + 18))
            surface.blit(budget, (rect.x + 24, rect.y + 52))

            button_rect = pygame.Rect(rect.right - 302, rect.y + 28, 250, 76)
            self._button_rects[f"route:{view.route}"] = button_rect
            selected = view.selected or "未解锁"
            selected_label = BUFF_LABELS.get(selected, selected)
            is_hover = self._hovered_button == f"route:{view.route}"
            self._draw_route_button(surface, button_rect, selected_label, view.is_unlocked, is_hover)

            detail = self._route_detail(view.selected, view.locked_buffs)
            detail_text = self._font_small.render(detail, True, (150, 176, 194))
            surface.blit(detail_text, (rect.x + 24, rect.bottom - 38))

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
            fit_text_to_width(self._font_small, hint, (132, 154, 172), text_width),
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

    def _route_from_button(self, button: str) -> str | None:
        if button.startswith("route:"):
            return button.split(":", 1)[1]
        return None
