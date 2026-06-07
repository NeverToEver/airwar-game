"""UI rendering for the tutorial scene.

All instructional and HUD-style text/panels live here: the stage
overlay (badge, title, objective, instructions, counter, hold bar),
the bottom status bar (boost gauge, health battery, score, kills),
the summary screen, the stage title card, the skip button, and a
few stage-specific text overlays (escape countdown, homecoming
depart transition, base talent console).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from airwar.config import TUTORIAL_STAGES
from airwar.config.design_tokens import SceneColors
from airwar.i18n import t
from airwar.ui.chamfered_panel import draw_chamfered_panel
from airwar.ui.scene_rendering_utils import fit_text_to_width, wrap_text

if TYPE_CHECKING:
    from airwar.scenes.tutorial_scene import TutorialScene


class UIRenderer:
    """Draw all text panels, buttons, and HUD bars for the tutorial scene.

    Pure presentation — every value is read off the scene and a
    ``pygame.Surface`` is the only thing that is mutated.
    """

    def __init__(self, scene: TutorialScene) -> None:
        self._scene = scene

    # -- Stage overlay (top instructional panel) -------------------------

    def render_stage_overlay(self, surface: pygame.Surface) -> None:
        """Top HUD panel: stage badge, title, objective, instructions, counter."""
        s = self._scene
        sw, sh = surface.get_width(), surface.get_height()
        skip_reserved_w = 210 if sw >= 760 else 0
        panel_w = min(sw - 48 - skip_reserved_w, 1040)
        panel_w = max(380, panel_w)
        x = 24 if skip_reserved_w else (sw - panel_w) // 2
        y = 20
        badge_size = 62
        right_badge_w = 154
        content_left = x + 96
        content_right = x + panel_w - right_badge_w - 26
        max_text_w = max(230, content_right - content_left)

        stage_instructions = self._current_stage_instructions()
        instruction_lines: list[str] = []
        for line in stage_instructions:
            instruction_lines.extend(wrap_text(line, s._small_font, max_text_w, max_lines=2))
        instruction_lines = instruction_lines[:4]
        panel_h = min(sh - 156, 120 + len(instruction_lines) * 24)
        panel_h = max(184, panel_h)

        transition_pulse = 1.0 if s._stage_card_timer > s.STAGE_CARD_FADE_FRAMES else 0.0
        border_alpha = 150 + int(55 * math.sin(s._animation_time * 0.08))
        glow_alpha = 42 + int(48 * transition_pulse)
        draw_chamfered_panel(
            surface,
            x - 3,
            y - 3,
            panel_w + 6,
            panel_h + 6,
            SceneColors.BG_PANEL,
            (*SceneColors.ACCENT_TEAL_BRIGHT, min(235, border_alpha + int(40 * transition_pulse))),
            (*SceneColors.ACCENT_TEAL_BRIGHT, glow_alpha),
            14,
        )
        draw_chamfered_panel(
            surface,
            x,
            y,
            panel_w,
            panel_h,
            SceneColors.BG_PANEL_LIGHT,
            (*SceneColors.BORDER_DIM, 210),
            None,
            12,
        )

        panel_tint = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_tint.fill((0, 0, 0, 28))
        line_color = (*SceneColors.ACCENT_TEAL_BRIGHT, 80)
        pygame.draw.line(panel_tint, line_color, (24, panel_h - 36), (panel_w - 24, panel_h - 36), 1)
        surface.blit(panel_tint, (x, y))

        badge_rect = pygame.Rect(0, 0, badge_size, badge_size)
        badge_rect.center = (x + 42, y + 48)
        badge_layer = pygame.Surface((badge_size + 14, badge_size + 14), pygame.SRCALPHA)
        pygame.draw.circle(
            badge_layer,
            (*SceneColors.ACCENT_TEAL_BRIGHT, 34 + int(24 * math.sin(s._animation_time * 0.07))),
            (badge_layer.get_width() // 2, badge_layer.get_height() // 2),
            badge_size // 2 + 6,
        )
        pygame.draw.circle(
            badge_layer,
            (*SceneColors.BG_PANEL, 240),
            (badge_layer.get_width() // 2, badge_layer.get_height() // 2),
            badge_size // 2,
        )
        pygame.draw.circle(
            badge_layer,
            SceneColors.ACCENT_TEAL_BRIGHT,
            (badge_layer.get_width() // 2, badge_layer.get_height() // 2),
            badge_size // 2,
            2,
        )
        surface.blit(badge_layer, badge_layer.get_rect(center=badge_rect.center))

        badge_top = s._tiny_font.render(t("tutorial.badge_stage"), True, SceneColors.TEXT_DIM)
        badge_num = s._body_font.render(str(s._stage_index + 1), True, SceneColors.TEXT_BRIGHT)
        surface.blit(badge_top, badge_top.get_rect(center=(badge_rect.centerx, badge_rect.centery - 12)))
        surface.blit(badge_num, badge_num.get_rect(center=(badge_rect.centerx, badge_rect.centery + 12)))

        title = s._heading_font.render(s._stage.title, True, SceneColors.ACCENT_TEAL_BRIGHT)
        surface.blit(title, title.get_rect(midleft=(content_left, y + 32)))

        objective = f"{t('tutorial.objective_prefix')}{s._stage.objective}"
        obj_surf = fit_text_to_width(s._small_font, objective, SceneColors.ACCENT_PRIMARY, max_text_w)
        surface.blit(obj_surf, obj_surf.get_rect(midleft=(content_left, y + 66)))

        line_y = y + 92
        for wrapped in instruction_lines:
            text = s._small_font.render(wrapped, True, SceneColors.TEXT_PRIMARY)
            surface.blit(text, (content_left, line_y))
            line_y += 24

        counter_rect = pygame.Rect(x + panel_w - right_badge_w - 20, y + 28, right_badge_w, 48)
        draw_chamfered_panel(
            surface,
            counter_rect.x,
            counter_rect.y,
            counter_rect.width,
            counter_rect.height,
            SceneColors.BG_PANEL,
            (*SceneColors.ACCENT_PRIMARY, 220),
            (*SceneColors.ACCENT_TEAL_BRIGHT, 38),
            8,
        )
        counter_label = s._tiny_font.render(t("tutorial.badge_progress"), True, SceneColors.TEXT_DIM)
        counter = self._objective_counter_text()
        counter_surf = fit_text_to_width(s._body_font, counter, SceneColors.TEXT_BRIGHT, counter_rect.width - 20)
        surface.blit(counter_label, counter_label.get_rect(midtop=(counter_rect.centerx, counter_rect.y + 5)))
        surface.blit(counter_surf, counter_surf.get_rect(midbottom=(counter_rect.centerx, counter_rect.bottom - 4)))

        hold_ratio = self._stage_hold_ratio()
        if hold_ratio is not None:
            bar = pygame.Rect(x + 96, y + panel_h - 24, panel_w - 192, 10)
            self._draw_bar(surface, bar, hold_ratio, SceneColors.ACCENT_TEAL_BRIGHT)

    # -- Status bar (bottom HUD) -----------------------------------------

    def render_status_bar(self, surface: pygame.Surface) -> None:
        """Bottom HUD: boost gauge, health battery, score and kill counters."""
        s = self._scene
        sw, sh = surface.get_width(), surface.get_height()
        s._boost_gauge.render(
            surface,
            s._player_energy,
            s.ENERGY_MAX,
            s._boost_held(),
            {"dash_enabled": True, "dash_cooldown": 0},
        )
        self.render_health_battery(surface)

        panel_w = min(460, sw - 44)
        panel_h = 54
        panel = pygame.Rect((sw - panel_w) // 2, sh - panel_h - 24, panel_w, panel_h)
        draw_chamfered_panel(
            surface,
            panel.x - 3,
            panel.y - 3,
            panel.width + 6,
            panel.height + 6,
            SceneColors.BG_PANEL,
            (*SceneColors.BORDER_DIM, 190),
            (*SceneColors.ACCENT_TEAL_BRIGHT, 38),
            10,
        )
        draw_chamfered_panel(
            surface,
            panel.x,
            panel.y,
            panel.width,
            panel.height,
            SceneColors.BG_PANEL_LIGHT,
            (*SceneColors.ACCENT_PRIMARY, 190),
            None,
            8,
        )

        score_text = s._small_font.render(
            t("tutorial.status_score", score=s._score),
            True,
            SceneColors.TEXT_PRIMARY,
        )
        kills_text = s._small_font.render(
            t("tutorial.status_kills", kills=s._kills),
            True,
            SceneColors.ACCENT_PRIMARY,
        )
        metric_gap = 58
        total_w = score_text.get_width() + metric_gap + kills_text.get_width()
        start_x = panel.centerx - total_w // 2
        surface.blit(score_text, score_text.get_rect(midleft=(start_x, panel.centery)))
        kills_x = start_x + score_text.get_width() + metric_gap
        surface.blit(kills_text, kills_text.get_rect(midleft=(kills_x, panel.centery)))

    def render_health_battery(self, surface: pygame.Surface) -> None:
        """Left-side discrete battery indicator with subtle border."""
        s = self._scene
        battery_x = 24
        battery_y = max(136, surface.get_height() - s._battery_indicator._h - 214)
        s._battery_indicator.set_health(s._player_health, s._player_max_health)
        s._battery_indicator.render(surface, battery_x, battery_y)
        border = pygame.Rect(
            battery_x,
            battery_y,
            s._battery_indicator._w,
            s._battery_indicator._h,
        )
        pygame.draw.rect(surface, (*SceneColors.BORDER_DIM, 140), border, 1, border_radius=4)

    # -- Summary / title card / skip button ------------------------------

    def render_summary(self, surface: pygame.Surface) -> None:
        """Centred summary panel listing cleared and locked tutorial stages."""
        s = self._scene
        sw, sh = surface.get_width(), surface.get_height()
        panel_w = min(720, sw - 80)
        panel_h = min(560, sh - 90)
        panel = pygame.Rect((sw - panel_w) // 2, (sh - panel_h) // 2, panel_w, panel_h)
        draw_chamfered_panel(
            surface,
            panel.x,
            panel.y,
            panel.width,
            panel.height,
            SceneColors.BG_PANEL_LIGHT,
            SceneColors.ACCENT_PRIMARY,
            SceneColors.GOLD_GLOW,
            12,
        )

        title = s._title_font.render(t("tutorial.summary_title"), True, SceneColors.ACCENT_TEAL_BRIGHT)
        surface.blit(title, title.get_rect(center=(panel.centerx, panel.y + 54)))

        summary = s._body_font.render(
            t("tutorial.summary_progress", cleared=len(s._cleared_stage_ids), total=len(TUTORIAL_STAGES)),
            True,
            SceneColors.TEXT_PRIMARY,
        )
        surface.blit(summary, summary.get_rect(center=(panel.centerx, panel.y + 98)))

        y = panel.y + 142
        for index, stage in enumerate(TUTORIAL_STAGES, start=1):
            mark_color = SceneColors.ACCENT_TEAL_BRIGHT if stage.id in s._cleared_stage_ids else SceneColors.TEXT_DIM
            label = f"{index}. {stage.title}"
            text = s._small_font.render(label, True, mark_color)
            surface.blit(text, (panel.x + 72, y))
            y += 36

        wrap_y = y + 10
        tip_text = t("tutorial.summary_tip")
        for line in wrap_text(tip_text, s._small_font, panel.width - 112, max_lines=3):
            surface.blit(s._small_font.render(line, True, SceneColors.TEXT_DIM), (panel.x + 56, wrap_y))
            wrap_y += 26

        btn = pygame.Rect(panel.centerx - 120, panel.bottom - 74, 240, 48)
        s.register_button("return_menu", btn)
        hover = s.is_button_hovered("return_menu")
        draw_chamfered_panel(
            surface,
            btn.x,
            btn.y,
            btn.width,
            btn.height,
            SceneColors.ACCENT_TEAL if hover else SceneColors.ACCENT_TEAL_DIM,
            SceneColors.ACCENT_PRIMARY,
            None,
            6,
        )
        btn_text = s._body_font.render(t("tutorial.summary_return_menu"), True, SceneColors.TEXT_BRIGHT)
        surface.blit(btn_text, btn_text.get_rect(center=btn.center))

    def render_stage_title_card(self, surface: pygame.Surface) -> None:
        """Sliding intro card that appears at the start of each stage."""
        s = self._scene
        if s._stage_card_timer <= 0 or s._is_summary_stage():
            return

        total = s.STAGE_CARD_SLIDE_FRAMES + s.STAGE_CARD_HOLD_FRAMES + s.STAGE_CARD_FADE_FRAMES
        elapsed = total - s._stage_card_timer
        sw = surface.get_width()
        card_w = min(620, sw - 80)
        card_h = 116
        target_y = 106

        if elapsed < s.STAGE_CARD_SLIDE_FRAMES:
            t = elapsed / max(1, s.STAGE_CARD_SLIDE_FRAMES)
            eased = 1 - (1 - t) * (1 - t)
            y = int(-card_h + eased * (target_y + card_h))
            alpha = int(255 * t)
        else:
            y = target_y
            alpha = 255

        fade_start = s.STAGE_CARD_SLIDE_FRAMES + s.STAGE_CARD_HOLD_FRAMES
        if elapsed > fade_start:
            t = (elapsed - fade_start) / max(1, s.STAGE_CARD_FADE_FRAMES)
            alpha = int(255 * max(0.0, 1.0 - t))

        x = (sw - card_w) // 2
        card = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        pulse = 0.5 + 0.5 * math.sin(s._animation_time * 0.1)
        draw_chamfered_panel(
            card,
            4,
            4,
            card_w - 8,
            card_h - 8,
            SceneColors.BG_PANEL_LIGHT,
            (*SceneColors.ACCENT_TEAL_BRIGHT, 235),
            (*SceneColors.ACCENT_TEAL_BRIGHT, int(alpha * (0.16 + 0.10 * pulse))),
            14,
        )

        stage_label = t("tutorial.stage_label", index=s._stage_index + 1)
        stage_text = s._body_font.render(stage_label, True, SceneColors.ACCENT_PRIMARY)
        title_text = fit_text_to_width(s._heading_font, s._stage.title, SceneColors.TEXT_BRIGHT, card_w - 96)
        card.blit(stage_text, stage_text.get_rect(center=(card_w // 2, 34)))
        card.blit(title_text, title_text.get_rect(center=(card_w // 2, 76)))

        card.set_alpha(alpha)
        surface.blit(card, (x, y))

    def render_skip_button(self, surface: pygame.Surface) -> None:
        """Top-right 'skip tutorial' button (registers a hit-area)."""
        s = self._scene
        if not s.running:
            return
        sw = surface.get_width()
        if s._is_summary_stage():
            return
        rect = pygame.Rect(sw - 190, 24, 164, 42)
        s.register_button("skip_tutorial", rect)
        hover = s.is_button_hovered("skip_tutorial")
        fill = SceneColors.BG_PANEL_LIGHT if hover else SceneColors.BG_PANEL
        border = SceneColors.ACCENT_PRIMARY if hover else SceneColors.BORDER_DIM
        draw_chamfered_panel(surface, rect.x, rect.y, rect.width, rect.height, fill, border, None, 6)
        skip_label = t("tutorial.skip_button")
        text = s._small_font.render(skip_label, True, SceneColors.TEXT_PRIMARY if hover else SceneColors.TEXT_DIM)
        surface.blit(text, text.get_rect(center=rect.center))

    # -- Base console / depart transition / escape countdown -------------

    def render_base_talent_console(self, surface: pygame.Surface) -> None:
        """Delegate the base talent console to its widget when at home base."""
        s = self._scene
        if not (
            s._base_talent_console
            and s._talent_balance_manager
            and s._base_reward_system
            and s._base_player_status
            and s._base_game_controller
        ):
            return
        s._base_talent_console.render(
            surface,
            s._talent_balance_manager,
            s._base_reward_system,
            player=s._base_player_status,
            game_controller=s._base_game_controller,
            mothership_status=s._mothership_status_data(),
            requisition_points=s._base_game_controller.state.requisition_points,
            missions=s._tutorial_missions(),
        )

    def render_homecoming_depart_transition(self, surface: pygame.Surface) -> None:
        """Black overlay with centred 'depart' text during homecoming exit."""
        s = self._scene
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 138))
        surface.blit(overlay, (0, 0))
        text = s._heading_font.render(
            t("tutorial.homecoming_depart_text"),
            True,
            SceneColors.ACCENT_TEAL_BRIGHT,
        )
        surface.blit(text, text.get_rect(center=(surface.get_width() // 2, surface.get_height() // 2)))

    def render_escape_countdown(self, surface: pygame.Surface) -> None:
        """Big warning text counting down the boss-escape window."""
        s = self._scene
        seconds = max(0, math.ceil(s._escape_timer / 60))
        text = s._title_font.render(
            t("tutorial.boost_escape_label", seconds=seconds),
            True,
            SceneColors.WARNING_ACCENT,
        )
        surface.blit(text, text.get_rect(center=(surface.get_width() // 2, 250)))

    def render_boost_gate(self, surface: pygame.Surface) -> None:
        """Pulsing elliptical gate used as the dash training target."""
        s = self._scene
        sw, sh = surface.get_width(), surface.get_height()
        gate_rect = pygame.Rect(sw // 2 - 170, sh // 2 - 80, 340, 160)
        gate_layer = pygame.Surface(gate_rect.size, pygame.SRCALPHA)
        pulse = 70 + int(35 * math.sin(s._animation_time * 0.08))
        pygame.draw.ellipse(
            gate_layer,
            (*SceneColors.ACCENT_TEAL_BRIGHT, pulse),
            gate_layer.get_rect(),
            4,
        )
        pygame.draw.ellipse(
            gate_layer,
            (*SceneColors.ACCENT_PRIMARY, 45),
            gate_layer.get_rect().inflate(-70, -52),
            2,
        )
        surface.blit(gate_layer, gate_rect)
        if s._boost_feedback_timer > 0:
            text = s._heading_font.render(
                t("tutorial.boost_label"),
                True,
                SceneColors.ACCENT_TEAL_BRIGHT,
            )
            surface.blit(text, text.get_rect(center=(gate_rect.centerx, gate_rect.centery)))

    def render_mothership_components(self, surface: pygame.Surface) -> None:
        """Show the mothership sprite plus the docked-state ammo + warning UI."""
        s = self._scene
        if s._mothership:
            mothership_departing = (
                s._dock_sub_phase == "eject_player" and s._dock_undock_phase == "mothership"
            )
            if not mothership_departing:
                s._mothership.show()
            s._mothership.render(surface)
        if s._dock_sub_phase == "docked" and s._ammo_magazine:
            is_warning = s._mothership_ammo < s.WARNING_CELL_THRESHOLD
            s._ammo_magazine.render(
                surface,
                ammo_count=s._mothership_ammo,
                ammo_max=s.MOTHERSHIP_STARTING_AMMO,
                is_cooldown=False,
                is_docked=True,
                is_warning=is_warning,
                is_present=True,
            )
        if s._warning_banner:
            s._warning_banner.render(surface)

    # -- Helpers ---------------------------------------------------------

    def _draw_bar(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        ratio: float,
        fill_color: tuple[int, int, int],
    ) -> None:
        """Draw a rounded progress bar clamped to ``[0, 1]``."""
        ratio = max(0.0, min(1.0, ratio))
        pygame.draw.rect(surface, SceneColors.SEGMENT_EMPTY, rect, border_radius=3)
        fill = rect.copy()
        fill.width = int(rect.width * ratio)
        if fill.width > 0:
            pygame.draw.rect(surface, fill_color, fill, border_radius=3)
        pygame.draw.rect(surface, SceneColors.SEGMENT_BORDER, rect, 1, border_radius=3)

    def _current_stage_instructions(self) -> list[str]:
        """Return the localised instruction lines for the current stage/sub-phase."""
        s = self._scene
        if s._stage.id == "mothership_docking":
            if s._dock_sub_phase == "approach":
                return [t("tutorial.approach_text")]
            if s._dock_sub_phase == "entering":
                return [t("tutorial.entering_text")]
            if s._dock_sub_phase == "docked":
                return [t("tutorial.docked_text")]
            return [t("tutorial.eject_text")]

        if s._stage.id == "homecoming_base":
            if s._base_sub_phase == "combat":
                return [t("tutorial.homecoming_combat_text")]
            if s._base_sub_phase == "base":
                return [t("tutorial.homecoming_base_text")]
            return [t("tutorial.homecoming_depart_text")]

        return s._stage.instructions

    def _objective_counter_text(self) -> str:
        """Return the localised counter text shown in the right badge."""
        s = self._scene
        if s._stage.id == "mothership_docking" and s._dock_sub_phase == "approach":
            return t(
                "tutorial.objective.dock_percent",
                percent=int(s._hold_h_frames / s.DOCK_HOLD_FRAMES * 100),
            )
        if s._stage.id == "mothership_docking" and s._dock_sub_phase == "entering":
            return t("tutorial.objective.dock")
        if s._stage.id == "mothership_docking" and s._dock_sub_phase == "docked":
            return f"{s._mothership_ammo:.1f}"
        if s._stage.id == "mothership_docking" and s._dock_sub_phase == "eject_player":
            if s._dock_undock_phase == "player":
                return t("tutorial.objective.dock_eject")
            return t("tutorial.objective.dock_undock")
        if s._stage.id == "homecoming_base" and s._base_sub_phase == "combat":
            return t(
                "tutorial.objective.homecoming_percent",
                percent=int(s._hold_b_frames / s.HOME_HOLD_FRAMES * 100),
            )
        if s._stage.id == "homecoming_base" and s._base_sub_phase == "base":
            return t("tutorial.objective.base")
        if s._stage.id == "homecoming_base" and s._base_sub_phase == "depart":
            return t("tutorial.objective.depart")
        if s._stage.id == "boss_encounter" and s._boss is None and s._escape_timer > 0:
            seconds = max(0, math.ceil(s._escape_timer / 60))
            return t("tutorial.objective.escape", seconds=seconds)
        if s._stage_completed:
            return t("tutorial.objective.completed")
        return t(
            "tutorial.objective.progress",
            current=s._stage_progress,
            total=s._stage.objective_count,
        )

    def _stage_hold_ratio(self) -> float | None:
        """Return hold-progress ratio for the hold-key mini bar, if applicable."""
        s = self._scene
        if s._stage.id == "mothership_docking" and s._dock_sub_phase == "approach":
            return s._hold_h_frames / s.DOCK_HOLD_FRAMES
        if s._stage.id == "homecoming_base" and s._base_sub_phase == "combat":
            return s._hold_b_frames / s.HOME_HOLD_FRAMES
        return None
