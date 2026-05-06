from types import SimpleNamespace
from unittest.mock import MagicMock

import pygame

from airwar.entities.player import Player
from airwar.game.constants import GAME_CONSTANTS, PlayerConstants
from airwar.game.homecoming import HomecomingDetector, HomecomingPhase, HomecomingSequence
from airwar.game.managers.game_controller import GameController
from airwar.game.mother_ship.mother_ship_state import GameSaveData
from airwar.game.scene_director import SceneDirector
from airwar.game.systems.talent_balance_manager import TalentBalanceManager
from airwar.input.input_handler import MockInputHandler
from airwar.scenes.game_scene import GameScene
from airwar.ui.base_talent_console import BaseTalentConsoleAction
from airwar.ui.homecoming_ui import HomecomingUI


class _PressedKeys:
    def __init__(self, pressed_key: int | None):
        self._pressed_key = pressed_key

    def __getitem__(self, key: int) -> bool:
        return key == self._pressed_key


def _make_player() -> Player:
    return Player(420, 760, MockInputHandler())


def _capture_base_saves(monkeypatch) -> list[tuple[str | None, dict, bool]]:
    saved = []

    class RecordingPersistenceManager:
        def __init__(self, username=None):
            self.username = username

        def save_game(self, save_data):
            saved.append((self.username, save_data.talent_loadout, save_data.is_in_mothership))
            return True

    monkeypatch.setattr("airwar.scenes.game_scene.PersistenceManager", RecordingPersistenceManager)
    return saved


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


def test_homecoming_departure_runs_orbital_strike_then_complete() -> None:
    player = _make_player()
    completed = []
    strike = []
    sequence = HomecomingSequence()

    assert sequence.start_departure(
        player,
        1280,
        720,
        on_complete_callback=lambda: completed.append(True),
        on_orbital_strike_callback=lambda: strike.append(True),
    ) is True
    assert sequence.phase == HomecomingPhase.BASE_LAUNCH

    for _ in range(
        HomecomingSequence.BASE_LAUNCH_FRAMES
        + HomecomingSequence.RETURN_BLACKOUT_FRAMES
        + int(HomecomingSequence.ORBITAL_STRIKE_FRAMES * HomecomingSequence.ORBITAL_STRIKE_IMPACT_PROGRESS)
        + 1
    ):
        sequence.update(player)

    assert strike == [True]
    assert completed == []

    for _ in range(HomecomingSequence.ORBITAL_STRIKE_FRAMES):
        sequence.update(player)

    assert sequence.is_complete() is True
    assert completed == [True]


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


def test_homecoming_ftl_exit_transition_keeps_flash_muted() -> None:
    surface = pygame.Surface((320, 240), pygame.SRCALPHA)
    surface.fill((0, 0, 0))
    ui = HomecomingUI(320, 240)
    flash_peak_progress = 0.72 + 0.28 * 0.36

    ui._render_ftl_exit_transition(surface, flash_peak_progress)

    assert max(surface.get_at((5, 5))[:3]) <= HomecomingUI.FTL_EXIT_FLASH_ALPHA_MAX


def test_homecoming_blackout_bridge_previews_station_reveal() -> None:
    surface = pygame.Surface((320, 240), pygame.SRCALPHA)
    ui = HomecomingUI(320, 240)

    ui._render_blackout_bridge(surface, 0.88)

    center_pixel = surface.get_at((160, 132))
    ring_pixels = [surface.get_at((x, y)) for x in range(158, 163) for y in range(40, 45)]
    assert center_pixel[:3] != (0, 0, 0)
    assert any(pixel[:3] != (0, 0, 0) for pixel in ring_pixels)


def test_homecoming_launch_corridor_uses_slow_low_contrast_pulse(monkeypatch) -> None:
    pygame.font.init()
    ui = HomecomingUI(320, 240)
    player = _make_player()
    sequence = HomecomingSequence()
    sequence.start_departure(player, 320, 240)
    original_line = pygame.draw.line
    line_alphas = []

    def capture_line(surface, color, start_pos, end_pos, width=1):
        line_alphas.append(color[3])
        return original_line(surface, color, start_pos, end_pos, width)

    monkeypatch.setattr(pygame.draw, "line", capture_line)

    for frame in range(HomecomingSequence.BASE_LAUNCH_FRAMES + 1):
        surface = pygame.Surface((320, 240), pygame.SRCALPHA)
        progress = frame / HomecomingSequence.BASE_LAUNCH_FRAMES
        ui._render_launch_corridor(surface, sequence, progress)

    deltas = [current - previous for previous, current in zip(line_alphas, line_alphas[1:], strict=False)]
    sign_changes = 0
    previous_sign = 0
    for delta in deltas:
        if delta == 0:
            continue
        sign = 1 if delta > 0 else -1
        if previous_sign and sign != previous_sign:
            sign_changes += 1
        previous_sign = sign

    assert max(line_alphas) <= HomecomingUI.LAUNCH_CORRIDOR_LINE_ALPHA_BASE + HomecomingUI.LAUNCH_CORRIDOR_LINE_ALPHA_RANGE
    assert max(abs(delta) for delta in deltas) <= 3
    assert sign_changes <= 4


