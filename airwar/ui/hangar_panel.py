"""Hangar panel — ship silhouette, status rows, repair/recharge buttons.

Phase 5-δ extraction. The hangar module of the base console
(``airwar.ui.base_talent_console``) was the largest single block
left after the Phase 4 Wave beta split. This widget owns:

* the ship silhouette
* the four status rows (health / boost / damage / fire-rate)
* the repair / recharge action buttons
* the facility info cards

It writes the ``hangar:repair`` and ``hangar:recharge`` button rects
into the shared ``button_rects`` dict on each render. State and
permission logic (RP cost, max-ratio gating) live on the parent
console and are passed in via ``status`` / ``requisition_points``.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from airwar.config.constants_access import get_game_constants

from .chamfered_panel import draw_chamfered_panel
from .scene_rendering_utils import fit_text_to_width

if TYPE_CHECKING:
    from collections.abc import Callable


class HangarPanel:
    """Hangar module renderer — ship silhouette, status, repair/recharge.

    Pure renderer: writes the ``hangar:repair`` and ``hangar:recharge``
    button rects and draws ship art, status rows and facility cards.
    State and gating live on the parent console and are passed in via
    ``status`` / ``requisition_points`` and the ``_frame`` counter.
    """

    def __init__(
        self,
        button_rects: dict[str, pygame.Rect],
        hovered_button_getter: Callable[[], str | None],
        fonts: dict,
    ):
        self._button_rects = button_rects
        self._get_hovered = hovered_button_getter
        self._fonts = fonts

    def render_hangar_module(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        status: dict,
        requisition_points: int = 0,
        frame: int = 0,
    ) -> None:
        """Draw the hangar module inside ``rect``.

        The status dict is the parent's ``_collect_base_status`` output;
        ``frame`` drives the ship silhouette pulse animation.
        """
        font_section = self._fonts["font_section"]
        font_small = self._fonts["font_small"]

        left_w = int(rect.w * 0.46)
        left = pygame.Rect(rect.x, rect.y, left_w, rect.h)
        right = pygame.Rect(left.right + 18, rect.y, rect.w - left_w - 18, rect.h)

        draw_chamfered_panel(surface, left.x, left.y, left.w, left.h, (10, 24, 34), (58, 118, 138, 150), None, 7)
        title = font_section.render("战机库状态", True, (225, 242, 240))
        surface.blit(title, (left.x + 18, left.y + 16))
        rows = [
            ("机体完整", f"{status['health']}/{status['max_health']}", status["health_ratio"], (112, 206, 142)),
            ("加速燃料", f"{int(status['boost'])}/{int(status['boost_max'])}", status["boost_ratio"], (96, 192, 232)),
            ("火力指数", f"{status['damage']} DMG", status["damage_ratio"], (222, 184, 92)),
            ("射控冷却", f"{status['fire_interval']} F", status["fire_ratio"], (184, 128, 214)),
        ]
        ship_y = left.y + min(116, max(74, int(left.h * 0.34)))
        self._draw_ship_silhouette(surface, (left.centerx, ship_y), min(1.0, left.w / 420), frame)

        row_step = 30 if left.h < 260 else 34
        bar_y = min(left.y + 188, left.bottom - len(rows) * row_step - 8)
        bar_y = max(left.y + 72, bar_y)
        for index, row in enumerate(rows):
            self._draw_status_row(surface, left.x + 20, bar_y + index * row_step, left.w - 40, *row)

        # Right side: actionable repair/recharge buttons + info cards
        rp = requisition_points
        requisition = get_game_constants().REQUISITION
        repair_cost = requisition.REPAIR_COST
        recharge_cost = requisition.RECHARGE_COST
        can_repair = rp >= repair_cost and status["health_ratio"] < 1.0
        can_recharge = rp >= recharge_cost and status["boost_ratio"] < 1.0

        btn_h = 50
        btn_gap = 8
        top_btn_y = right.y
        # Repair button
        repair_rect = pygame.Rect(right.x, top_btn_y, right.w, btn_h)
        self._button_rects["hangar:repair"] = repair_rect
        repair_hover = self._get_hovered() == "hangar:repair"
        repair_label = f"维修机体 (-{repair_cost}RP)    HP → 100%"
        self._draw_action_button(surface, repair_rect, repair_label, can_repair, repair_hover, (112, 206, 142))

        # Recharge button
        recharge_rect = pygame.Rect(right.x, top_btn_y + btn_h + btn_gap, right.w, btn_h)
        self._button_rects["hangar:recharge"] = recharge_rect
        recharge_hover = self._get_hovered() == "hangar:recharge"
        recharge_label = f"补给燃料 (-{recharge_cost}RP)   能量 → 100%"
        self._draw_action_button(surface, recharge_rect, recharge_label, can_recharge, recharge_hover, (96, 192, 232))

        # Requisition points display
        rp_text = font_small.render(f"征用点数: {rp} RP", True, (222, 224, 110))
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

    def _draw_facility_card(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        title: str,
        status: str,
        detail: str,
        accent: tuple[int, int, int],
    ) -> None:
        font = self._fonts["font"]
        font_small = self._fonts["font_small"]
        draw_chamfered_panel(surface, rect.x, rect.y, rect.w, rect.h, (10, 21, 31), (*accent, 145), None, 7)
        pygame.draw.rect(surface, accent, pygame.Rect(rect.x + 16, rect.y + 17, 4, max(30, rect.h - 34)))
        title_y = rect.y + (10 if rect.h < 64 else 14)
        surface.blit(fit_text_to_width(font, title, (226, 242, 240), rect.w - 160), (rect.x + 32, title_y))
        status_surf = fit_text_to_width(font_small, status, accent, 100)
        status_rect = status_surf.get_rect(topright=(rect.right - 18, rect.y + (14 if rect.h < 64 else 18)))
        surface.blit(status_surf, status_rect)
        if rect.h >= 52:
            surface.blit(
                fit_text_to_width(font_small, detail, (145, 170, 188), rect.w - 50),
                (rect.x + 32, rect.y + (36 if rect.h < 64 else 46)),
            )

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
        font_small = self._fonts["font_small"]
        label_surf = fit_text_to_width(font_small, label, (164, 186, 198), max(80, width // 3))
        value_surf = fit_text_to_width(font_small, value, (218, 234, 232), max(70, width // 4))
        surface.blit(label_surf, (x, y))
        surface.blit(value_surf, value_surf.get_rect(topright=(x + width, y)))
        meter = pygame.Rect(x, y + 22, width, 10)
        self._draw_meter(surface, meter, ratio, color)

    def _draw_meter(
        self, surface: pygame.Surface, rect: pygame.Rect, ratio: float, color: tuple[int, int, int]
    ) -> None:
        ratio = max(0.0, min(1.0, ratio))
        pygame.draw.rect(surface, (18, 28, 36), rect)
        pygame.draw.rect(surface, (62, 82, 94), rect, 1)
        if rect.w > 4 and ratio > 0:
            fill = rect.inflate(-4, -4)
            fill.w = max(1, int(fill.w * ratio))
            pygame.draw.rect(surface, color, fill)

    def _draw_action_button(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        label: str,
        enabled: bool,
        hovered: bool,
        accent: tuple[int, int, int],
    ) -> None:
        """Draw an actionable base button (repair/recharge)."""
        font_small = self._fonts["font_small"]
        if enabled:
            bg = (min(255, accent[0] // 3 + 12), min(255, accent[1] // 3 + 8), min(255, accent[2] // 3 + 6))
            border = (*accent, 210)
            if hovered:
                bg = (
                    min(255, accent[0] // 2 + 20),
                    min(255, accent[1] // 2 + 16),
                    min(255, accent[2] // 2 + 12),
                )
                border = (*accent, 255)
        else:
            bg = (18, 22, 28)
            border = (52, 58, 68, 120)
        draw_chamfered_panel(surface, rect.x, rect.y, rect.w, rect.h, bg, border, None, 6)
        color = (220, 236, 242) if enabled else (92, 98, 108)
        text = fit_text_to_width(font_small, label, color, rect.w - 16)
        surface.blit(text, text.get_rect(center=rect.center))

    def _draw_ship_silhouette(
        self, surface: pygame.Surface, center: tuple[int, int], scale: float, frame: int = 0
    ) -> None:
        cx, cy = center
        pulse = 0.5 + 0.5 * math.sin(frame * 0.08)
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


__all__ = ["HangarPanel"]
