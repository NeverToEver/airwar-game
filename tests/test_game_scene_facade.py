"""Regression tests for the GameScene facade."""

from types import SimpleNamespace

from airwar.scenes.game_scene import GameScene


class TestGameSceneEventBus:
    def test_event_bus_forwards_to_integrator(self):
        scene = GameScene()
        bus = object()
        scene._mother_ship_integrator = SimpleNamespace(event_bus=bus)
        assert scene.event_bus is bus

    def test_event_bus_is_none_without_integrator(self):
        scene = GameScene()
        scene._mother_ship_integrator = None
        assert scene.event_bus is None