def test_homecoming_departure_renders_launch_and_orbital_strike_pixels() -> None:
    pygame.font.init()
    surface = pygame.Surface((320, 240), pygame.SRCALPHA)
    ui = HomecomingUI(320, 240)
    player = _make_player()
    sequence = HomecomingSequence()
    sequence.start_departure(player, 320, 240)

    for _ in range(12):
        sequence.update(player)
    ui.render_sequence(surface, sequence, player)

    launch_pixels = [
        surface.get_at((x, y))
        for x in range(150, 171, 5)
        for y in range(110, 210, 12)
    ]
    assert any(pixel[:3] != (2, 4, 10) for pixel in launch_pixels)

    for _ in range(HomecomingSequence.BASE_LAUNCH_FRAMES + HomecomingSequence.RETURN_BLACKOUT_FRAMES + 2):
        sequence.update(player)
    surface.fill((4, 8, 18))
    ui.render_sequence(surface, sequence, player)

    assert surface.get_at((160, 100))[:3] != (4, 8, 18)


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
    scene._mother_ship_integrator = None
    scene.notification_manager = SimpleNamespace(show=MagicMock())

    scene._on_homecoming_complete()

    assert scene.is_homecoming_complete() is True
    assert scene._talent_balance_manager is not None
    assert scene.reward_system.locked_buffs == {"Laser"}
    scene.notification_manager.show.assert_called_with("已进入基地整备")


def test_game_scene_leaving_base_starts_departure_sequence() -> None:
    scene = GameScene()
    scene.player = _make_player()
    scene.game_controller = GameController("medium", "pilot")
    scene._homecoming_base_pending = True
    scene._pause_requested = True
    scene.player.controls_locked = True
    scene.game_controller.state.paused = True
    scene.game_controller.state.player_invincible = True
    scene.game_controller.state.invincibility_timer = 999999
    scene.game_controller.state.silent_invincible = True
    scene._homecoming_sequence = HomecomingSequence()
    scene._homecoming_detector = SimpleNamespace(reset=MagicMock())
    scene._homecoming_ui = SimpleNamespace(hide=MagicMock())
    scene.notification_manager = SimpleNamespace(show=MagicMock())

    scene._leave_homecoming_base()

    assert scene.is_homecoming_locked() is True
    assert scene._homecoming_base_pending is False
    assert scene._pause_requested is False
    assert scene.player.controls_locked is True
    assert scene.game_controller.state.paused is True
    assert scene.game_controller.state.player_invincible is True
    assert scene.game_controller.state.invincibility_timer == GameScene.HOMECOMING_LOCK_INVINCIBILITY_TIMER
    assert scene.game_controller.state.silent_invincible is True
    assert scene._homecoming_sequence.phase == HomecomingPhase.BASE_LAUNCH
    scene._homecoming_detector.reset.assert_not_called()
    scene._homecoming_ui.hide.assert_called_once()
    scene.notification_manager.show.assert_called_with("基地弹射程序启动")


def test_game_scene_homecoming_departure_complete_restores_play_state() -> None:
    scene = GameScene()
    scene.player = _make_player()
    scene.game_controller = GameController("medium", "pilot")
    scene._homecoming_sequence = HomecomingSequence()
    scene._homecoming_detector = SimpleNamespace(reset=MagicMock())
    scene._homecoming_ui = SimpleNamespace(hide=MagicMock())
    scene.notification_manager = SimpleNamespace(show=MagicMock())
    scene.player.controls_locked = True
    scene.game_controller.state.paused = True
    scene.game_controller.state.player_invincible = True
    scene.game_controller.state.invincibility_timer = 999999
    scene.game_controller.state.silent_invincible = True

    scene._on_homecoming_departure_complete()

    assert scene.is_homecoming_locked() is False
    assert scene.player.controls_locked is False
    assert scene.game_controller.state.paused is False
    assert scene.game_controller.state.player_invincible is True
    assert scene.game_controller.state.invincibility_timer == GAME_CONSTANTS.PLAYER.INVINCIBILITY_DURATION
    assert scene.game_controller.state.silent_invincible is False
    assert scene.game_controller.state.entrance_animation is True
    assert scene.game_controller.state.entrance_timer == 0
    assert scene.player.rect.y == PlayerConstants.INITIAL_Y
    scene._homecoming_detector.reset.assert_called_once()
    scene._homecoming_ui.hide.assert_called_once()
    scene.notification_manager.show.assert_called_with("已返回战场")


