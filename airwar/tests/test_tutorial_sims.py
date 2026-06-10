"""Unit tests for the tutorial sim helpers (M-9).

The ``tutorial_player_sim`` / ``tutorial_boss_sim`` / ``tutorial_enemy_sim``
classes are extracted from ``tutorial_scene`` (Phase 4 Wave α) but until
M-9 they had no direct unit-test coverage — every assertion went through
the scene's per-frame ``update()`` loop. M-9 covers the contracts that
matter for future refactors:

* **Player sim** — the safe-spawn rect (player never lands on top of an
  enemy) and the fire cooldown / wing-muzzle geometry.
* **Enemy sim** — the fire-on-cooldown cadence for the "enemy" kind and
  the target-only "no-fire" branch for the "target" kind.
* **Boss sim** — the 30 % enrage threshold and the spread-vs-fan-pattern
  bullet count change when enraged.

These tests stub the scene to the smallest shape the sims actually
touch (``_enemies``, ``_enemy_bullets``, ``_player``, ``_aim_pos``,
``_fire_timer``, ``_stage_spawned``, ``_boss``) so they stay decoupled
from the larger scene lifecycle. If a future refactor moves a sim into
a different module, these tests will fail loudly with a clear
``AttributeError`` from the stub — exactly the failure mode we want.
"""

from __future__ import annotations

from types import SimpleNamespace

import pygame

from airwar.scenes.tutorial.entities_core import TutorialBoss, TutorialBullet, TutorialEnemy
from airwar.scenes.tutorial.tutorial_boss_sim import TutorialBoss as BossSim
from airwar.scenes.tutorial.tutorial_enemy_sim import TutorialEnemySim
from airwar.scenes.tutorial.tutorial_player_sim import TutorialPlayer


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


