"""Achievement notification — slide-in toast panel for newly unlocked achievements.

Renders a stack of toast cards (one per unlocked achievement) that slide
in from the right edge, dwell for a short hold, then slide out. The
notification self-activates on construction; the host scene drives
:py:meth:`update` and :py:meth:`render` once per frame.

Text comes from the i18n catalog via :func:`airwar.i18n.t`; missing
keys fall back to the key string itself (see :mod:`airwar.i18n`).
"""

from __future__ import annotations

import math

import pygame

from airwar.config.design_tokens import SceneColors
from airwar.i18n import t
from airwar.utils.fonts import get_cjk_font


class _Card:
    """Internal per-achievement slide-in card.

    Lifecycle: ENTERING -> HOLDING -> EXITING -> DONE. ``frame`` is the
    global notification frame counter incremented by
    :py:meth:`AchievementNotification.update`.
    """

    ENTER_FRAMES = 22  # ~0.37s @ 60fps
    HOLD_FRAMES = 150  # ~2.5s
    EXIT_FRAMES = 22
    TOTAL_FRAMES = ENTER_FRAMES + HOLD_FRAMES + EXIT_FRAMES

    CARD_WIDTH = 360
    CARD_HEIGHT = 72
    CARD_GAP = 10
    HORIZONTAL_MARGIN = 32
    TOP_FRACTION = 0.10

    ACCENT_BAR_WIDTH = 4
    BADGE_RADIUS = 14
    BADGE_OFFSET_X = 28
    TEXT_TITLE_X = 60
    TEXT_NAME_Y = 26
    TEXT_DESC_Y = 50

    def __init__(self, achievement_id: str, slot_index: int) -> None:
        self.achievement_id = achievement_id
        self.slot_index = slot_index
        self.start_frame = 0
        self._done = False

    def activate(self, start_frame: int) -> None:
        self.start_frame = start_frame
        self._done = False

    @property
    def is_done(self) -> bool:
        return self._done

    def tick(self, current_frame: int) -> None:
        age = current_frame - self.start_frame
        if age >= self.TOTAL_FRAMES:
            self._done = True

    def slide_offset(self, current_frame: int) -> int:
        """Return the horizontal offset in px from the resting right edge.

        Positive values push the card off-screen to the right during
        enter/exit transitions; ``0`` while holding.
        """
        age = current_frame - self.start_frame
        if age < 0:
            return self.CARD_WIDTH
        if age < self.ENTER_FRAMES:
            t = age / self.ENTER_FRAMES
            eased = 1.0 - (1.0 - t) ** 3
            return int(self.CARD_WIDTH * (1.0 - eased))
        if age < self.ENTER_FRAMES + self.HOLD_FRAMES:
            return 0
        if age < self.TOTAL_FRAMES:
            exit_age = age - self.ENTER_FRAMES - self.HOLD_FRAMES
            t = exit_age / self.EXIT_FRAMES
            eased = t**3
            return int(self.CARD_WIDTH * eased)
        return self.CARD_WIDTH

    def alpha(self, current_frame: int) -> int:
        age = current_frame - self.start_frame
        if age < 0:
            return 0
        if age < self.ENTER_FRAMES:
            return int(255 * (age / self.ENTER_FRAMES))
        if age < self.ENTER_FRAMES + self.HOLD_FRAMES:
            return 255
        if age < self.TOTAL_FRAMES:
            exit_age = age - self.ENTER_FRAMES - self.HOLD_FRAMES
            t = exit_age / self.EXIT_FRAMES
            return int(255 * (1.0 - t**3))
        return 0


