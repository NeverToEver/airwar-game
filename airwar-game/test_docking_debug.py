"""
回归测试：验证 H 键在入场动画期间也能触发母舰停靠流程。
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from collections import defaultdict

import pygame

from airwar.game.mother_ship.mother_ship_state import MotherShipState
from airwar.scenes.game_scene import GameScene


def _pressed_keys(*pressed_keys: int):
    state = defaultdict(int)
    for key in pressed_keys:
        state[key] = 1
    return state


def test_h_key_docking_flow_during_entrance(monkeypatch):
    """测试完整的 H 键触发进入母舰流程。"""
    pygame.init()
    pygame.display.set_mode((800, 600))

    try:
        scene = GameScene()
        scene.enter(difficulty='medium', username='TestPilot')

        assert scene._mother_ship_integrator is not None
        assert scene.game_controller.state.entrance_animation is True

        tick_state = {'current': 0}

        def fake_get_ticks():
            value = tick_state['current']
            tick_state['current'] += 100
            return value

        monkeypatch.setattr(pygame.time, 'get_ticks', fake_get_ticks)
        monkeypatch.setattr(pygame.key, 'get_pressed', lambda: _pressed_keys(pygame.K_h))

        for _ in range(40):
            scene.update()

        state_machine = scene._mother_ship_integrator._state_machine

        assert state_machine.current_state in (MotherShipState.DOCKING, MotherShipState.DOCKED)
        assert scene._mother_ship_integrator.is_docking_animation_active() or (
            state_machine.current_state == MotherShipState.DOCKED
        )
        assert scene.game_controller.state.entrance_animation is True
    finally:
        pygame.display.quit()
        pygame.quit()
