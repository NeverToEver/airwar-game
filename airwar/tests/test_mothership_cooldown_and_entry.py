from types import SimpleNamespace

import pygame

from airwar.entities.base import Rect
from airwar.game.mother_ship import (
    EventBus,
    GameIntegrator,
    InputDetector,
    MotherShip,
    MotherShipState,
    MotherShipStateMachine,
    PersistenceManager,
    ProgressBarUI,
)
from airwar.game.mother_ship.event_bus import EVENT_START_UNDOCKING_ANIMATION


class FakeTarget:
    def __init__(self, x=960, y=360, width=40, height=40, health=200, score=90):
        self.rect = Rect(x, y, width, height)
        self.health = health
        self.active = True
        self.data = SimpleNamespace(score=score)

    def get_hitbox(self):
        return self.rect

    def take_damage(self, damage):
        self.health -= damage
        if self.health <= 0:
            self.active = False


class FakeGameScene:
    def __init__(self, enemies=None, boss=None):
        self.enemies = enemies or []
        self.boss = boss
        self.spawn_controller = SimpleNamespace()
        self.player = SimpleNamespace(mothership_cooldown_mult=1.0)
        self.explosions = []
        self.score = 0
        self.kills = 0
        self.boss_kills = 0
        self.boss_death_explosions = []
        self.notifications = []

    def get_enemies(self):
        return self.enemies

    def get_boss(self):
        return self.boss

    def trigger_explosion(self, x, y, radius):
        self.explosions.append((x, y, radius))

    def add_score(self, amount):
        self.score += amount

    def add_kill(self):
        self.kills += 1

    def add_boss_kill(self):
        self.boss_kills += 1

    def clear_boss(self):
        self.boss = None

    def trigger_boss_death_explosion(self, boss):
        self.boss_death_explosions.append(boss)

    def show_notification(self, message):
        self.notifications.append(message)


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


def test_mothership_cooldown_status_exposes_reduced_return_timer(monkeypatch):
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: 10_000)
    integrator = _make_integrator()
    integrator._state_machine.force_state(MotherShipState.COOLDOWN)
    cooldown = integrator._state_machine.cooldown
    cooldown.cooldown_multiplier = 0.6
    cooldown.start_cooldown(4.0)
    cooldown.update_cooldown(10.0)

    status = integrator.get_status_data()

    assert status["is_in_cooldown"] is True
    assert status["cooldown_duration"] == 36.0
    assert status["cooldown_base_duration"] == 60.0
    assert status["cooldown_multiplier"] == 0.6
    assert status["cooldown_reduction"] == 0.4
    assert status["cooldown_remaining"] == 30.0
    assert status["ammo_count"] == 6.0 / 36.0 * integrator.AMMO_CELL_COUNT


def test_docked_mothership_requires_exit_hold_before_undocking():
    event_bus = EventBus()
    state_machine = MotherShipStateMachine(event_bus)
    started = []
    event_bus.subscribe(EVENT_START_UNDOCKING_ANIMATION, lambda **_: started.append(True))
    state_machine.force_state(MotherShipState.DOCKED)

    event_bus.publish("H_PRESSED")

    assert state_machine.current_state == MotherShipState.DOCKED
    assert state_machine.is_exit_in_progress() is True
    assert started == []

    event_bus.publish("EXIT_COMPLETE")

    assert state_machine.current_state == MotherShipState.UNDOCKING
    assert started == [True]


def test_event_bus_unsubscribes_repeatedly_failing_callback():
    event_bus = EventBus()
    calls = []

    def broken_callback(**_):
        calls.append("broken")
        raise RuntimeError("callback failed")

    event_bus.subscribe("BROKEN_EVENT", broken_callback)

    for _ in range(4):
        event_bus.publish("BROKEN_EVENT")

    assert calls == ["broken", "broken", "broken"]


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


def test_mothership_render_uses_wide_carrier_silhouette():
    surface = pygame.Surface((1920, 1080), pygame.SRCALPHA)
    mother_ship = MotherShip(1920, 1080)
    mother_ship.show()

    mother_ship.render(surface)
    bounds = surface.get_bounding_rect()

    assert bounds.width >= 480
    assert bounds.height >= 220
    assert bounds.width > bounds.height * 1.8


