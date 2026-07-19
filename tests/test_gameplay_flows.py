"""P5 gameplay-flow regression tests (headless).

Covers the full input → state-machine chains that previously had no
automated coverage:

- Phase dash (①): Shift tap → dash → teleport + i-frames + cooldown.
- Homecoming (②): hold B → detector → HOMECOMING lock → return-to-base
  sequence → resupply → departure → protection released.
- Give-up (③): hold K → detector → instant-kill wiring, plus the
  InputCoordinator gating (paused / reward selector visible).

All tests drive the real components; only the outermost edges (pygame
key state, game controller, UI) are doubled.
"""

from types import SimpleNamespace

import pygame
import pytest

from airwar.entities.base import Vector2
from airwar.entities.player import Player
from airwar.game.constants import GAME_CONSTANTS, PlayerConstants
from airwar.game.give_up.give_up_detector import GiveUpDetector
from airwar.game.homecoming.homecoming_detector import HomecomingDetector
from airwar.game.homecoming.homecoming_sequence import HomecomingPhase, HomecomingSequence
from airwar.game.managers.input_coordinator import InputCoordinator
from airwar.game.systems.homecoming_coordinator import HomecomingCoordinator
from airwar.game.systems.lock_manager import LockLayer, LockManager
from airwar.scenes.game_scene_updater import GameSceneUpdater


class _FakeInputHandler:
    """Scriptable InputSourceProtocol for driving a real Player headlessly."""

    def __init__(self):
        self.direction = Vector2(0, 0)
        self.boost_held = False
        self._boost_just_pressed = False

    # -- scripting helpers --
    def set_direction(self, x, y):
        self.direction = Vector2(x, y)

    def tap_boost(self):
        """Arm a one-frame Shift press, consumed by the next update."""
        self._boost_just_pressed = True

    # -- protocol surface --
    def tick(self):
        pass

    def get_movement_direction(self):
        return self.direction

    def is_pause_pressed(self):
        return False

    def is_boost_pressed(self):
        return self.boost_held

    def is_boost_just_pressed(self):
        value = self._boost_just_pressed
        self._boost_just_pressed = False
        return value

    def is_precision_pressed(self):
        return False

    def is_precision_just_pressed(self):
        return False


def _make_player(x=500, y=500):
    return Player(x, y, _FakeInputHandler())


class TestPhaseDashFlow:
    def test_dash_blocked_until_talent_unlocked(self):
        player = _make_player()
        handler = player._input_handler
        handler.set_direction(1, 0)
        handler.tap_boost()
        energy_before = player.boost_current

        player.update()

        assert not player.phase_dash.is_dashing()
        assert player.boost_current == pytest.approx(energy_before)

    def test_tap_shift_dashes_with_cost_iframes_and_cooldown(self):
        player = _make_player()
        handler = player._input_handler
        player.activate_phase_dash()
        handler.set_direction(1, 0)
        energy_before = player.boost_current
        start_x = player.rect.x

        handler.tap_boost()
        player.update()  # dash starts on this frame

        assert player.phase_dash.is_dashing()
        assert player.boost_current == pytest.approx(energy_before - player.boost_max * Player.PHASE_DASH_COST_RATIO)
        assert player.is_phase_dash_invincible()  # WINDUP i-frames

        dash_frames = (
            Player.PHASE_DASH_WINDUP_FRAMES + Player.PHASE_DASH_ACTIVE_FRAMES + Player.PHASE_DASH_RECOVERY_FRAMES
        )
        mid_dash_invincible = False
        for frame in range(dash_frames - 1):
            player.update()
            mid_dash_invincible = mid_dash_invincible or player.is_phase_dash_invincible()

        assert mid_dash_invincible
        assert not player.phase_dash.is_dashing()
        assert not player.is_phase_dash_invincible()
        assert player.phase_dash.cooldown == Player.PHASE_DASH_COOLDOWN_FRAMES
        # 250px teleport in the movement direction (no clamp at x=500).
        assert player.rect.x == pytest.approx(start_x + Player.PHASE_DASH_DISTANCE, abs=1)

    def test_dash_blocked_by_low_energy(self):
        player = _make_player()
        player.activate_phase_dash()
        player.boost_current = 1.0  # below the 25% cost
        handler = player._input_handler
        handler.set_direction(1, 0)

        handler.tap_boost()
        player.update()

        assert not player.phase_dash.is_dashing()

    def test_dash_blocked_while_controls_locked(self):
        player = _make_player()
        player.activate_phase_dash()
        player.is_controls_locked = True
        handler = player._input_handler
        handler.set_direction(1, 0)

        handler.tap_boost()
        player.update()

        assert not player.phase_dash.is_dashing()