class AchievementNotification:
    """Slide-in notification panel listing newly unlocked achievements.

    Drives an internal frame counter; callers wire it into the scene
    loop by invoking :py:meth:`update` and :py:meth:`render` once per
    frame. The panel self-disables when all cards have finished their
    enter/hold/exit cycle — ``is_active`` flips to ``False`` and
    :py:meth:`render` becomes a no-op.

    Args:
        unlocked_ids: List of achievement IDs unlocked on this pass.
            ``None`` and empty lists are both treated as "no notification".
    """

    STACK_FAN_OUT = 6  # vertical fan-out between stacked cards

    def __init__(self, unlocked_ids: list[str] | None = None) -> None:
        self._unlocked_ids: list[str] = list(unlocked_ids) if unlocked_ids else []
        self._cards: list[_Card] = []
        self._frame: int = 0
        for i, ach_id in enumerate(self._unlocked_ids):
            card = _Card(ach_id, slot_index=i)
            card.activate(0)
            self._cards.append(card)
        self._active = bool(self._cards)
        self._fonts_built = False
        self._title_font: pygame.font.Font | None = None
        self._name_font: pygame.font.Font | None = None
        self._desc_font: pygame.font.Font | None = None
        self._title_text: pygame.Surface | None = None

    # ---- public API ----------------------------------------------------

    @property
    def is_active(self) -> bool:
        """Return ``True`` while at least one card is still animating."""
        return self._active

    @property
    def unlocked_ids(self) -> list[str]:
        """Return the list of achievement IDs this notification is showing."""
        return list(self._unlocked_ids)

    def update(self, dt: float = 0.0) -> None:
        """Advance the internal frame counter and prune done cards.

        ``dt`` is accepted for forward-compat with delta-time scenes;
        the current implementation runs on a 60fps tick.
        """
        if not self._active:
            return
        self._frame += 1
        for card in self._cards:
            card.tick(self._frame)
        if all(card.is_done for card in self._cards):
            self._active = False

    def render(self, surface: pygame.Surface) -> None:
        """Draw all live cards onto ``surface``.

        No-op when :py:attr:`is_active` is ``False`` or no cards remain.
        """
        if not self._active or not self._cards:
            return
        self._ensure_fonts()
        for card in self._cards:
            if card.is_done:
                continue
            self._render_card(surface, card)

    # ---- internals -----------------------------------------------------

    def _ensure_fonts(self) -> None:
        if self._fonts_built:
            return
        pygame.font.init()
        self._title_font = get_cjk_font(20)
        self._name_font = get_cjk_font(22)
        self._desc_font = get_cjk_font(16)
        self._title_text = self._title_font.render(t("achievement.unlocked.title"), True, SceneColors.ACCENT_BRIGHT)
        self._fonts_built = True

    def _render_card(self, surface: pygame.Surface, card: _Card) -> None:
        screen_w, screen_h = surface.get_size()
        base_y = int(screen_h * _Card.TOP_FRACTION) + card.slot_index * (
            _Card.CARD_HEIGHT + _Card.CARD_GAP + self.STACK_FAN_OUT
        )
        offset_x = card.slide_offset(self._frame)
        alpha = card.alpha(self._frame)
        if alpha <= 0:
            return

        card_surf = pygame.Surface((_Card.CARD_WIDTH, _Card.CARD_HEIGHT), pygame.SRCALPHA)
        # Panel background
        pygame.draw.rect(
            card_surf,
            (*SceneColors.BG_PANEL, min(235, alpha)),
            card_surf.get_rect(),
            border_radius=6,
        )
        # Accent left bar
        pygame.draw.rect(
            card_surf,
            (*SceneColors.ACCENT_PRIMARY, alpha),
            (0, 0, _Card.ACCENT_BAR_WIDTH, _Card.CARD_HEIGHT),
        )
        # Border
        pygame.draw.rect(
            card_surf,
            (*SceneColors.BORDER_DIM, alpha),
            card_surf.get_rect(),
            width=1,
            border_radius=6,
        )
        # Badge circle (star burst simplified to a filled disc)
        pygame.draw.circle(
            card_surf,
            (*SceneColors.ACCENT_TEAL_BRIGHT, alpha),
            (_Card.BADGE_OFFSET_X, _Card.CARD_HEIGHT // 2),
            _Card.BADGE_RADIUS,
        )
        pygame.draw.circle(
            card_surf,
            (*SceneColors.BG_PRIMARY, alpha),
            (_Card.BADGE_OFFSET_X, _Card.CARD_HEIGHT // 2),
            _Card.BADGE_RADIUS - 4,
        )

        # Title ("ACHIEVEMENT UNLOCKED")
        if self._title_text is not None:
            card_surf.blit(self._title_text, (_Card.TEXT_TITLE_X, 6))

        # Name + description (per-achievement i18n lookup with key fallback)
        name_key = f"achievement.{card.achievement_id}.name"
        desc_key = f"achievement.{card.achievement_id}.desc"
        name_text = self._name_font.render(t(name_key), True, SceneColors.TEXT_BRIGHT)
        desc_text = self._desc_font.render(t(desc_key), True, SceneColors.TEXT_DIM)
        # Apply per-card alpha by re-rendering onto an alpha-modulated surface
        name_alpha = name_text.copy()
        name_alpha.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
        desc_alpha = desc_text.copy()
        desc_alpha.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
        card_surf.blit(name_alpha, (_Card.TEXT_TITLE_X, _Card.TEXT_NAME_Y))
        card_surf.blit(desc_alpha, (_Card.TEXT_TITLE_X, _Card.TEXT_DESC_Y))

        # Right-anchored blit; offset_x slides it off-screen.
        rest_x = screen_w - _Card.CARD_WIDTH - _Card.HORIZONTAL_MARGIN
        surface.blit(card_surf, (rest_x + offset_x, base_y))

        # Subtle accent glow during hold
        if _Card.ENTER_FRAMES <= (self._frame - card.start_frame) < _Card.ENTER_FRAMES + _Card.HOLD_FRAMES:
            pulse = 0.5 + 0.5 * math.sin(self._frame * 0.1)
            glow_alpha = int(40 * pulse)
            if glow_alpha > 4:
                glow_surf = pygame.Surface((_Card.CARD_WIDTH + 12, _Card.CARD_HEIGHT + 12), pygame.SRCALPHA)
                pygame.draw.rect(
                    glow_surf,
                    (*SceneColors.ACCENT_PRIMARY, glow_alpha),
                    glow_surf.get_rect(),
                    width=2,
                    border_radius=8,
                )
                surface.blit(glow_surf, (rest_x + offset_x - 6, base_y - 6))