def test_game_scene_homecoming_update_does_not_relock_after_departure_complete() -> None:
    scene = GameScene()
    scene.player = _make_player()
    scene.game_controller = GameController("medium", "pilot")
    scene._homecoming_detector = SimpleNamespace(reset=MagicMock())
    scene._homecoming_ui = SimpleNamespace(hide=MagicMock())
    scene._homecoming_sequence = HomecomingSequence(scene._on_homecoming_complete)
    scene.notification_manager = SimpleNamespace(show=MagicMock())
    scene._set_homecoming_protection(locked=True)
    scene._homecoming_sequence.start_departure(
        scene.player,
        1280,
        720,
        on_complete_callback=scene._on_homecoming_departure_complete,
    )
    scene._homecoming_sequence._set_phase(HomecomingPhase.ORBITAL_STRIKE)
    scene._homecoming_sequence._frame = HomecomingSequence.ORBITAL_STRIKE_FRAMES - 1

    scene._update_homecoming()

    assert scene._homecoming_sequence.phase == HomecomingPhase.INACTIVE
    assert scene.player.controls_locked is False
    assert scene.game_controller.state.paused is False


def test_game_scene_homecoming_orbital_strike_clears_hostiles() -> None:
    scene = GameScene()
    scene.player = _make_player()
    scene.player.get_bullets().append(SimpleNamespace(active=True))
    enemy = SimpleNamespace(active=True, rect=SimpleNamespace(centerx=120, centery=80, width=40))
    boss = SimpleNamespace(active=True, rect=SimpleNamespace(centerx=400, centery=140, width=210, height=170))
    scene.spawn_controller = SimpleNamespace(
        enemies=[enemy],
        boss=boss,
        enemy_bullets=[SimpleNamespace(active=True)],
        reset_boss_timer=MagicMock(),
    )
    scene._bullet_manager = SimpleNamespace(clear_enemy_bullets=MagicMock())
    scene.notification_manager = SimpleNamespace(show=MagicMock())

    scene._on_homecoming_orbital_strike()

    assert scene.spawn_controller.enemies == []
    assert scene.spawn_controller.boss is None
    assert scene.player.get_bullets() == []
    scene.spawn_controller.reset_boss_timer.assert_called_once()
    scene._bullet_manager.clear_enemy_bullets.assert_called_once_with(include_clear_immune=True)
    scene.notification_manager.show.assert_called_with("轨道导弹清场完成")


def test_game_scene_base_loadout_save_persists_current_route(monkeypatch) -> None:
    scene = GameScene()
    scene.player = _make_player()
    scene.game_controller = GameController("medium", "pilot")
    scene.reward_system = scene.game_controller.reward_system
    scene.reward_system.capture_player_baselines(scene.player)
    scene._talent_balance_manager = TalentBalanceManager({"Spread Shot": 1}, {"offense": "Spread Shot"})
    scene.notification_manager = SimpleNamespace(show=MagicMock())

    def create_save_data():
        return GameSaveData(username="pilot", talent_loadout=scene.get_talent_loadout())

    scene._mother_ship_integrator = SimpleNamespace(
        create_save_data=MagicMock(side_effect=create_save_data)
    )
    saved = _capture_base_saves(monkeypatch)

    scene._handle_base_console_action(BaseTalentConsoleAction.select_route("offense"))

    assert scene.reward_system.talent_loadout == {"offense": "Laser"}
    assert saved == [("pilot", {"offense": "Laser"}, False)]


