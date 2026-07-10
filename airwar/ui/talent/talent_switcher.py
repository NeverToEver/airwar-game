"""Talent switcher — Offense/Support route selection rendering and clicks.

Owns the loadout (route) panel: per-route view rendering, route-button hit
hit detection, and the ``route:<name>`` button registry. Has no business logic
of its own — all state lives on the parent ``BaseTalentConsole`` and the
``TalentBalanceManager`` passed at render time.
"""

import pygame

from ..chamfered_panel import draw_chamfered_panel
from ..scene_rendering_utils import fit_text_to_width

BUFF_LABELS = {
    "Spread Shot": "散射弹幕",
    "Laser": "激光模式",
    "Phase Dash": "相位突进",
    "Mothership Recall": "母舰冷却",
}


class TalentSwitcher:
    """Offense/Support route selection widget.

    The widget is a pure renderer/dispatcher: it reads route views from a
    ``TalentBalanceManager`` and writes ``route:<name>`` button rects back
    into the shared ``button_rects`` dict on each render. The parent
    orchestrator owns the hovered-button state.
    """

    def __init__(self, button_rects: dict[str, pygame.Rect], hovered_button_getter, fonts: dict):
        self._button_rects = button_rects
        self._get_hovered = hovered_button_getter
        self._fonts = fonts  # {"font": ..., "font_small": ..., "font_tiny": ...}

    def render_loadout_module(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        manager,
    ) -> None:
        """Render the loadout (weapon route) module inside ``rect``."""
        font = self._fonts["font"]
        font_small = self._fonts["font_small"]
        compact = rect.h < 250
        intro_h = 46 if compact else 54
        intro = pygame.Rect(rect.x, rect.y, rect.w, intro_h)
        draw_chamfered_panel(surface, intro.x, intro.y, intro.w, intro.h, (10, 25, 36), (58, 126, 142, 150), None, 6)
        title = font.render("武器挂载台", True, (224, 244, 244))
        body = "选择同一路线内的主模式；未选中的互斥能力会被基地临时关闭。"
        title_y = intro.y + (9 if compact else 13)
        surface.blit(title, (intro.x + 18, title_y))
        surface.blit(
            fit_text_to_width(font_small, body, (142, 170, 186), intro.w - 260),
            (intro.x + 190, intro.y + (13 if compact else 17)),
        )
        route_gap = 10 if compact else 14
        route_top_gap = 14 if compact else 18
        route_h = max(58, min(124, (rect.h - intro_h - route_top_gap - route_gap) // 2))
        self._render_routes(
            surface,
            rect.x,
            intro.bottom + route_top_gap,
            rect.w,
            manager,
            route_h=route_h,
            route_gap=route_gap,
        )

    def _render_routes(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        width: int,
        manager,
        route_h: int = 124,
        route_gap: int = 14,
    ) -> None:
        font = self._fonts["font"]
        font_small = self._fonts["font_small"]
        for index, view in enumerate(manager.route_views()):
            rect = pygame.Rect(x, y + index * (route_h + route_gap), width, route_h)
            border = (84, 230, 210, 180) if view.is_unlocked else (80, 96, 112, 145)
            draw_chamfered_panel(surface, rect.x, rect.y, rect.w, rect.h, (11, 21, 34), border, None, 8)

            label = font.render(view.label, True, (218, 238, 238))
            budget = font_small.render(f"路线点数 {view.budget}", True, (146, 174, 190))
            surface.blit(label, (rect.x + 22, rect.y + 18))
            surface.blit(budget, (rect.x + 24, rect.y + 52))

            button_w = min(250, max(190, rect.w // 4))
            button_y_pad = 16 if route_h < 86 else 24
            button_rect = pygame.Rect(
                rect.right - button_w - 26, rect.y + button_y_pad, button_w, max(44, route_h - button_y_pad * 2)
            )
            self._button_rects[f"route:{view.route}"] = button_rect
            selected = view.selected or "未解锁"
            selected_label = BUFF_LABELS.get(selected, selected)
            is_hover = self._get_hovered() == f"route:{view.route}"
            self._render_route_button(surface, button_rect, selected_label, view.is_unlocked, is_hover)

            detail = self._route_detail(view.selected, view.locked_buffs)
            detail_width = max(80, button_rect.left - rect.x - 46)
            detail_text = fit_text_to_width(font_small, detail, (150, 176, 194), detail_width)
            surface.blit(detail_text, (rect.x + 24, rect.bottom - (28 if route_h < 86 else 34)))

    def _render_route_button(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        text: str,
        enabled: bool,
        hovered: bool,
    ) -> None:
        font = self._fonts["font"]
        if enabled:
            bg = (18, 42, 55) if hovered else (14, 32, 44)
            border = (115, 250, 232, 220) if hovered else (78, 220, 204, 170)
            color = (224, 248, 246)
        else:
            bg = (20, 24, 30)
            border = (76, 86, 98, 150)
            color = (110, 124, 138)
        draw_chamfered_panel(surface, rect.x, rect.y, rect.w, rect.h, bg, border, None, 8)
        text_surface = font.render(text, True, color)
        surface.blit(text_surface, text_surface.get_rect(center=rect.center))

    @staticmethod
    def _route_detail(selected: str | None, locked_buffs: tuple[str, ...]) -> str:
        if not selected:
            return "尚未获得该路线天赋，暂不可切换。"
        if locked_buffs:
            locked = "、".join(BUFF_LABELS.get(name, name) for name in locked_buffs)
            return f"强化 {BUFF_LABELS.get(selected, selected)}，关闭 {locked}。"
        return f"保持 {BUFF_LABELS.get(selected, selected)} 生效。"
