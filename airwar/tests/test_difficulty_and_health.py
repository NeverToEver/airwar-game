import pytest

from airwar.config import HEALTH_REGEN
from airwar.game.systems.difficulty_manager import DifficultyManager
from airwar.game.systems.health_system import HealthSystem


class FakePlayer:
    def __init__(self, health=50, max_health=100):
        self.health = health
        self.max_health = max_health


class RecordingListener:
    def __init__(self):
        self.params = []

    def on_difficulty_changed(self, params):
        self.params.append(params)


class FailingListener:
    def on_difficulty_changed(self, params):
        raise RuntimeError("listener failed")


def test_difficulty_manager_caps_boss_kill_count():
    manager = DifficultyManager("hard")

    manager.set_boss_kill_count(manager.MAX_BOSS_COUNT + 10)

    assert manager.get_boss_kill_count() == manager.MAX_BOSS_COUNT
    assert manager.get_current_multiplier() <= manager.MAX_MULTIPLIER_GLOBAL


def test_difficulty_manager_rejects_negative_boss_kill_count():
    manager = DifficultyManager("medium")

    with pytest.raises(ValueError):
        manager.set_boss_kill_count(-1)


def test_difficulty_manager_notifies_and_removes_failing_listeners():
    manager = DifficultyManager("medium")
    recording = RecordingListener()
    failing = FailingListener()
    manager.add_listener(recording)
    manager.add_listener(failing)

    manager.on_boss_killed()
    manager.on_boss_killed()

    assert len(recording.params) == 2
    assert failing not in manager._listeners


def test_health_system_normal_regen_waits_for_delay_and_interval():
    player = FakePlayer(health=50, max_health=100)
    system = HealthSystem("medium")
    settings = HEALTH_REGEN["medium"]

    for _ in range(settings["delay"] + settings["interval"] - 2):
        system.update(player)

    assert player.health == 50

    system.update(player)

    assert player.health == 52


def test_health_system_buff_regen_uses_shorter_fixed_tick():
    player = FakePlayer(health=50, max_health=51)
    system = HealthSystem("medium")

    for _ in range(60):
        system.update(player, has_regen_buff=True)

    assert player.health == 51
