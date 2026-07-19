"""P1 regression tests: boss enrage vs mothership docking.

Sub-problem A: while the player is docked, the update pipeline must
tell the boss to skip its screen-center enrage grab, and the docking
position lock must leave rect and hitbox consistent.

Sub-problem B: while the boss enrage grab (transition or active dash)
is running, the mothership holds position and ceases fire; everything
resumes once the enrage ends.
"""

from types import SimpleNamespace

import pygame

from airwar.game.mother_ship.game_integrator import GameIntegrator
from airwar.scenes.game_scene_updater import GameSceneUpdater


def _make_core_logic_updater(docked: bool, boss, player, updates: list) -> GameSceneUpdater:
    updater = object.__new__(GameSceneUpdater)
    updater._docked = docked
    updater._scene = SimpleNamespace(
        player=player,
        spawn_controller=SimpleNamespace(boss=boss),
        _game_loop_manager=SimpleNamespace(update_game=lambda p: updates.append(p)),
        _mother_ship_integrator=SimpleNamespace(get_docking_position=lambda: (500, 400)),
    )
    return updater


def test_core_logic_step_locks_enrage_centering_when_docked():
    """Docked frame: the boss is told the player position is locked
    BEFORE update_game runs, and the dock lock leaves rect + hitbox
    consistent at the docking bay."""
    hitbox_syncs = []
    player = SimpleNamespace(
        rect=pygame.Rect(0, 0, 40, 30),
        sync_hitbox=lambda: hitbox_syncs.append(True),
    )
    boss = SimpleNamespace(player_position_locked=False)
    updater = _make_core_logic_updater(docked=True, boss=boss, player=player, updates=[])

    updater._step_core_logic()

    assert boss.player_position_locked is True
    assert (player.rect.centerx, player.rect.centery) == (500, 400)
    assert hitbox_syncs  # hitbox re-synced after the dock lock writes rect


def test_core_logic_step_unlocks_enrage_centering_when_not_docked():
    """Free-flight frame: the boss flag is cleared and the dock lock
    does not touch the player rect."""
    hitbox_syncs = []
    player = SimpleNamespace(
        rect=pygame.Rect(0, 0, 40, 30),
        sync_hitbox=lambda: hitbox_syncs.append(True),
    )
    boss = SimpleNamespace(player_position_locked=True)
    updater = _make_core_logic_updater(docked=False, boss=boss, player=player, updates=[])

    updater._step_core_logic()

    assert boss.player_position_locked is False
    assert (player.rect.x, player.rect.y) == (0, 0)
    assert not hitbox_syncs


def _make_integrator(boss, inputs: list, player_positions: list) -> GameIntegrator:
    integrator = GameIntegrator(
        event_bus=SimpleNamespace(),
        input_detector=SimpleNamespace(update=lambda t: None),
        state_machine=SimpleNamespace(
            is_docked=lambda: True,
            is_entering=lambda: False,
            set_current_time=lambda t: None,
            update=lambda t: None,
        ),
        progress_bar_ui=SimpleNamespace(),
        mother_ship=SimpleNamespace(
            is_visible=lambda: True,
            set_player_input=lambda x, y: inputs.append((x, y)),
            update=lambda: None,
            get_docking_position=lambda: (500, 400),
        ),
    )
    integrator._game_scene = SimpleNamespace(
        get_boss=lambda: boss,
        get_enemies=lambda: [],
        spawn_controller=object(),
        set_player_position=lambda x, y: player_positions.append((x, y)),
    )
    return integrator


def _enraged_boss() -> SimpleNamespace:
    return SimpleNamespace(active=True, is_enrage_engaged=lambda: True)


def test_mothership_holds_position_and_ceases_fire_during_enrage():
    """P1-B: docked + enrage engaged → movement input zeroed, firing
    skipped entirely, player still bound to the docking bay."""
    inputs, player_positions = [], []
    integrator = _make_integrator(_enraged_boss(), inputs, player_positions)

    integrator.update(delta_seconds=1.0, elapsed_seconds=10.0)

    assert integrator._boss_enrage_engaged is True
    assert inputs == [(0, 0)]  # position locked, keyboard ignored
    assert integrator._mothership_fire_elapsed == 0.0  # ceasefire: timer frozen
    assert integrator._mothership_bullets == []
    assert player_positions == [(500, 400)]  # player stays bound to the dock


def test_mothership_resumes_movement_and_fire_after_enrage():
    """P1-B: once the enrage ends, the cache flips back and both
    movement input and the fire timer resume on the next frame."""
    inputs, player_positions = [], []
    boss = _enraged_boss()
    integrator = _make_integrator(boss, inputs, player_positions)

    integrator.update(delta_seconds=1.0, elapsed_seconds=10.0)
    assert integrator._mothership_fire_elapsed == 0.0

    boss.is_enrage_engaged = lambda: False  # enrage over
    integrator.update(delta_seconds=0.1, elapsed_seconds=11.0)

    assert integrator._boss_enrage_engaged is False
    assert integrator._mothership_fire_elapsed == 0.1  # fire timer ticking again


def test_mothership_behaves_normally_without_boss():
    """No boss (or dead boss) → enrage cache stays clear, fire timer runs."""
    inputs, player_positions = [], []
    integrator = _make_integrator(None, inputs, player_positions)

    integrator.update(delta_seconds=0.1, elapsed_seconds=10.0)

    assert integrator._boss_enrage_engaged is False
    assert integrator._mothership_fire_elapsed == 0.1
