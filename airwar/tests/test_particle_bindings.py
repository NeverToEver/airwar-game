"""Tests for Rust particle bindings"""
import pytest
from airwar.core_bindings import (
    update_particle,
    batch_update_particles,
    generate_explosion_particles,
    RUST_AVAILABLE,
)


@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust core not available")
class TestUpdateParticle:
    def test_update_particle_moves(self):
        x, y, vx, vy, life, alpha = update_particle(0.0, 0.0, 10.0, 10.0, 30, 30, 3.0, 1.0)
        assert x > 0.0
        assert y > 0.0
        assert vx < 10.0  # dampened
        assert vy < 10.0
        assert life == 29
        assert 0.0 < alpha <= 1.0

    def test_update_particle_alpha_calculation(self):
        x, y, vx, vy, life, alpha = update_particle(0.0, 0.0, 1.0, 1.0, 10, 20, 2.0, 1.0)
        assert life == 9  # life is decremented first
        assert abs(alpha - 0.45) < 0.01  # 9/20 after decrement

    def test_update_particle_zero_max_life(self):
        x, y, vx, vy, life, alpha = update_particle(0.0, 0.0, 1.0, 1.0, 10, 0, 2.0, 1.0)
        assert alpha == 0.0  # avoid division by zero


@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust core not available")
class TestBatchUpdateParticles:
    def test_batch_update_filters_dead(self):
        particles = [
            (0.0, 0.0, 1.0, 1.0, 30, 30, 3.0),
            (10.0, 10.0, 1.0, 1.0, 1, 30, 3.0),  # dies (life becomes 0)
            (20.0, 20.0, 1.0, 1.0, 30, 30, 3.0),
        ]
        results = batch_update_particles(particles, 1.0)
        # Now returns all particles with is_alive flag, Python filters
        alive_count = sum(1 for r in results if r[-1])  # is_alive is last element
        assert alive_count == 2

    def test_batch_update_preserves_alive(self):
        particles = [
            (0.0, 0.0, 1.0, 1.0, 30, 30, 3.0),
            (10.0, 10.0, 1.0, 1.0, 2, 30, 3.0),  # survives
        ]
        results = batch_update_particles(particles, 1.0)
        assert len(results) == 2

    def test_batch_update_empty_input(self):
        results = batch_update_particles([], 1.0)
        assert len(results) == 0


@pytest.mark.skipif(not RUST_AVAILABLE, reason="Rust core not available")
class TestGenerateExplosionParticles:
    def test_generate_explosion_count(self):
        particles = generate_explosion_particles(100.0, 200.0, 30, 20, 40, 3.0, 8.0, 2.0, 5.0)
        assert len(particles) == 30

    def test_generate_explosion_center(self):
        particles = generate_explosion_particles(100.0, 200.0, 10, 20, 40, 3.0, 8.0, 2.0, 5.0)
        for p in particles:
            x, y, vx, vy, life, max_life, size = p
            assert abs(x - 100.0) < 0.1
            assert abs(y - 200.0) < 0.1

    def test_generate_explosion_life_range(self):
        particles = generate_explosion_particles(0.0, 0.0, 50, 20, 40, 3.0, 8.0, 2.0, 5.0)
        for p in particles:
            _, _, _, _, life, max_life, size = p
            assert 20 <= life <= 40
            assert life == max_life
            assert 2.0 <= size <= 5.0

    def test_generate_explosion_zero_count(self):
        particles = generate_explosion_particles(0.0, 0.0, 0, 20, 40, 3.0, 8.0, 2.0, 5.0)
        assert len(particles) == 0