class TestGiveUpDetector:
    def test_hold_k_three_seconds_completes_once(self):
        completed = []
        held = {"k": False}
        detector = GiveUpDetector(lambda: completed.append(True), key_state_provider=lambda key: held["k"])

        held["k"] = True
        for _ in range(185):  # HOLD_DURATION is 3.0s; 180 frames at 60Hz + float margin
            detector.update(1 / 60)

        assert completed == [True]
        assert detector.get_progress() == pytest.approx(1.0)
        assert not detector.is_active()  # completed is not "in progress" anymore

    def test_release_before_threshold_resets_progress(self):
        completed = []
        held = {"k": False}
        detector = GiveUpDetector(lambda: completed.append(True), key_state_provider=lambda key: held["k"])

        held["k"] = True
        for _ in range(60):  # 1.0s of the 3.0s hold
            detector.update(1 / 60)
        assert 0 < detector.get_progress() < 1.0
        assert detector.is_active()

        held["k"] = False
        detector.update(1 / 60)

        assert detector.get_progress() == 0.0
        assert not detector.is_active()
        assert completed == []


class TestGiveUpCoordination:
    def _make_coordinator(self, *, playing=True, paused=False, reward_visible=False, held=None):
        held = held if held is not None else {"k": False}
        completed = []
        detector = GiveUpDetector(lambda: completed.append(True), key_state_provider=lambda key: held["k"])
        ui_calls = {"show": 0, "hide": 0, "progress": []}
        ui = SimpleNamespace(
            show=lambda: ui_calls.__setitem__("show", ui_calls["show"] + 1),
            hide=lambda: ui_calls.__setitem__("hide", ui_calls["hide"] + 1),
            update_progress=lambda p: ui_calls["progress"].append(p),
        )
        game_controller = SimpleNamespace(
            is_playing=lambda: playing,
            state=SimpleNamespace(is_paused=paused),
        )
        reward_selector = SimpleNamespace(visible=reward_visible, handle_input=lambda event: None)
        player = SimpleNamespace(fire=lambda: None, get_bullets=lambda: [], render=lambda surface: None)
        coordinator = InputCoordinator(player, game_controller, reward_selector, detector, ui)
        return coordinator, detector, completed, ui_calls, held

    def test_hold_k_triggers_completion_and_progress_ui(self):
        coordinator, detector, completed, ui_calls, held = self._make_coordinator()

        held["k"] = True
        for _ in range(185):
            coordinator.update_give_up(1 / 60)

        assert completed == [True]
        assert ui_calls["show"] >= 1
        assert ui_calls["progress"], "UI never received progress updates"
        assert ui_calls["progress"][-1] == pytest.approx(1.0)

    def test_paused_game_blocks_and_resets_detection(self):
        coordinator, detector, completed, ui_calls, held = self._make_coordinator(paused=True)

        held["k"] = True
        for _ in range(185):
            coordinator.update_give_up(1 / 60)

        assert completed == []
        assert detector.get_progress() == 0.0
        assert ui_calls["show"] == 0

    def test_visible_reward_selector_blocks_detection(self):
        coordinator, detector, completed, ui_calls, held = self._make_coordinator(reward_visible=True)

        held["k"] = True
        for _ in range(185):
            coordinator.update_give_up(1 / 60)

        assert completed == []
        assert detector.get_progress() == 0.0

    def test_completion_kills_player_through_standard_hit_path(self):
        """Wiring: give-up completion routes an instant-kill through the
        game controller, so the run ends via the normal death flow."""
        hits = []
        player = object()
        game_controller = SimpleNamespace(on_player_hit=lambda damage, target: hits.append((damage, target)))
        updater = GameSceneUpdater(SimpleNamespace(game_controller=game_controller, player=player))

        updater._on_give_up_complete()

        assert hits == [(GAME_CONSTANTS.DAMAGE.INSTANT_KILL, player)]


class TestHomecomingDetector:
    def test_hold_b_2_4_seconds_completes_once(self):
        completed = []
        held = {"b": False}
        detector = HomecomingDetector(lambda: completed.append(True), key_state_provider=lambda key: held["b"])

        held["b"] = True
        for _ in range(150):  # HOLD_DURATION is 2.4s; 144 frames at 60Hz + margin
            detector.update(1 / 60)

        assert completed == [True]

    def test_release_before_threshold_resets(self):
        completed = []
        held = {"b": False}
        detector = HomecomingDetector(lambda: completed.append(True), key_state_provider=lambda key: held["b"])

        held["b"] = True
        for _ in range(60):
            detector.update(1 / 60)
        assert 0 < detector.get_progress() < 1.0

        held["b"] = False
        detector.update(1 / 60)

        assert detector.get_progress() == 0.0
        assert completed == []

    def test_disabled_detector_stays_reset(self):
        completed = []
        held = {"b": True}
        detector = HomecomingDetector(lambda: completed.append(True), key_state_provider=lambda key: held["b"])

        for _ in range(150):
            detector.update(1 / 60, enabled=False)

        assert detector.get_progress() == 0.0
        assert completed == []


