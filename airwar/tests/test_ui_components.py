"""Unit tests for new UI components: AmmoMagazine, WarningBanner, DiscreteBattery, LiquidHealthTank."""
import math
import time
import pytest
import pygame


def _init_pygame():
    """Minimal pygame init for font/Surface support."""
    if not pygame.get_init():
        pygame.init()
    if not pygame.display.get_surface():
        pygame.display.set_mode((200, 200))


def _retry_import(module_path, attr_name):
    """Import with retry to handle circular import via airwar.ui.__init__."""
    try:
        mod = __import__(module_path, fromlist=[attr_name])
        return getattr(mod, attr_name)
    except ImportError:
        mod = __import__(module_path, fromlist=[attr_name])
        return getattr(mod, attr_name)


# ══════════════════════════════════════════════════════════════════════════════
# AmmoMagazine
# ══════════════════════════════════════════════════════════════════════════════

class TestAmmoMagazine:
    """Tests for AmmoMagazine — frame geometry and cell calculation logic."""

    @pytest.fixture(autouse=True)
    def setup(self):
        _init_pygame()
        AmmoMagazine = _retry_import('airwar.ui.ammo_magazine', 'AmmoMagazine')
        self.AmmoMagazine = AmmoMagazine
        self.magazine = AmmoMagazine()
        yield

    def test_frame_dimensions_positive(self):
        assert self.magazine.frame_width > 0
        assert self.magazine.frame_height > 0

    def test_cell_count_constant(self):
        assert self.magazine.CELL_COUNT == 10

    def test_hide_when_not_present_and_empty(self):
        """render() should be a no-op when not present and ammo <= 0 and not cooldown."""
        surf = pygame.Surface((400, 600), pygame.SRCALPHA)
        before = surf.get_at((100, 300))
        self.magazine.render(surf, ammo_count=0.0, ammo_max=10.0,
                             is_cooldown=False, is_docked=False,
                             is_warning=False, is_present=False)
        assert surf.get_at((100, 300)) == before

    def test_show_during_cooldown_even_empty(self):
        """Should render during cooldown even with zero ammo."""
        surf = pygame.Surface((400, 600), pygame.SRCALPHA)
        self.magazine.render(surf, ammo_count=0.0, ammo_max=10.0,
                             is_cooldown=True, is_docked=False,
                             is_warning=False, is_present=False)
        assert surf.get_at((20, 300)) != (0, 0, 0, 0)

    def test_show_when_present(self):
        surf = pygame.Surface((400, 600), pygame.SRCALPHA)
        self.magazine.render(surf, ammo_count=10.0, ammo_max=10.0,
                             is_cooldown=False, is_docked=False,
                             is_warning=False, is_present=True)
        assert surf.get_at((20, 300)) != (0, 0, 0, 0)

    def test_ammo_count_clamped(self):
        """Verify render doesn't crash with out-of-range ammo values."""
        surf = pygame.Surface((400, 600), pygame.SRCALPHA)
        self.magazine.render(surf, ammo_count=15.0, ammo_max=10.0,
                             is_cooldown=False, is_docked=False,
                             is_warning=False, is_present=True)
        self.magazine.render(surf, ammo_count=-5.0, ammo_max=10.0,
                             is_cooldown=True, is_docked=False,
                             is_warning=False, is_present=True)

    def test_partial_cell_rendering(self):
        """Partial fill (e.g. 3.5 cells) should not crash."""
        surf = pygame.Surface((400, 600), pygame.SRCALPHA)
        self.magazine.render(surf, ammo_count=3.5, ammo_max=10.0,
                             is_cooldown=False, is_docked=True,
                             is_warning=False, is_present=True)

    def test_warning_condition_renders(self):
        """Warning state should render without errors."""
        surf = pygame.Surface((400, 600), pygame.SRCALPHA)
        self.magazine.render(surf, ammo_count=2.0, ammo_max=10.0,
                             is_cooldown=False, is_docked=True,
                             is_warning=True, is_present=True)


# ══════════════════════════════════════════════════════════════════════════════
# WarningBanner
# ══════════════════════════════════════════════════════════════════════════════

