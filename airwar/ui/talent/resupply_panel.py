"""Resupply panel — resupply action button and the supply module body.

Owns the supply module (resupply trigger + status cards + activity log).
Reads player/mothership status from the parent's ``_collect_base_status``
output and writes the ``supply:resupply`` button rect on each render.
"""

import pygame

from ..chamfered_panel import draw_chamfered_panel
from ..scene_rendering_utils import fit_text_to_width


class ResupplyPanel:
    """Resupply action panel widget.

    The widget is a pure renderer: it writes the ``supply:resupply``
    button rect and draws status cards / activity log. State and
    permission logic (RP cost, max-ratio gating) live on the parent
    console and are passed in via ``status`` / ``requisition_points``.
    """

    def __init__(self, button_rects: dict[str, pygame.Rect], hovered_button_getter, fonts: dict):
        self._button_rects = button_rects
        self._get_hovered = hovered_button_getter
        self._fonts = fonts

    def render_supply_module(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        status: dict,
        requisition_points: int = 0,
    ) -> None:
        """Render the supply module inside ``rect``."""
        font = self._fonts["font"]
        font_section = self._fonts["font_section"]
        font_small = self._fonts["font_small"]
        rp = requisition_points
        button_rect = pygame.Rect(rect.right - 218, rect.y + 8, 190, 52)
        title = font_section.render("维修补给站", True, (225, 242, 240))
        rp_display = font_small.render(f"征用点数: {rp} RP", True, (222, 224, 110))
        subtitle = fit_text_to_width(
            font_small,
            "击败Boss获得征用点数，在此消耗点数进行补给。",
            (142, 170, 186),
            rect.w - 260,
        )

        # Layout: title | rp (left of button) | button (right)
        surface.blit(title, (rect.x, rect.y))
        rp_x = min(rect.x + title.get_width() + 24, button_rect.left - rp_display.get_width() - 16)
        surface.blit(rp_display, (rp_x, rect.y + 8))
        surface.blit(subtitle, (rect.x, rect.y + 36))

        self._button_rects["supply:resupply"] = button_rect
        self._render_resupply_button(surface, button_rect, self._get_hovered() == "supply:resupply")

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
            surface.blit(
                fit_text_to_width(font, label, (224, 242, 240), card.w - 36),
                (card.x + 18, card.y + 14),
            )
            surface.blit(font_small.render(value, True, (190, 210, 218)), (card.x + 20, card.y + 42))
            meter_y = max(card.y + 62, card.bottom - 30)
            self._render_meter(surface, pygame.Rect(card.x + 20, meter_y, card.w - 40, 14), ratio, color)

        log_y = card_y + card_h + log_gap
        log_rect = pygame.Rect(rect.x, log_y, rect.w, max(0, rect.bottom - log_y))
        draw_chamfered_panel(
            surface, log_rect.x, log_rect.y, log_rect.w, log_rect.h, (8, 18, 28), (64, 98, 118, 150), None, 7
        )
        logs = [
            "补给完成后会立刻写入当前基地配置。",
            "母舰弹匣随战斗冷却与驻留时间变化，基地会显示当前链路状态。",
            "离开基地后恢复战斗控制，并获得短暂无敌窗口。",
        ]
        visible_lines = min(len(logs), max(0, (log_rect.h - 18) // 22))
        for index, text in enumerate(logs[:visible_lines]):
            y = log_rect.y + 14 + index * 22
            text_surf = fit_text_to_width(font_small, text, (150, 176, 194), log_rect.w - 38)
            surface.blit(text_surf, (log_rect.x + 18, y))

    @staticmethod
    def _render_meter(
        surface: pygame.Surface,
        rect: pygame.Rect,
        ratio: float,
        color: tuple[int, int, int],
    ) -> None:
        ratio = max(0.0, min(1.0, ratio))
        pygame.draw.rect(surface, (18, 28, 36), rect)
        pygame.draw.rect(surface, (62, 82, 94), rect, 1)
        if rect.w > 4 and ratio > 0:
            fill = rect.inflate(-4, -4)
            fill.w = max(1, int(fill.w * ratio))
            pygame.draw.rect(surface, color, fill)

    def _render_resupply_button(self, surface: pygame.Surface, rect: pygame.Rect, hovered: bool) -> None:
        font = self._fonts["font"]
        bg = (34, 68, 50) if hovered else (24, 50, 40)
        border = (148, 234, 158, 230) if hovered else (104, 198, 128, 180)
        draw_chamfered_panel(surface, rect.x, rect.y, rect.w, rect.h, bg, border, None, 8)
        label = fit_text_to_width(font, "执行补给", (232, 252, 238), rect.w - 28)
        surface.blit(label, label.get_rect(center=rect.center))