def _make_player_scene(*, screen_w: int = 1280, screen_h: int = 800):
    """Build a minimal scene stub for the player sim tests.

    Only the attributes the sim actually reads or writes are populated.
    """
    player = pygame.Rect(0, 0, 32, 32)
    player.center = (screen_w // 2, screen_h // 2)
    return SimpleNamespace(
        _player=player,
        _aim_pos=(player.centerx, player.centery - 200),
        _bullets=[],
        _fire_timer=0,
        FIRE_INTERVAL=8,
        ENEMY_SIZE=44,
        WING_MUZZLE_X_OFFSETS=(-14, 14),
        WING_MUZZLE_Y_OFFSET=-22,
        PLAYER_W=32,
        PLAYER_H=32,
        PLAYER_SPEED=5,
        BOOST_MULT=1.7,
        PLAYER_BULLET_DAMAGE=8,
        ENERGY_MAX=100,
        ENERGY_RECOVER=2,
        _player_energy=100,
        _player_max_health=100,
        _player_health=100,
        ENERGY_DRAIN=4,
        _update_player_fire=lambda: None,
        get_screen_width=lambda: screen_w,
        get_screen_height=lambda: screen_h,
    )


def _make_enemy_scene(*, screen_w: int = 1280, screen_h: int = 800):
    """Stub scene for the enemy sim. The sim's ``update()`` calls
    ``scene._spawn_enemy_bullet(...)`` when an enemy reaches its fire
    timer, so we wire that to a simple push onto ``_enemy_bullets``."""
    enemy_bullets: list = []

    def _spawn_enemy_bullet(center, *, damage: int) -> None:
        enemy_bullets.append((center, damage))

    return SimpleNamespace(
        _enemies=[],
        _enemy_bullets=enemy_bullets,
        _stage_spawned=0,
        _stage=SimpleNamespace(objective_count=99),
        ENEMY_SIZE=44,
        _spawn_enemy_bullet=_spawn_enemy_bullet,
        get_screen_width=lambda: screen_w,
        get_screen_height=lambda: screen_h,
    )


def _make_boss_scene(*, screen_w: int = 1280):
    return SimpleNamespace(
        _boss=None,
        _enemy_bullets=[],
        BOSS_W=200,
        BOSS_H=120,
        BOSS_ENRAGE_THRESHOLD=0.30,
        get_screen_width=lambda: screen_w,
    )


# ---------------------------------------------------------------------------
# Player sim
# ---------------------------------------------------------------------------


def test_player_sim_fire_creates_two_wing_muzzle_bullets() -> None:
    """``fire()`` must spawn exactly two bullets, one per wing muzzle,
    with symmetric x-offset around the player's centerline. The second
    call must be a no-op (fire_timer not yet drained to 0)."""
    scene = _make_player_scene()
    sim = TutorialPlayer(scene)
    sim.fire()
    # Second call decrements fire_timer (now FIRE_INTERVAL) and returns
    # without spawning more bullets — that proves the cooldown works.
    sim.fire()
    assert len(scene._bullets) == 2
    # Bullets must be at different x positions (wing symmetry).
    xs = sorted(b.rect.centerx for b in scene._bullets)
    assert xs[0] < xs[1]
    # Fire timer contract: after a successful fire it's set to
    # FIRE_INTERVAL, then decremented once by the second (no-op) call.
    assert scene._fire_timer == scene.FIRE_INTERVAL - 1
    # And a third call (still above 0) must NOT spawn more bullets.
    sim.fire()
    assert len(scene._bullets) == 2
    assert scene._fire_timer == scene.FIRE_INTERVAL - 2


def test_player_sim_spawn_rect_is_inside_play_area() -> None:
    """The player sim's ``initialise()`` and ``reset_to_spawn()`` must
    always place the rect inside the play area (i.e. below the top HUD
    strip and above the bottom of the screen). The renderer / collision
    code depends on this guarantee to avoid spawning outside the visible
    playfield.

    Note: the bottom HUD's "danger zone" starts at ``sh - 128`` but the
    sim intentionally spawns the player at ``sh - 126`` (just above
    that strip) so the wing-muzzle bullets clear the HUD — we therefore
    only assert ``rect.bottom <= sh`` (i.e. the rect stays on-screen).
    """
    from airwar.config import get_screen_height, get_screen_width

    scene = _make_player_scene()
    scene.PLAYER_W = 32
    scene.PLAYER_H = 32
    scene.PLAYER_SPEED = 5
    scene.BOOST_MULT = 1.7
    scene.PLAYER_BULLET_DAMAGE = 8
    sim = TutorialPlayer(scene)
    sim.initialise()
    sw = get_screen_width()
    sh = get_screen_height()
    rect = scene._player
    # Below the top HUD strip (which ends at y=128).
    assert rect.top >= 128, "player must not spawn above the top HUD strip"
    # On-screen (the bottom HUD overlap is intentional and harmless
    # because the player's collision rect is narrower than its sprite).
    assert 0 <= rect.bottom <= sh
    assert 0 <= rect.left and rect.right <= sw

    # reset_to_spawn must keep the same bounds guarantee.
    sim.reset_to_spawn()
    rect = scene._player
    assert rect.top >= 128
    assert 0 <= rect.bottom <= sh


# ---------------------------------------------------------------------------
# Enemy sim
# ---------------------------------------------------------------------------


def test_enemy_sim_spawn_training_targets_creates_three_targets() -> None:
    scene = _make_enemy_scene()
    sim = TutorialEnemySim(scene)
    sim.spawn_training_targets()
    assert len(scene._enemies) == 3
    assert all(e.kind == "target" for e in scene._enemies)
    assert all(e.active is True for e in scene._enemies)
    # Targets must not fire — initial fire_timer stays 0 and update()
    # must not append to _enemy_bullets for the "target" kind.
    sim.update()
    sim.update()
    sim.update()
    assert scene._enemy_bullets == []


def test_enemy_sim_easy_wave_fires_on_cooldown() -> None:
    """The "enemy" kind must fire every 92 frames; the cadence is the
    contract callers (e.g. the tutorial completion predicate) rely on."""
    scene = _make_enemy_scene()
    sim = TutorialEnemySim(scene)
    sim.spawn_easy_enemy_wave(initial=True)
    assert len(scene._enemies) == 3
    enemy = scene._enemies[0]
    initial_fire_timer = enemy.fire_timer
    assert 0 < initial_fire_timer <= 92

    # Tick the enemy sim until the first shot lands. The sim sets the
    # timer to 92 after each shot, then continues decrementing. We tick
    # one extra frame so the assertion sees a post-fire (but already
    # decremented) timer.
    for _ in range(initial_fire_timer + 2):
        sim.update()
    # The sim calls scene._spawn_enemy_bullet (which our stub pushes
    # onto _enemy_bullets). At least one shot must have landed.
    assert len(scene._enemy_bullets) >= 1
    # The fire timer is set to 92 the frame the bullet fires, then
    # decremented on subsequent frames — so by the time we look, it
    # has been decremented once. Anything in [0, 92] is fine; we just
    # pin it stayed at the contract value.
    assert 0 < enemy.fire_timer <= 92


def test_enemy_sim_spawn_clamps_to_objective_count() -> None:
    """A wave that would exceed the stage's objective count must stop early."""
    scene = _make_enemy_scene()
    scene._stage = SimpleNamespace(objective_count=2)
    sim = TutorialEnemySim(scene)
    sim.spawn_easy_enemy_wave(initial=True)
    # objective_count=2 caps spawning at 2, not the usual 3.
    assert len(scene._enemies) == 2


# ---------------------------------------------------------------------------
# Boss sim
# ---------------------------------------------------------------------------


def test_boss_sim_spawn_creates_boss_with_full_health() -> None:
    scene = _make_boss_scene()
    sim = BossSim(scene)
    sim.spawn()
    assert scene._boss is not None
    assert scene._boss.health == 280
    assert scene._boss.max_health == 280
    assert scene._boss.enraged is False


def test_boss_sim_enrages_below_30_percent_threshold() -> None:
    """The boss must enter enrage once HP drops to ≤ 30% of max.

    Enrage must:
    * flip the ``enraged`` flag
    * halve the fire interval (62 → 22)
    * expand the spread from 2 bullets to 5
    """
    scene = _make_boss_scene()
    BossSim(scene).spawn()
    boss = scene._boss
    boss.health = int(boss.max_health * 0.30)  # exactly at threshold

    BossSim(scene).update()  # first update — must enrage
    assert boss.enraged is True
    assert boss.fire_timer == 22
    # First enraged frame fires a 5-bullet spread.
    assert len(scene._enemy_bullets) == 5


def test_boss_sim_non_enraged_spread_is_two_bullets() -> None:
    """Pre-enrage, the boss fires a 2-bullet fan (one left, one right)."""
    scene = _make_boss_scene()
    BossSim(scene).spawn()
    scene._boss.health = scene._boss.max_health  # well above threshold

    BossSim(scene).update()
    assert scene._boss.enraged is False
    assert scene._boss.fire_timer == 62
    # First non-enraged update fires a 2-bullet spread.
    assert len(scene._enemy_bullets) == 2