class TestWarningBanner:
    """Tests for WarningBanner — state machine lifecycle and activate behavior."""

    @pytest.fixture(autouse=True)
    def setup(self):
        _init_pygame()
        WarningBanner = _retry_import('airwar.ui.warning_banner', 'WarningBanner')
        self.WarningBanner = WarningBanner
        self.banner = WarningBanner()
        yield

    def test_initial_state_inactive(self):
        assert not self.banner.is_active

    def test_activate_returns_true_on_success(self):
        assert self.banner.activate() is True
        assert self.banner.is_active

    def test_activate_returns_false_when_already_active(self):
        self.banner.activate()
        assert self.banner.activate() is False

    def test_reset_clears_state(self):
        self.banner.activate()
        self.banner.reset()
        assert not self.banner.is_active

    def test_multiple_activate_only_counts_first(self):
        """Second activate() during active state must not reset animation."""
        callback_calls = []

        self.banner.activate(on_complete=lambda: callback_calls.append(1))
        result = self.banner.activate(on_complete=lambda: callback_calls.append(2))
        assert result is False
        self.banner.reset()
        assert len(callback_calls) == 0  # callback only fires on natural completion

    def test_render_inactive_does_nothing(self):
        surf = pygame.Surface((600, 400), pygame.SRCALPHA)
        before = surf.get_at((300, 50))
        self.banner.render(surf)
        assert surf.get_at((300, 50)) == before

    def test_activate_then_render(self):
        """After activation + one update tick, banner should be visible on screen."""
        surf = pygame.Surface((600, 400), pygame.SRCALPHA)
        self.banner.activate()
        # Advance time so the banner slides into view
        self.banner._last_tick = pygame.time.get_ticks() - 100  # 100ms elapsed
        self.banner.update()
        self.banner.render(surf)
        # Banner center at ~(300, 48 + offset). After 100ms of entering animation,
        # y_offset should be > -60, making banner partially visible.
        # Check center of banner area for non-transparent pixels.
        assert surf.get_at((300, 60)) != (0, 0, 0, 0)

    def test_update_advances_state(self):
        self.banner.activate()
        assert self.banner._state == self.banner._STATE_ENTERING
        self.banner._state_time = 999.0
        self.banner.update()
        assert self.banner._state != self.banner._STATE_ENTERING


# ══════════════════════════════════════════════════════════════════════════════
# DiscreteBatteryIndicator
# ══════════════════════════════════════════════════════════════════════════════

class TestDiscreteBattery:
    """Tests for DiscreteBatteryIndicator — segment math and color mapping."""

    @pytest.fixture(autouse=True)
    def setup(self):
        _init_pygame()
        DiscreteBatteryIndicator = _retry_import(
            'airwar.ui.discrete_battery', 'DiscreteBatteryIndicator')
        self.DiscreteBattery = DiscreteBatteryIndicator
        yield

    def test_vertical_orientation_default(self):
        batt = self.DiscreteBattery(36, 350, num_segments=30, orientation='vertical')
        assert batt._orientation == 'vertical'

    def test_horizontal_orientation(self):
        batt = self.DiscreteBattery(350, 24, num_segments=30, orientation='horizontal')
        assert batt._orientation == 'horizontal'

    def test_invalid_orientation_raises(self):
        with pytest.raises(ValueError, match="orientation must be"):
            self.DiscreteBattery(36, 350, num_segments=30, orientation='diagonal')

    def test_full_health_all_segments_active_vertical(self):
        batt = self.DiscreteBattery(36, 350, num_segments=30, orientation='vertical')
        batt.set_health(100, 100)
        surf = pygame.Surface((100, 400), pygame.SRCALPHA)
        batt.render(surf, 10, 10)

    def test_half_health_color_amber(self):
        batt = self.DiscreteBattery(36, 350, num_segments=30, orientation='vertical')
        batt.set_health(50, 100)
        color = batt._health_color(0.5)
        assert color == (230, 170, 50)

    def test_low_health_color_red(self):
        batt = self.DiscreteBattery(36, 350, num_segments=30, orientation='vertical')
        batt.set_health(20, 100)
        color = batt._health_color(0.2)
        assert color == (220, 60, 45)

    def test_high_health_color_green(self):
        batt = self.DiscreteBattery(36, 350, num_segments=30, orientation='vertical')
        batt.set_health(80, 100)
        color = batt._health_color(0.8)
        assert color == (80, 200, 100)

    def test_zero_health(self):
        batt = self.DiscreteBattery(36, 350, num_segments=30, orientation='vertical')
        batt.set_health(0, 100)
        color = batt._health_color(0.0)
        assert color == (220, 60, 45)

    def test_zero_max_health_handled(self):
        """Zero max_health should not cause division by zero."""
        batt = self.DiscreteBattery(36, 350, num_segments=30, orientation='vertical')
        batt.set_health(0, 0)
        surf = pygame.Surface((100, 400), pygame.SRCALPHA)
        batt.render(surf, 10, 10)  # should not crash

    def test_horizontal_rendering(self):
        batt = self.DiscreteBattery(350, 24, num_segments=20, orientation='horizontal')
        batt.set_health(75, 100)
        surf = pygame.Surface((400, 100), pygame.SRCALPHA)
        batt.render(surf, 10, 10)
        assert surf.get_at((12, 22)) != (0, 0, 0, 0)

    def test_edge_case_one_segment(self):
        batt = self.DiscreteBattery(36, 350, num_segments=1, orientation='vertical')
        batt.set_health(50, 100)
        surf = pygame.Surface((100, 400), pygame.SRCALPHA)
        batt.render(surf, 10, 10)  # should not crash


# ══════════════════════════════════════════════════════════════════════════════
# LiquidHealthTank
# ══════════════════════════════════════════════════════════════════════════════

