from types import SimpleNamespace
from unittest.mock import MagicMock

import pygame

from airwar.entities.player import Player
from airwar.game.homecoming import HomecomingDetector, HomecomingPhase, HomecomingSequence
from airwar.game.managers.game_controller import GameController
from airwar.game.scene_director import SceneDirector
from airwar.input.input_handler import MockInputHandler
from airwar.scenes.game_scene import GameScene
from airwar.ui.homecoming_ui import HomecomingUI


class _PressedKeys:
    def __init__(self, pressed_key: int | None):
        self._pressed_key = pressed_key

    def __getitem__(self, key: int) -> bool:
        return key == self._pressed_key


def _make_player() -> Player:
    return Player(420, 760, MockInputHandler())


def test_homecoming_detector_requires_full_hold(monkeypatch) -> None:
    completed = []
    detector = HomecomingDetector(lambda: completed.append(True))
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: _PressedKeys(HomecomingDetector.B_KEY))

    detector.update(0.0)
    detector.update(HomecomingDetector.HOLD_DURATION * 0.5)

    assert detector.is_active() is True
    assert completed == []

    detector.update(HomecomingDetector.HOLD_DURATION * 0.5)

    assert completed == [True]
    assert detector.is_active() is False


def test_homecoming_detector_resets_when_disabled(monkeypatch) -> None:
    detector = HomecomingDetector(lambda: None)
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: _PressedKeys(HomecomingDetector.B_KEY))

    detector.update(HomecomingDetector.HOLD_DURATION * 0.4)
    detector.update(0.0, enabled=False)

    assert detector.get_progress() == 0.0
    assert detector.is_active() is False


def test_homecoming_sequence_runs_to_complete_and_locks_final_state() -> None:
    player = _make_player()
    completed = []
    sequence = HomecomingSequence(lambda: completed.append(True))

    assert sequence.start(player, 1920, 1080) is True
    assert sequence.phase == HomecomingPhase.FTL_ESCAPE

    for _ in range(
        HomecomingSequence.FTL_FRAMES
        + HomecomingSequence.BLACKOUT_FRAMES
        + HomecomingSequence.STATION_REVEAL_FRAMES
        + HomecomingSequence.APPROACH_FRAMES
        + HomecomingSequence.LANDING_FRAMES
        + HomecomingSequence.HANDOFF_FRAMES
        + 6
    ):
        sequence.update(player)

    assert sequence.is_complete() is True
    assert completed == [True]
    assert player.rect.centery < 1080


def test_homecoming_handoff_moves_player_into_base_entry() -> None:
    player = _make_player()
    sequence = HomecomingSequence()
    sequence.start(player, 1920, 1080)

    for _ in range(
        HomecomingSequence.FTL_FRAMES
        + HomecomingSequence.BLACKOUT_FRAMES
        + HomecomingSequence.STATION_REVEAL_FRAMES
        + HomecomingSequence.APPROACH_FRAMES
        + HomecomingSequence.LANDING_FRAMES
        + 1
    ):
        sequence.update(player)

    assert sequence.phase == HomecomingPhase.HANDOFF
    start_x, start_y = sequence.get_player_center()
    entry_x, entry_y = sequence.get_base_entry_center()

    for _ in range(HomecomingSequence.HANDOFF_FRAMES):
        sequence.update(player)

    final_x, final_y = sequence.get_player_center()
    assert final_x == entry_x
    assert abs(final_y - entry_y) < abs(start_y - entry_y)
    assert abs(final_x - entry_x) < 1.0
    assert abs(final_y - entry_y) < 1.0


def test_homecoming_scene_renders_asteroid_belt_and_space_station() -> None:
    pygame.font.init()
    surface = pygame.Surface((1920, 1080), pygame.SRCALPHA)
    ui = HomecomingUI(1920, 1080)
    player = _make_player()
    sequence = HomecomingSequence()
    sequence.start(player, 1920, 1080)

    ui._render_deep_space(surface, HomecomingPhase.APPROACH, 0.5)
    background_pixel = surface.get_at((1540, 507))
    empty_station_pixel = surface.get_at((960, 508))
    ui._render_asteroid_belt(surface, HomecomingPhase.APPROACH, 0.5)
    asteroid_pixels = [
        surface.get_at((x, y))
        for x in range(1528, 1553, 4)
        for y in range(495, 520, 4)
    ]
    ui._render_space_station(surface, HomecomingPhase.APPROACH, 0.5, sequence)
    station_hub_pixel = surface.get_at((960, 508))
    solar_array_pixel = surface.get_at((1288, 383))

    assert any(pixel != background_pixel for pixel in asteroid_pixels)
    assert station_hub_pixel != empty_station_pixel
    assert solar_array_pixel != background_pixel


