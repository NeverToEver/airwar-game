from airwar.scenes import welcome_scene


ParticleSystem = welcome_scene.ParticleSystem


def test_texture_size_maps_small_to_first_bucket() -> None:
    assert ParticleSystem._texture_size_for_particle(1) == 2
    assert ParticleSystem._texture_size_for_particle(2) == 2


def test_texture_size_maps_mid_to_correct_bucket() -> None:
    assert ParticleSystem._texture_size_for_particle(3) == 3
    assert ParticleSystem._texture_size_for_particle(4) == 4
    assert ParticleSystem._texture_size_for_particle(5) == 6
    assert ParticleSystem._texture_size_for_particle(6) == 6
    assert ParticleSystem._texture_size_for_particle(7) == 8
    assert ParticleSystem._texture_size_for_particle(8) == 8


def test_texture_size_maps_large_to_last_bucket() -> None:
    assert ParticleSystem._texture_size_for_particle(12) == 12
    assert ParticleSystem._texture_size_for_particle(16) == 16
    assert ParticleSystem._texture_size_for_particle(20) == 20


def test_texture_size_oversized_falls_back_to_max() -> None:
    assert ParticleSystem._texture_size_for_particle(21) == 20
    assert ParticleSystem._texture_size_for_particle(100) == 20


def test_texture_size_zero_falls_back_to_first_bucket() -> None:
    assert ParticleSystem._texture_size_for_particle(0) == 2
