import pygame

from airwar.scenes.tutorial_scene import TutorialScene


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