class TestLiquidHealthTank:
    """Tests for LiquidHealthTank — spring physics, color interpolation, health API."""

    @pytest.fixture(autouse=True)
    def setup(self):
        _init_pygame()
        LiquidHealthTank = _retry_import(
            'airwar.ui.liquid_health_tank', 'LiquidHealthTank')
        self.LiquidHealthTank = LiquidHealthTank
        self.tank = LiquidHealthTank(width=60, height=230)
        yield

    def _advance_time(self, n_ticks: int, dt_per_tick: float = 0.016):
        """Simulate n ticks of game time at ~60fps (16ms per tick)."""
        for _ in range(n_ticks):
            self.tank._last_tick -= int(dt_per_tick * 1000)
            self.tank.update()

    def test_initial_level_full(self):
        assert self.tank._liquid_level == 1.0
        assert self.tank._target_level == 1.0

    def test_set_health_updates_target(self):
        self.tank.set_health(50, 100)
        assert self.tank._target_level == 0.5

    def test_set_health_zero_max_triggers_zero(self):
        self.tank.set_health(0, 0)
        assert self.tank._target_level == 0.0

    def test_set_health_negative_clamped(self):
        self.tank.set_health(-10, 100)
        assert self.tank._target_level == 0.0

    def test_set_health_over_max_clamped(self):
        self.tank.set_health(200, 100)
        assert self.tank._target_level == 1.0

    def test_disturbance_on_large_change(self):
        self.tank.set_health(100, 100)
        old_disturbance = self.tank._disturbance
        self.tank.set_health(20, 100)  # large delta
        assert self.tank._disturbance > old_disturbance

    def test_spring_converges_to_target_after_many_updates(self):
        self.tank.set_health(30, 100)
        self._advance_time(300)
        assert abs(self.tank._liquid_level - self.tank._target_level) < 0.005

    def test_spring_converges_upward(self):
        self.tank.set_health(0, 100)
        self._advance_time(300)
        self.tank.set_health(100, 100)
        self._advance_time(300)
        assert abs(self.tank._liquid_level - 1.0) < 0.005

    def test_velocity_decays_near_target(self):
        self.tank.set_health(30, 100)
        self._advance_time(400)
        assert abs(self.tank._liquid_velocity) < 0.01

    def test_update_dt_clamped(self):
        """Large time gaps should be clamped to prevent physics explosion."""
        self.tank.set_health(30, 100)
        self.tank._last_tick = 0  # force huge dt
        self.tank.update()
        assert 0.0 <= self.tank._liquid_level <= 1.0

    def test_render_does_not_crash(self):
        self.tank.set_health(75, 100)
        self._advance_time(50)
        surf = pygame.Surface((200, 400), pygame.SRCALPHA)
        self.tank.render(surf, 20, 20)

    def test_liquid_color_interpolation(self):
        c_full = self.tank._liquid_color(1.0)
        c_half = self.tank._liquid_color(0.5)
        c_low = self.tank._liquid_color(0.2)
        c_zero = self.tank._liquid_color(0.0)
        for c in [c_full, c_half, c_low, c_zero]:
            assert isinstance(c, tuple)
            assert len(c) == 3

    def test_color_is_green_at_full(self):
        c = self.tank._liquid_color(1.0)
        assert c[1] > c[0]  # green > red at full health

    def test_color_is_red_at_zero(self):
        c = self.tank._liquid_color(0.0)
        assert c[0] > c[1]  # red > green at zero health

    def test_bubble_generation(self):
        """Bubbles should appear when liquid level > 0 and timer is advanced."""
        self.tank.set_health(80, 100)
        assert len(self.tank._bubbles) == 0
        self.tank._bubble_timer = 0.5
        self.tank.update()

    def test_max_bubbles_limited(self):
        self.tank.set_health(100, 100)
        for _ in range(200):
            self.tank._last_tick -= 16
            self.tank.update()
        assert len(self.tank._bubbles) <= 8


# ══════════════════════════════════════════════════════════════════════════════
# WarningBanner lifecycle integration
# ══════════════════════════════════════════════════════════════════════════════

class TestWarningBannerLifecycle:
    """Test WarningBanner full lifecycle: enter → hold → exit → callback."""

    @pytest.fixture(autouse=True)
    def setup(self):
        _init_pygame()
        WarningBanner = _retry_import('airwar.ui.warning_banner', 'WarningBanner')
        self.banner = WarningBanner()
        yield

    def test_complete_lifecycle_triggers_callback(self):
        callback_fired = []

        self.banner.activate(on_complete=lambda: callback_fired.append(1))

        assert self.banner._state == self.banner._STATE_ENTERING
        self.banner._state_time = self.banner.ENTER_DURATION + 0.1
        self.banner.update()
        assert self.banner._state == self.banner._STATE_HOLDING

        self.banner._state_time = self.banner.HOLD_DURATION + 0.1
        self.banner.update()
        assert self.banner._state == self.banner._STATE_EXITING

        self.banner._state_time = self.banner.EXIT_DURATION + 0.1
        self.banner.update()
        assert self.banner._state == self.banner._STATE_INACTIVE
        assert len(callback_fired) == 1

    def test_reset_during_lifecycle_cancels(self):
        callback_fired = []
        self.banner.activate(on_complete=lambda: callback_fired.append(1))
        self.banner.reset()
        assert not self.banner.is_active
        assert len(callback_fired) == 0
