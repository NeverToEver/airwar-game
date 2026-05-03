import pytest

from airwar.entities.base import Vector2
from airwar.entities.player import Player
from airwar.game.managers.game_controller import GameController
from airwar.input.input_handler import InputHandler, MockInputHandler
from airwar.scenes.game_scene import GameScene


def _make_player(x=400, y=700):
    input_handler = MockInputHandler()
    player = Player(x, y, input_handler)
    player.boost_max = 200
    player.boost_current = 200
    player.boost_recovery_delay = 999
    player.boost_recovery_ramp = 1
    return player, input_handler


def _finish_dash(player):
    for _ in range(
        Player.PHASE_DASH_WINDUP_FRAMES
        + Player.PHASE_DASH_ACTIVE_FRAMES
        + Player.PHASE_DASH_RECOVERY_FRAMES
        + 2
    ):
        player.update()


def test_phase_dash_requires_talent_unlock():
    player, input_handler = _make_player()
    input_handler.set_direction(1, 0)
    input_handler.tap_boost()

    player.update()

    assert not player.is_phase_dashing()
    assert player.boost_current == 199
    assert player.rect.x == 400 + player.base_speed * player.boost_speed_mult


def test_input_handler_requires_boost_edge_detector():
    class LegacyInputHandler(InputHandler):
        def get_movement_direction(self):
            return Vector2()

        def is_pause_pressed(self) -> bool:
            return False

        def is_boost_pressed(self) -> bool:
            return False

    with pytest.raises(TypeError):
        LegacyInputHandler()


def test_phase_dash_consumes_quarter_boost_and_moves_smoothly():
    player, input_handler = _make_player()
    player.activate_phase_dash()
    start_x = player.rect.x
    input_handler.set_direction(1, 0)
    input_handler.tap_boost()

    player.update()

    assert player.is_phase_dashing()
    assert player.is_phase_dash_invincible()
    assert player.boost_current == 150
    assert player.rect.x == start_x

    for _ in range(Player.PHASE_DASH_WINDUP_FRAMES + 1):
        player.update()

    assert start_x < player.rect.x < start_x + Player.PHASE_DASH_DISTANCE

    _finish_dash(player)

    assert not player.is_phase_dashing()
    assert player.rect.x >= start_x + Player.PHASE_DASH_MIN_DISTANCE
    status = player.get_boost_status()
    assert status["dash_cooldown"] > 0
    assert status["dash_ready"] is False


def test_phase_dash_cooldown_prevents_immediate_second_dash():
    player, input_handler = _make_player()
    player.activate_phase_dash()
    input_handler.set_direction(1, 0)
    input_handler.tap_boost()
    player.update()
    _finish_dash(player)
    boost_after_first_dash = player.boost_current

    input_handler.set_boost_pressed(False)
    player.update()
    input_handler.tap_boost()
    player.update()

    assert not player.is_phase_dashing()
    assert player.boost_current == boost_after_first_dash - 1


def test_phase_dash_reward_unlocks_player_ability():
    player, _ = _make_player()
    controller = GameController("medium", "Test")

    notification = controller.reward_system.apply_reward({"name": "Phase Dash"}, player)

    assert "Phase Dash" in notification
    assert player.phase_dash_enabled is True
    assert controller.reward_system.buff_levels["Phase Dash"] == 1


def test_game_scene_syncs_phase_dash_invincibility_without_permanent_flag():
    scene = GameScene()
    player, _ = _make_player()
    player.activate_phase_dash()
    player._phase_dash_state = "active"
    player._phase_dash_timer = 1
    scene.player = player
    scene.game_controller = GameController("medium", "Test")

    scene._sync_player_phase_dash_invincibility()

    assert scene.game_controller.state.player_invincible is True
    assert scene.game_controller.state.silent_invincible is True

    player._phase_dash_state = "ready"
    scene._sync_player_phase_dash_invincibility()

    assert scene.game_controller.state.player_invincible is False
    assert scene.game_controller.state.silent_invincible is False
