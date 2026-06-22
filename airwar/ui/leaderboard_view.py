"""Leaderboard view — renders the top 10 high scores (local or remote)."""

import pygame

from airwar.config.design_tokens import SceneColors, get_design_tokens
from airwar.i18n import t
from airwar.leaderboard import LeaderboardService
from airwar.ui.chamfered_panel import draw_chamfered_panel
from airwar.utils.database import LEADERBOARD_CAP, UserDB
from airwar.utils.fonts import get_cjk_font


class LeaderboardView:
    """Simple, self-contained leaderboard overlay renderer.

    Reads the top scores from a :class:`LeaderboardService` instance
    (defaulting to the shared on-disk local database) and renders them as
    a centered panel. The footer indicates whether the data comes from the
    global remote server, the local database, or a local fallback due to a
    remote outage.
    """

    PANEL_W = 520
    PANEL_H = 580
    CHAMFER = 12
    ROW_H = 38
    HEADER_GAP = 18
    RANK_COL_W = 60
    SCORE_COL_W = 140
    ROW_INDENT = 24

    def __init__(self, service: LeaderboardService | None = None):
        self._service = service if service is not None else LeaderboardService(UserDB())
        self._tokens = get_design_tokens()
        self._fonts_initialized = False
        self._title_font = None
        self._row_font = None
        self._empty_font = None

    def _ensure_fonts(self) -> None:
        if self._fonts_initialized:
            return
        pygame.font.init()
        tokens = self._tokens
        self._title_font = get_cjk_font(tokens.typography.SUBHEADING_SIZE)
        self._row_font = get_cjk_font(tokens.typography.BODY_SIZE)
        self._empty_font = get_cjk_font(tokens.typography.HUD_SIZE)
        self._fonts_initialized = True

    def set_service(self, service: LeaderboardService) -> None:
        """Inject an alternate service (e.g. one wired to a test database)."""
        self._service = service

    def set_user_db(self, user_db: UserDB) -> None:
        """Backward-compatible helper that wraps a raw UserDB in a service."""
        self._service = LeaderboardService(user_db)

    def fetch_entries(self) -> list[dict]:
        """Return the current top-10 leaderboard entries."""
        return self._service.get_leaderboard()

    def _footer_text(self) -> str:
        """Compose the footer label based on the active backend."""
        if self._service.is_remote_active():
            suffix = t("leaderboard.footer.global")
        elif self._service.is_local_only():
            suffix = t("leaderboard.footer.local")
        else:
            suffix = t("leaderboard.footer.offline")
        return f"Top {LEADERBOARD_CAP}  ·  {suffix}"

    def render(self, surface: pygame.Surface, screen_w: int, screen_h: int) -> None:
        """Render the leaderboard panel centered on the given surface."""
        self._ensure_fonts()
        SC = SceneColors

        entries = self.fetch_entries()
        panel_w = self.PANEL_W
        panel_h = self.PANEL_H
        panel_x = (screen_w - panel_w) // 2
        panel_y = (screen_h - panel_h) // 2

        draw_chamfered_panel(
            surface,
            panel_x,
            panel_y,
            panel_w,
            panel_h,
            SC.BG_PANEL_LIGHT,
            SC.GOLD_PRIMARY,
            SC.GOLD_GLOW,
            self.CHAMFER,
        )

        title = self._title_font.render(t("leaderboard.title"), True, SC.GOLD_PRIMARY)
        surface.blit(title, title.get_rect(center=(screen_w // 2, panel_y + 50)))

        separator_y = panel_y + 96
        pygame.draw.line(
            surface,
            SC.BORDER_DIM,
            (panel_x + 30, separator_y),
            (panel_x + panel_w - 30, separator_y),
            1,
        )

        if not entries:
            empty = self._empty_font.render(t("leaderboard.empty"), True, SC.TEXT_DIM)
            surface.blit(empty, empty.get_rect(center=(screen_w // 2, panel_y + panel_h // 2)))
        else:
            self._render_rows(surface, entries, panel_x, separator_y + self.HEADER_GAP, panel_w)

        footer_y = panel_y + panel_h - 30
        footer = self._empty_font.render(self._footer_text(), True, SC.TEXT_DIM)
        surface.blit(footer, footer.get_rect(center=(screen_w // 2, footer_y)))

    def _render_rows(
        self,
        surface: pygame.Surface,
        entries: list[dict],
        panel_x: int,
        start_y: int,
        panel_w: int,
    ) -> None:
        SC = SceneColors
        for index, entry in enumerate(entries[:LEADERBOARD_CAP]):
            rank = index + 1
            row_y = start_y + index * self.ROW_H
            rank_color = self._rank_color(rank)

            rank_surf = self._row_font.render(f"#{rank:02d}", True, rank_color)
            rank_x = panel_x + self.ROW_INDENT
            surface.blit(rank_surf, rank_surf.get_rect(midleft=(rank_x, row_y + self.ROW_H // 2)))

            name = str(entry.get("player_name", ""))
            name_surf = self._row_font.render(name, True, SC.TEXT_PRIMARY)
            name_x = panel_x + self.ROW_INDENT + self.RANK_COL_W
            surface.blit(name_surf, name_surf.get_rect(midleft=(name_x, row_y + self.ROW_H // 2)))

            score = int(entry.get("score", 0))
            score_surf = self._row_font.render(f"{score:>8}", True, SC.GOLD_PRIMARY)
            score_x = panel_x + panel_w - self.ROW_INDENT - self.SCORE_COL_W
            surface.blit(score_surf, score_surf.get_rect(midleft=(score_x, row_y + self.ROW_H // 2)))

    @staticmethod
    def _rank_color(rank: int) -> tuple[int, int, int]:
        if rank == 1:
            return (255, 210, 90)
        if rank == 2:
            return (200, 215, 235)
        if rank == 3:
            return (210, 150, 100)
        return SceneColors.TEXT_DIM