def test_mothership_gatling_turrets_cover_120_degrees_with_overlap():
    integrator = _make_integrator()
    left, right = integrator.MOTHERSHIP_GATLING_TURRETS

    assert left.angle_min == -60.0
    assert right.angle_max == 60.0
    assert left.angle_max - left.angle_min == integrator.MOTHERSHIP_GATLING_SWEEP_ARC_DEGREES
    assert right.angle_max - right.angle_min == integrator.MOTHERSHIP_GATLING_SWEEP_ARC_DEGREES
    assert left.angle_max > right.angle_min
    assert right.angle_max - left.angle_min == integrator.MOTHERSHIP_GATLING_TOTAL_SWEEP_DEGREES
    assert left.angle_max - right.angle_min == integrator.MOTHERSHIP_GATLING_OVERLAP_DEGREES


def test_mothership_gatling_turrets_sweep_out_of_sync():
    integrator = _make_integrator()

    integrator._mothership_gatling_sweep_frame = 0
    left_start = integrator._current_gatling_sweep_angle("left")
    right_start = integrator._current_gatling_sweep_angle("right")
    integrator._mothership_gatling_sweep_frame = integrator.MOTHERSHIP_GATLING_SWEEP_PERIOD // 2
    left_mid = integrator._current_gatling_sweep_angle("left")
    right_mid = integrator._current_gatling_sweep_angle("right")

    assert left_start != right_start
    assert left_mid != right_mid
    assert integrator.MOTHERSHIP_GATLING_TURRETS[0].period != integrator.MOTHERSHIP_GATLING_TURRETS[1].period


def test_mothership_gatling_fires_high_frequency_sweep_bullets():
    integrator = _make_integrator()
    integrator._game_scene = FakeGameScene(enemies=[FakeTarget(960, 220)])

    for _ in range(integrator.MOTHERSHIP_GATLING_FIRE_RATE):
        integrator._update_mothership_firing()

    gatling = [
        bullet for bullet in integrator._mothership_bullets
        if bullet.data.bullet_type == integrator.MOTHERSHIP_GATLING_BULLET_TYPE
    ]
    missiles = [bullet for bullet in integrator._mothership_bullets if bullet.data.is_explosive]

    assert len(gatling) == len(integrator.MOTHERSHIP_GATLING_TURRETS)
    assert missiles == []
    assert {bullet.data.damage for bullet in gatling} == {integrator.MOTHERSHIP_GATLING_DAMAGE}
    assert {bullet.data.is_explosive for bullet in gatling} == {False}
    assert gatling[0].rect.x < gatling[1].rect.x
    assert gatling[0].velocity.x != gatling[1].velocity.x


def test_mothership_gatling_hit_does_not_trigger_missile_explosion():
    target = FakeTarget(x=500, y=500, width=40, height=40, health=80)
    scene = FakeGameScene(enemies=[target])
    integrator = _make_integrator()
    integrator._game_scene = scene
    integrator._fire_gatling_sweep()
    bullet = integrator._mothership_bullets[0]
    integrator._mothership_bullets = [bullet]
    bullet.rect.x = target.rect.x
    bullet.rect.y = target.rect.y
    bullet.velocity.x = 0
    bullet.velocity.y = 0

    integrator._update_mothership_bullets()

    assert target.health == 80 - integrator.MOTHERSHIP_GATLING_DAMAGE
    assert scene.explosions == []
    assert integrator._mothership_bullets == []


def test_mothership_boss_kill_triggers_wreck_explosion_before_clear():
    boss = FakeTarget(x=500, y=500, width=120, height=120, health=1, score=1000)
    scene = FakeGameScene(boss=boss)
    integrator = _make_integrator()
    integrator._game_scene = scene

    integrator._on_mothership_kill_boss(boss)

    assert scene.boss_death_explosions == [boss]
    assert scene.boss is None
    assert scene.boss_kills == 1
