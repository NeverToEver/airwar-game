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


def test_render_does_not_mutate_shared_cache_alpha() -> None:
    """Two ParticleSystem instances share the class-level Flyweight cache.
    A render call in one instance must NOT mutate the cached surface in
    place — otherwise the next instance's render would blit with the wrong
    alpha (the previous instance's `set_alpha` call)."""
    system_a = ParticleSystem()
    system_b = ParticleSystem()
    surface = welcome_scene.pygame.Surface((64, 64))
    color = (255, 255, 255)

    # Force a known state then render. The shared cache surface must keep
    # full alpha (255) regardless of how many times either instance renders.
    system_a.render(surface, color)
    system_b.render(surface, color)
    system_a.render(surface, color)

    shared = ParticleSystem._texture_cache
    for (size, key), surf in shared.items():
        assert surf.get_alpha() == 255, (
            f"cache surface ({size}, {key}) was mutated in place to alpha "
            f"{surf.get_alpha()} — render() must `.copy()` before set_alpha"
        )


def test_cache_omits_dead_particle_alt_key() -> None:
    """`_init_cache` used to populate both `particle` and `particle_alt`
    surfaces, but the render path only ever reads `particle`. The alt key
    doubled the cache size for no behavioural gain."""
    system = ParticleSystem()
    keys = {k[1] for k in system._texture_cache}
    assert "particle_alt" not in keys
    assert "particle" in keys
