import pygame

from airwar.scenes.tutorial_scene import TutorialScene
from airwar.ui.base_talent_console import BaseTalentConsoleAction


def _make_scene() -> TutorialScene:
    pygame.init()
    scene = TutorialScene()
    scene.enter()
    return scene


def test_tutorial_aim_assist_locks_to_nearest_training_target() -> None:
    scene = _make_scene()

    target = scene._enemies[0]
    scene._set_raw_aim_position((40, 40))
    scene._update_aim_assist()

    assert scene._aim_assist_target is target
    assert scene._aim_pos == target.rect.center


def test_tutorial_aim_assist_releases_on_large_mouse_movement() -> None:
    scene = _make_scene()

    scene._set_raw_aim_position(scene._enemies[0].rect.center)
    scene._update_aim_assist()
    scene._set_raw_aim_position((
        scene._raw_aim_position[0] + scene.AIM_ASSIST_RELEASE_DISTANCE + 20,
        scene._raw_aim_position[1],
    ))
    scene._update_aim_assist()

    assert scene._aim_assist_target is None
    assert scene._aim_pos == scene._smoothed_raw_aim_position


def test_tutorial_player_fires_from_both_wings() -> None:
    scene = _make_scene()
    scene._fire_timer = 0
    scene._set_raw_aim_position(scene._enemies[0].rect.center)
    scene._update_aim_assist()

    scene._update_player_fire()

    assert len(scene._bullets) == 2
    assert scene._bullets[0].rect.center != scene._bullets[1].rect.center


def test_tutorial_boss_enrages_at_real_thirty_percent_threshold() -> None:
    scene = _make_scene()
    scene._load_stage(5)
    assert scene._boss is not None
    scene._boss.health = int(scene._boss.max_health * 0.30)

    scene._update_boss()

    assert scene._boss.enraged is True
    assert scene._boss.fire_timer == 22
    assert len(scene._enemy_bullets) == 5


def test_mothership_docking_runs_real_four_phase_flow() -> None:
    scene = _make_scene()
    scene._load_stage(3)
    scene._fade_phase = ""

    assert scene._dock_sub_phase == "approach"
    assert scene._mothership is not None
    assert scene._mothership._phantom_visible is True
    assert len(scene._enemies) == 3
    assert all(enemy.kind == "target" for enemy in scene._enemies)

    scene._keys_down.add(pygame.K_h)
    for _ in range(scene.DOCK_HOLD_FRAMES):
        scene._update_docking_stage()

    assert scene._dock_sub_phase == "entering"
    assert scene._docked is False
    assert scene._player_enter_timer == 0
    assert scene._mothership._phantom_visible is False

    enter_start_y = scene._player.centery
    for _ in range(scene.DOCK_ENTER_FRAMES // 2):
        scene._update_docking_stage()

    assert scene._dock_sub_phase == "entering"
    assert scene._player.centery < enter_start_y

    for _ in range(scene.DOCK_ENTER_FRAMES - scene.DOCK_ENTER_FRAMES // 2):
        scene._update_docking_stage()

    assert scene._dock_sub_phase == "docked"
    assert scene._docked is True
    assert scene._mothership_ammo == scene.MOTHERSHIP_STARTING_AMMO
    assert scene._player.center == scene._docking_player_center()
    assert scene._stage_completed is False

    scene._mothership_fire_timer = 0
    scene._update_docking_stage()

    assert scene._kills == 1
    assert len(scene._tutorial_explosions) == 1
    assert len([enemy for enemy in scene._enemies if enemy.active]) == 2
    assert scene._stage_progress == 0

    docked_center = scene._player.center
    scene._mothership_ammo = scene.MOTHERSHIP_AMMO_DRAIN
    scene._update_docking_stage()

    assert scene._dock_sub_phase == "eject_player"
    assert scene._dock_undock_phase == "player"
    assert scene._dock_undock_timer == scene._dock_undock_player_frames
    assert scene._docked is False
    assert scene._mothership.is_flyaway_mode() is False

    scene._update_docking_stage()

    assert scene._player.centery > docked_center[1]

    for _ in range(scene._dock_undock_player_frames):
        scene._update_docking_stage()
        if scene._dock_undock_phase == "mothership":
            break

    assert scene._dock_sub_phase == "eject_player"
    assert scene._dock_undock_phase == "mothership"
    assert scene._mothership.is_flyaway_mode() is True

    for _ in range(scene.DOCK_UNDOCK_FRAMES + 30):
        scene._update_docking_stage()
        scene._check_stage_completion()
        if scene._stage_completed:
            break

    assert scene._stage_completed is True
    assert scene._enemies == []


def test_homecoming_runs_combat_base_and_depart_phases() -> None:
    scene = _make_scene()
    scene._load_stage(4)
    scene._fade_phase = ""

    assert scene._base_sub_phase == "combat"
    assert len(scene._enemies) >= 3
    assert all(enemy.kind == "enemy" for enemy in scene._enemies)
    assert scene._player_health == scene._player_max_health
    assert scene._player_energy == scene.ENERGY_MAX

    scene._keys_down.add(pygame.K_b)
    for _ in range(scene.HOME_HOLD_FRAMES):
        scene._update_homecoming_stage()
    assert scene._pending_base_sub_phase == "base"
    for _ in range(scene.FADE_FRAMES + 4):
        scene._update_fade()

    assert scene._base_sub_phase == "base"
    assert scene._base_ready is True
    assert scene._enemies == []
    assert scene._base_game_controller is not None
    assert scene._base_game_controller.state.requisition_points == 10
    assert scene._stage_completed is False

    scene._handle_base_console_action(BaseTalentConsoleAction.resupply())
    assert scene._base_game_controller.state.requisition_points < 10

    scene._handle_base_console_action(BaseTalentConsoleAction.continue_sortie())
    assert scene._base_sub_phase == "depart"
    assert scene._depart_timer == scene.DEPART_FRAMES

    while scene._fade_phase == "out":
        scene._update_fade()
    scene._fade_phase = ""
    for _ in range(scene.DEPART_FRAMES):
        scene._update_homecoming_stage()
    scene._check_stage_completion()

    assert scene._stage_completed is True
