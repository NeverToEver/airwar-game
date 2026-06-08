"""Mission list — mission rendering and progress bars.

Owns the mission module body: per-mission row layout, progress bar,
done/pending visual state. The mission ``list[dict]`` itself lives on
the parent console (so the parent can refresh it from outside).
"""

import pygame

from ..chamfered_panel import draw_chamfered_panel


class MissionList:
    """Mission list widget.

    The widget is a pure renderer: it reads the parent console's
    ``_missions`` list and draws each row. State (mission dicts) lives
    on the parent — this widget only owns the visual layout.
    """

    def __init__(self, missions_getter, fonts: dict):
        self._get_missions = missions_getter
        self._fonts = fonts

    def render_mission_module(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
    ) -> None:
        """Render the mission module inside ``rect``."""
        font = self._fonts["font"]
        font_section = self._fonts["font_section"]
        font_small = self._fonts["font_small"]
        draw_chamfered_panel(surface, rect.x, rect.y, rect.w, rect.h, (10, 24, 34), (58, 118, 138, 150), None, 7)
        title = font_section.render("任务规划台", True, (225, 242, 240))
        surface.blit(title, (rect.x + 18, rect.y + 16))

        missions = self._get_missions()
        if not missions:
            empty_text = font.render("暂无任务", True, (150, 176, 194))
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
            name_text = font.render(mission["name"], True, (225, 242, 240))
            surface.blit(name_text, (mr.x + 14, mr.y + 8))
            desc_text = font_small.render(mission["desc"], True, (150, 176, 194))
            surface.blit(desc_text, (mr.x + 18, mr.y + 32))
            # Progress bar
            ratio = min(1.0, mission["progress"] / max(1, mission["goal"]))
            bar_color = (112, 206, 142) if mission["done"] else (222, 184, 92)
            bar_x = mr.right - 190
            bar_rect = pygame.Rect(bar_x, mr.y + mr.h // 2 - 7, 168, 14)
            self._render_meter(surface, bar_rect, ratio, bar_color)
            prog_text = font_small.render(
                f"{min(mission['progress'], mission['goal'])}/{mission['goal']}" + (" ✓" if mission["done"] else ""),
                True,
                (180, 210, 218) if not mission["done"] else (112, 206, 142),
            )
            surface.blit(
                prog_text,
                (bar_x - prog_text.get_width() - 10, mr.y + mr.h // 2 - prog_text.get_height() // 2),
            )

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
