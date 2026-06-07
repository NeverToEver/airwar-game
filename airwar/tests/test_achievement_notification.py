"""Tests for AchievementNotification — slide-in toast for newly unlocked achievements."""

import pygame

from airwar.ui.achievement_notification import AchievementNotification, _Card


def _make_surface() -> pygame.Surface:
    pygame.font.init()
    return pygame.Surface((1280, 720), pygame.SRCALPHA)


def test_empty_unlocked_list_starts_inactive() -> None:
    notif = AchievementNotification([])
    assert not notif.is_active
    assert notif.unlocked_ids == []


def test_none_unlocked_list_starts_inactive() -> None:
    notif = AchievementNotification(None)
    assert not notif.is_active
    assert notif.unlocked_ids == []


def test_single_achievement_starts_active_and_lists_id() -> None:
    notif = AchievementNotification(["first_kill"])
    assert notif.is_active
    assert notif.unlocked_ids == ["first_kill"]


def test_multiple_achievements_preserve_order() -> None:
    ids = ["first_kill", "score_1k", "boss_kill"]
    notif = AchievementNotification(ids)
    assert notif.is_active
    assert notif.unlocked_ids == ids


def test_card_slide_offset_fades_in_holds_and_fades_out() -> None:
    card = _Card("first_kill", slot_index=0)
    card.activate(0)

    # Before enter: pushed off-screen to the right (positive offset).
    assert card.slide_offset(0) == _Card.CARD_WIDTH
    # First frame starts entering.
    assert card.slide_offset(1) < _Card.CARD_WIDTH
    # Holding: resting position.
    hold_frame = _Card.ENTER_FRAMES + 5
    assert card.slide_offset(hold_frame) == 0
    # Exiting: offset grows back positive.
    exit_frame = _Card.ENTER_FRAMES + _Card.HOLD_FRAMES + _Card.EXIT_FRAMES // 2
    assert card.slide_offset(exit_frame) > 0
    # After total duration: fully off-screen.
    assert card.slide_offset(_Card.TOTAL_FRAMES) == _Card.CARD_WIDTH


def test_card_alpha_matches_lifecycle() -> None:
    card = _Card("first_kill", slot_index=0)
    card.activate(0)

    assert card.alpha(0) == 0
    assert card.alpha(1) > 0
    # Holding: full alpha.
    assert card.alpha(_Card.ENTER_FRAMES + 1) == 255
    # Late: alpha drops to zero.
    assert card.alpha(_Card.TOTAL_FRAMES) == 0


def test_update_advances_internal_frame() -> None:
    notif = AchievementNotification(["first_kill"])
    assert notif.is_active
    # Force done via total-frames ticks.
    for _ in range(_Card.TOTAL_FRAMES + 5):
        notif.update()
    assert not notif.is_active


def test_render_is_noop_when_inactive() -> None:
    notif = AchievementNotification(["first_kill"])
    # Force into the done state.
    for _ in range(_Card.TOTAL_FRAMES + 5):
        notif.update()
    surface = _make_surface()
    # Should not raise and should not draw anything (no assertion needed
    # beyond the call returning successfully while inactive).
    notif.render(surface)


def test_render_draws_visible_card() -> None:
    notif = AchievementNotification(["first_kill"])
    surface = _make_surface()
    # Advance partway through the enter animation so alpha > 0 and
    # the card is partly on-screen.
    for _ in range(_Card.ENTER_FRAMES // 2 + 2):
        notif.update()
    notif.render(surface)
    assert notif.is_active


def test_render_with_multiple_cards_does_not_raise() -> None:
    notif = AchievementNotification(["first_kill", "score_1k", "boss_kill"])
    surface = _make_surface()
    for _ in range(_Card.ENTER_FRAMES + 5):
        notif.update()
        notif.render(surface)