def test_homecoming_ftl_exit_fades_to_black_before_blackout() -> None:
    surface = pygame.Surface((320, 240), pygame.SRCALPHA)
    surface.fill((240, 248, 255))
    ui = HomecomingUI(320, 240)

    ui._render_ftl_exit_transition(surface, 1.0)

    assert surface.get_at((160, 120))[:3] == (0, 0, 0)


def test_homecoming_blackout_bridge_previews_station_reveal() -> None:
    surface = pygame.Surface((320, 240), pygame.SRCALPHA)
    ui = HomecomingUI(320, 240)

    ui._render_blackout_bridge(surface, 0.88)

    center_pixel = surface.get_at((160, 132))
    ring_pixels = [surface.get_at((x, y)) for x in range(158, 163) for y in range(40, 45)]
    assert center_pixel[:3] != (0, 0, 0)
    assert any(pixel[:3] != (0, 0, 0) for pixel in ring_pixels)


def test_game_scene_homecoming_request_sets_safe_interface_state() -> None:
    scene = GameScene()
    scene.player = _make_player()
    scene.game_controller = GameController("medium", "pilot")
    scene.reward_selector.visible = False
    scene._mother_ship_integrator = SimpleNamespace(is_docked=lambda: False)
    scene._homecoming_sequence = HomecomingSequence()
    scene._homecoming_ui = SimpleNamespace(hide=MagicMock())
    scene._bullet_manager = SimpleNamespace(clear_enemy_bullets=MagicMock())
    scene.notification_manager = SimpleNamespace(show=MagicMock())

    scene._on_homecoming_requested()

    assert scene.is_homecoming_active() is True
    assert scene.player.controls_locked is True
    assert scene.game_controller.state.paused is True
    assert scene.game_controller.state.player_invincible is True
    assert scene.game_controller.state.silent_invincible is True
    scene._bullet_manager.clear_enemy_bullets.assert_called_once()


def test_game_scene_homecoming_complete_keeps_scene_locked() -> None:
    scene = GameScene()
    scene.player = _make_player()
    scene.game_controller = GameController("medium", "pilot")
    scene.reward_system = scene.game_controller.reward_system
    scene._homecoming_base_pending = True
    scene.game_controller.state.paused = True

    scene.resume()

    assert scene.is_homecoming_locked() is True
    assert scene.game_controller.state.paused is True
    assert scene.consume_pause_request() is False


def test_game_scene_homecoming_complete_opens_base_talent_console() -> None:
    scene = GameScene()
    scene.player = _make_player()
    scene.game_controller = GameController("medium", "pilot")
    scene.reward_system = scene.game_controller.reward_system
    scene.reward_system.buff_levels["Spread Shot"] = 1
    scene.reward_system.earned_buff_levels["Spread Shot"] = 1
    scene._base_talent_console = SimpleNamespace(update=MagicMock())
    scene.notification_manager = SimpleNamespace(show=MagicMock())

    scene._on_homecoming_complete()

    assert scene.is_homecoming_complete() is True
    assert scene._talent_balance_manager is not None
    assert scene.reward_system.locked_buffs == {"Laser"}
    scene.notification_manager.show.assert_called_with("基地接口待接入")


def test_game_scene_homecoming_request_is_blocked_by_unsafe_states() -> None:
    scene = GameScene()
    scene.player = _make_player()
    scene.game_controller = GameController("medium", "pilot")
    scene.reward_selector.visible = False
    scene._mother_ship_integrator = SimpleNamespace(is_docked=lambda: False)
    scene._homecoming_sequence = HomecomingSequence()
    scene._game_loop_manager = SimpleNamespace(is_entrance_playing=lambda: False)

    assert scene._can_request_homecoming() is True

    scene.reward_selector.visible = True
    assert scene._can_request_homecoming() is False
    scene.reward_selector.visible = False

    scene.game_controller.state.paused = True
    assert scene._can_request_homecoming() is False
    scene.game_controller.state.paused = False

    scene._mother_ship_integrator = SimpleNamespace(is_docked=lambda: True)
    assert scene._can_request_homecoming() is False
    scene._mother_ship_integrator = SimpleNamespace(is_docked=lambda: False)

    scene._game_loop_manager = SimpleNamespace(is_entrance_playing=lambda: True)
    assert scene._can_request_homecoming() is False


def test_scene_director_ignores_pause_during_homecoming() -> None:
    director = SceneDirector(SimpleNamespace(), MagicMock())
    scene = SimpleNamespace(is_homecoming_locked=lambda: True)
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)

    assert director._handle_pause_toggle([event], scene) == "none"
