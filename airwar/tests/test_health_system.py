"""Tests for HealthSystem — regen timers, buff regen, difficulty switching."""

from unittest.mock import MagicMock

import pytest

from airwar.game.systems.health_system import HealthSystem

# Health regen timing + difficulty switching — pure logic, smoke subset.
pytestmark = pytest.mark.smoke


@pytest.fixture
def player():
    p = MagicMock()
    p.health = 50
    p.max_health = 100
    return p


@pytest.fixture
def hs():
    return HealthSystem("medium")


# --- normal regen ---


class TestNormalRegen:
    def test_no_regen_before_delay(self, hs, player):
        # medium: delay=240, interval=60, rate=2
        for _ in range(239):
            hs.update(player, has_regen_buff=False)
        assert player.health == 50  # unchanged

    def test_regen_activates_after_delay(self, hs, player):
        # tick 240 times to pass delay, then 60 more to hit interval
        for _ in range(240 + 60):
            hs.update(player, has_regen_buff=False)
        assert player.health == 52  # +2

    def test_regen_caps_at_max(self, hs, player):
        player.health = 99
        # pass delay + one interval
        for _ in range(240 + 60):
            hs.update(player, has_regen_buff=False)
        assert player.health == 100  # capped at max

    def test_no_regen_when_dead(self, hs, player):
        player.health = 0
        for _ in range(400):
            hs.update(player, has_regen_buff=False)
        assert player.health == 0


# --- buff regen ---


class TestBuffRegen:
    def test_buff_regen_heals(self, hs, player):
        # buff regen: threshold=60, rate=2
        for _ in range(60):
            hs.update(player, has_regen_buff=True)
        assert player.health == 52

    def test_buff_regen_resets_timer(self, hs, player):
        for _ in range(120):
            hs.update(player, has_regen_buff=True)
        assert player.health == 54  # 2 ticks of +2


# --- difficulty switching ---


class TestDifficultySwitch:
    def test_set_difficulty_resets(self, hs, player):
        hs._regen_timer = 100
        hs._regen_active = True
        hs.set_difficulty("easy")
        assert hs._regen_timer == 0
        assert hs._regen_active is False

    def test_easy_faster_regen(self, player):
        hs = HealthSystem("easy")
        # easy: delay=180, interval=45, rate=3
        for _ in range(180 + 45):
            hs.update(player, has_regen_buff=False)
        assert player.health == 53  # +3


# --- reset ---


class TestReset:
    def test_reset_clears_state(self, hs):
        hs._regen_timer = 500
        hs._regen_active = True
        hs._regen_interval_timer = 30
        hs.reset()
        assert hs._regen_timer == 0
        assert hs._regen_active is False
        assert hs._regen_interval_timer == 0
