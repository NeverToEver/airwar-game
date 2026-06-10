import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def pytest_configure(config):
    config.addinivalue_line("markers", "smoke: Smoke tests - core functionality verification")


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


# ---------------------------------------------------------------------------
# Generic entity stubs.
#
# Consolidated from near-identical local helpers in
# test_difficulty_and_health.py / test_collision_controller.py /
# test_mothership_cooldown_and_entry.py (P2-3 audit, 2026-06-10).
#
# The classes are public on this module so tests that need to subclass
# (e.g. ``Boss(StubEnemy)``) can do ``from .conftest import StubEnemy``.
# Tests that just need an instance should use the ``stub_*`` fixtures
# below.
# ---------------------------------------------------------------------------


class StubPlayer:
    """Player double for collision / health-system tests.

    Provides:
    - ``rect`` + ``_hitbox`` + ``get_hitbox()`` for collision tests.
    - ``health`` + ``max_health`` for health-system tests.
    - ``take_damage()`` to mirror the real Player API.
    """

    def __init__(self, rect=None, health=100, max_health=100):
        if rect is None:
            from airwar.entities.base import Rect
            rect = Rect(0, 0, 20, 20)
        self._hitbox = rect
        self.rect = rect
        self.health = health
        self.max_health = max_health

    def get_hitbox(self):
        return self._hitbox

    def take_damage(self, damage):
        self.health -= damage


class StubEnemy:
    """Enemy / target double for collision and mothership tests.

    Defaults: health 10, score 25. Tests can override via kwargs.
    Mirrors the surface used by ``CollisionController`` and
    ``MotherShipIntegrator`` -- ``get_hitbox`` / ``get_rect`` for
    collision, ``take_damage`` for HP bookkeeping, ``active`` flag
    for cleanup.
    """

    def __init__(self, rect=None, health=10, score=25):
        if rect is None:
            from airwar.entities.base import Rect
            rect = Rect(0, 0, 20, 20)
        self.rect = rect
        self._hitbox = rect
        from airwar.entities.base import EnemyData
        self.data = EnemyData(health=health, score=score)
        self.health = health
        self.active = True

    def get_hitbox(self):
        return self._hitbox

    def get_rect(self):
        return self.rect

    def take_damage(self, damage):
        self.health -= damage
        if self.health <= 0:
            self.active = False


class StubBullet:
    """Bullet double for collision tests.

    Tracks which enemies it has already damaged (piercing bullet
    bookkeeping) via the same ``has_hit_enemy`` / ``add_hit_enemy``
    API as the real Bullet class.
    """

    def __init__(self, rect=None, data=None, active=True):
        if rect is None:
            from airwar.entities.base import Rect
            rect = Rect(0, 0, 10, 10)
        if data is None:
            from airwar.entities.base import BulletData
            data = BulletData()
        self.rect = rect
        self.data = data
        self.active = active
        self._hit_enemies = []

    def get_rect(self):
        return self.rect

    def has_hit_enemy(self, enemy_id: int) -> bool:
        return enemy_id in self._hit_enemies

    def add_hit_enemy(self, enemy_id: int) -> None:
        self._hit_enemies.append(enemy_id)


@pytest.fixture
def stub_player():
    """Lightweight Player stub for collision / health-system tests."""
    return StubPlayer()


@pytest.fixture
def stub_enemy():
    """Lightweight Enemy stub for collision / mothership tests."""
    return StubEnemy()


@pytest.fixture
def stub_bullet():
    """Lightweight Bullet stub for collision tests."""
    return StubBullet()


class StubPlayerForStateMachine:
    """Duck-type placeholder for ``PlayerStateMachine.__init__``.

    Consolidated from 3 identical local ``_StubPlayer`` classes in
    ``test_player_state_machine.py``,
    ``test_logic_clarity/test_F03_silent_failure.py``, and
    ``test_logic_clarity/test_property_player_hsm.py`` (P2-3 follow-up,
    2026-06-10). The class body is intentionally empty: it asserts the
    contract that ``PlayerStateMachine`` constructor does not touch
    any attribute on the player it receives.
    """

    pass


@pytest.fixture
def stub_player_for_state_machine():
    """Empty Player placeholder for PlayerStateMachine unit tests."""
    return StubPlayerForStateMachine()