class TestHomecomingSequence:
    def _fake_player(self):
        return SimpleNamespace(rect=pygame.Rect(100, 100, 40, 30))

    def test_full_return_sequence_lands_player_at_base(self):
        completed = []
        player = self._fake_player()
        sequence = HomecomingSequence(lambda: completed.append(True))

        assert sequence.start(player, 1920, 1080) is True
        assert sequence.is_active()

        for _ in range(1000):
            if sequence.is_complete():
                break
            sequence.update(player)

        assert sequence.is_complete()
        assert completed == [True]
        # HANDOFF eases the player into the base-entry point (960, 507.6).
        assert sequence.get_player_center() == (960.0, pytest.approx(1080 * 0.47))
        assert player.rect.centerx == 960

    def test_phase_progression_order(self):
        player = self._fake_player()
        sequence = HomecomingSequence()
        sequence.start(player, 1920, 1080)

        expected = [
            (sequence.FTL_FRAMES, HomecomingPhase.BLACKOUT),
            (sequence.BLACKOUT_FRAMES, HomecomingPhase.STATION_REVEAL),
            (sequence.STATION_REVEAL_FRAMES, HomecomingPhase.APPROACH),
            (sequence.APPROACH_FRAMES, HomecomingPhase.LANDING),
            (sequence.LANDING_FRAMES, HomecomingPhase.HANDOFF),
            (sequence.HANDOFF_FRAMES, HomecomingPhase.COMPLETE),
        ]
        assert sequence.phase == HomecomingPhase.FTL_ESCAPE
        for frames, next_phase in expected:
            for _ in range(frames):
                sequence.update(player)
            assert sequence.phase == next_phase

    def test_start_while_active_is_rejected(self):
        player = self._fake_player()
        sequence = HomecomingSequence()
        assert sequence.start(player, 1920, 1080) is True
        assert sequence.start(player, 1920, 1080) is False


class TestHomecomingFlow:
    """End-to-end coordinator chain with the real detector, sequence and
    LockManager; only controller / UI / notification edges are doubled."""

    def _setup(self):
        state = SimpleNamespace(
            is_paused=False,
            is_player_invincible=False,
            invincibility_timer=0,
            is_silent_invincible=False,
            requisition_points=10_000,
        )
        entrances = []
        game_controller = SimpleNamespace(
            is_playing=lambda: True,
            state=state,
            start_entrance_animation=lambda: entrances.append(True),
        )
        player = _make_player()
        lock_manager = LockManager(state, player)

        wiring = {}
        detector = HomecomingDetector(
            lambda: wiring["coordinator"].on_requested(game_controller, player, lock_manager, None, None),
            key_state_provider=lambda key: wiring["held"]["b"],
        )
        sequence = HomecomingSequence(
            lambda: wiring["coordinator"].on_complete(game_controller, player, lock_manager, None, None)
        )
        coordinator = HomecomingCoordinator(detector, sequence, None, None)
        wiring.update({"coordinator": coordinator, "held": {"b": False}})
        return wiring, coordinator, detector, sequence, game_controller, player, lock_manager, state, entrances

    @staticmethod
    def _tick(coordinator, game_controller, player, lock_manager, frames):
        for _ in range(frames):
            coordinator.update(game_controller, player, lock_manager, None, None, None, None, 1 / 60)

    def test_hold_b_return_resupply_depart_full_chain(self):
        wiring, coordinator, detector, sequence, gc, player, lock_manager, state, entrances = self._setup()

        # 1. Hold B for 2.4s → sequence starts and HOMECOMING protection engages.
        wiring["held"]["b"] = True
        self._tick(coordinator, gc, player, lock_manager, 150)

        assert sequence.is_active()
        assert lock_manager.is_locked(LockLayer.HOMECOMING)
        assert state.is_player_invincible is True
        assert state.is_paused is True
        assert player.is_controls_locked is True

        # 2. Release B; the sequence runs to completion → base handoff.
        wiring["held"]["b"] = False
        self._tick(coordinator, gc, player, lock_manager, 500)

        assert sequence.is_complete()
        assert coordinator.is_base_pending()

        # 3. Resupply at base: health + boost refilled, RP deducted.
        player.health = 10
        player.boost_current = 0
        rp_before = state.requisition_points
        coordinator.resupply_at_base(gc, player, None)

        assert player.health == player.max_health
        assert player.boost_current == player.boost_max
        assert state.requisition_points == rp_before - (
            GAME_CONSTANTS.REQUISITION.REPAIR_COST + GAME_CONSTANTS.REQUISITION.RECHARGE_COST
        )

        # 4. Leave base → departure sequence → protection released, respawned.
        coordinator.leave_base(gc, player, lock_manager, None, None, None)
        self._tick(coordinator, gc, player, lock_manager, 300)

        assert not coordinator.is_base_pending()
        assert not lock_manager.is_locked(LockLayer.HOMECOMING)
        assert state.is_paused is False
        assert player.is_controls_locked is False
        assert entrances == [True]
        assert player.rect.y == PlayerConstants.INITIAL_Y