def test_game_scene_homecoming_complete_saves_initial_base_loadout(monkeypatch) -> None:
    scene = GameScene()
    scene.player = _make_player()
    scene.game_controller = GameController("medium", "pilot")
    scene.reward_system = scene.game_controller.reward_system
    scene.reward_system.buff_levels["Spread Shot"] = 1
    scene.reward_system.earned_buff_levels["Spread Shot"] = 1
    scene._base_talent_console = SimpleNamespace(update=MagicMock())
    scene.notification_manager = SimpleNamespace(show=MagicMock())

    def create_save_data():
        return GameSaveData(username="pilot", talent_loadout=scene.get_talent_loadout())

    scene._mother_ship_integrator = SimpleNamespace(
        create_save_data=MagicMock(side_effect=create_save_data)
    )
    saved = _capture_base_saves(monkeypatch)

    scene._on_homecoming_complete()

    assert scene.reward_system.talent_loadout == {"offense": "Spread Shot"}
    assert saved == [("pilot", {"offense": "Spread Shot"}, False)]


def test_game_scene_leaving_base_saves_current_loadout(monkeypatch) -> None:
    scene = GameScene()
    scene.player = _make_player()
    scene.game_controller = GameController("medium", "pilot")
    scene.reward_system = scene.game_controller.reward_system
    scene.reward_system.talent_loadout = {"offense": "Laser"}
    scene._homecoming_base_pending = True
    scene._homecoming_sequence = HomecomingSequence()
    scene._homecoming_detector = SimpleNamespace(reset=MagicMock())
    scene._homecoming_ui = SimpleNamespace(hide=MagicMock())
    scene.notification_manager = SimpleNamespace(show=MagicMock())

    def create_save_data():
        return GameSaveData(username="pilot", talent_loadout=scene.get_talent_loadout())

    scene._mother_ship_integrator = SimpleNamespace(
        create_save_data=MagicMock(side_effect=create_save_data)
    )
    saved = _capture_base_saves(monkeypatch)

    scene._leave_homecoming_base()

    assert saved == [("pilot", {"offense": "Laser"}, False)]


def test_game_scene_base_route_action_applies_loadout() -> None:
    scene = GameScene()
    scene.player = _make_player()
    scene.game_controller = GameController("medium", "pilot")
    scene.reward_system = scene.game_controller.reward_system
    scene.reward_system.capture_player_baselines(scene.player)
    scene._talent_balance_manager = TalentBalanceManager({"Spread Shot": 1}, {"offense": "Spread Shot"})
    scene.notification_manager = SimpleNamespace(show=MagicMock())

    scene._handle_base_console_action(BaseTalentConsoleAction.select_route("offense"))

    assert scene.reward_system.talent_loadout["offense"] == "Laser"
    assert scene.reward_system.locked_buffs == {"Spread Shot"}
    assert scene.player.get_weapon_status()["laser"] is True
    scene.notification_manager.show.assert_called_with("基地天赋配置已同步")


def test_game_scene_base_resupply_restores_ship_and_saves(monkeypatch) -> None:
    scene = GameScene()
    scene.player = _make_player()
    scene.player.max_health = 140
    scene.player.health = 35
    scene.player.boost_max = 220
    scene.player.boost_current = 40
    scene.game_controller = GameController("medium", "pilot")
    scene.game_controller.state.requisition_points = 10
    scene.reward_system = scene.game_controller.reward_system
    scene.reward_system.talent_loadout = {"offense": "Laser"}
    scene.notification_manager = SimpleNamespace(show=MagicMock())

    def create_save_data():
        return GameSaveData(username="pilot", talent_loadout=scene.get_talent_loadout())

    scene._mother_ship_integrator = SimpleNamespace(
        create_save_data=MagicMock(side_effect=create_save_data)
    )
    saved = _capture_base_saves(monkeypatch)

    scene._handle_base_console_action(BaseTalentConsoleAction.resupply())

    assert scene.player.health == scene.player.max_health
    assert scene.player.boost_current == scene.player.boost_max
    assert scene.game_controller.state.requisition_points == 6  # 10 - 4(resupply cost)
    assert saved == [("pilot", {"offense": "Laser"}, False)]
    scene.notification_manager.show.assert_called_with("基地全面补给完成 (-4RP)")


def test_game_scene_base_module_action_does_not_change_loadout() -> None:
    scene = GameScene()
    scene.player = _make_player()
    scene.game_controller = GameController("medium", "pilot")
    scene.reward_system = scene.game_controller.reward_system
    scene.reward_system.talent_loadout = {"offense": "Spread Shot"}

    scene._handle_base_console_action(BaseTalentConsoleAction.select_module("mission"))

    assert scene.reward_system.talent_loadout == {"offense": "Spread Shot"}


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
