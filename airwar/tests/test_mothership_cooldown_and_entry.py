from types import SimpleNamespace

import pygame

from airwar.game.mother_ship import (
    EventBus,
    GameIntegrator,
    InputDetector,
    MotherShip,
    MotherShipStateMachine,
    PersistenceManager,
    ProgressBarUI,
)


def _make_integrator():
    event_bus = EventBus()
    input_detector = InputDetector(event_bus)
    state_machine = MotherShipStateMachine(event_bus)
    persistence_manager = PersistenceManager(save_dir="/tmp/airwar-test-save")
    progress_bar_ui = ProgressBarUI(1920, 1080)
    mother_ship = MotherShip(1920, 1080)
    integrator = GameIntegrator(
        event_bus=event_bus,
        input_detector=input_detector,
        state_machine=state_machine,
        persistence_manager=persistence_manager,
        progress_bar_ui=progress_bar_ui,
        mother_ship=mother_ship,
    )
    return integrator


def test_mothership_early_undock_cooldown_reduction_is_capped():
    integrator = _make_integrator()

    integrator._state_machine.stay_progress.stay_progress = 0.0
    assert integrator._calculate_undocking_cooldown_multiplier() == 0.6

    integrator._state_machine.stay_progress.stay_progress = 0.5
    assert integrator._calculate_undocking_cooldown_multiplier() == 0.8

    integrator._state_machine.stay_progress.stay_progress = 1.0
    assert integrator._calculate_undocking_cooldown_multiplier() == 1.0


def test_mothership_early_undock_cooldown_stacks_with_recall_buff():
    integrator = _make_integrator()
    player = SimpleNamespace(mothership_cooldown_mult=0.5)
    integrator._game_scene = SimpleNamespace(player=player)
    integrator._undocking_cooldown_multiplier = 0.8

    integrator._apply_cooldown_multiplier_from_player()

    assert integrator._state_machine.cooldown.cooldown_multiplier == 0.4


def test_mothership_phantom_fades_in_instead_of_full_opacity_immediately():
    mother_ship = MotherShip(1920, 1080)
    mother_ship.show_phantom()
    start_ms = mother_ship._phantom_started_at

    assert mother_ship._get_phantom_reveal(start_ms) == 0.0
    assert 0.0 < mother_ship._get_phantom_reveal(start_ms + 120) < 1.0
    assert mother_ship._get_phantom_reveal(start_ms + 700) == 1.0


def test_mothership_phantom_first_render_is_not_abrupt(monkeypatch):
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 1000)
    surface = pygame.Surface((1920, 1080), pygame.SRCALPHA)
    mother_ship = MotherShip(1920, 1080)
    mother_ship.show_phantom()

    mother_ship._render_phantom(surface)

    assert surface.get_bounding_rect().width == 0
