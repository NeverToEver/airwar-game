"""Tests for Rust ↔ Python fallback boundary consistency (batch G)."""

from __future__ import annotations

import importlib
import struct
import sys
from types import ModuleType

import pytest

import airwar_core as rust_core
from airwar import core_bindings


@pytest.fixture
def restore_core_bindings():
    """Restore the real ``airwar_core`` and ``airwar.core_bindings`` after a test."""
    real_core = sys.modules.get("airwar_core")
    real_bindings = sys.modules.get("airwar.core_bindings")
    yield
    if real_core is not None:
        sys.modules["airwar_core"] = real_core
    if real_bindings is not None:
        sys.modules["airwar.core_bindings"] = real_bindings
        importlib.reload(core_bindings)


@pytest.fixture
def fallback_bindings(restore_core_bindings):
    """Provide ``airwar.core_bindings`` forced into pure-Python fallback mode."""
    fake = ModuleType("airwar_core")
    sys.modules["airwar_core"] = fake
    return importlib.reload(core_bindings)


class TestBulletIdType:
    """G1: bullet id type is i64 in both Rust and fallback."""

    def test_negative_id_roundtrip_rust_and_fallback(self, fallback_bindings):
        # -1 encoded as little-endian i64 occupies the same bytes as u64::MAX.
        buf = struct.pack("<qffffBxxxf", -1, 1.0, 2.0, 0.5, 0.5, 0, 1080.0)
        rust_result = rust_core.batch_update_bullets_buf(buf)
        fb_result = fallback_bindings.batch_update_bullets_buf(buf)
        assert rust_result == fb_result
        assert rust_result[0][0] == -1

    def test_positive_id_roundtrip_rust_and_fallback(self, fallback_bindings):
        buf = struct.pack("<qffffBxxxf", 42, 10.0, 20.0, 1.0, 2.0, 1, 1080.0)
        rust_result = rust_core.batch_update_bullets_buf(buf)
        fb_result = fallback_bindings.batch_update_bullets_buf(buf)
        assert rust_result == fb_result
        assert rust_result[0][0] == 42


class TestSpriteNonPositiveInput:
    """G2: non-positive sprite inputs return empty bytes in both paths."""

    @pytest.mark.parametrize(
        "func_name, kwargs",
        [
            ("create_single_bullet_glow", {"width": -5.0, "height": 10.0}),
            ("create_single_bullet_glow", {"width": 10.0, "height": -5.0}),
            ("create_single_bullet_glow", {"width": 0.0, "height": 10.0}),
            ("create_spread_bullet_glow", {"radius": -5.0}),
            ("create_spread_bullet_glow", {"radius": 0.0}),
            ("create_laser_bullet_glow", {"height": -5.0}),
            ("create_laser_bullet_glow", {"height": 0.0}),
            ("create_explosive_missile_glow", {"width": -5.0, "height": 10.0}),
            ("create_explosive_missile_glow", {"width": 10.0, "height": 0.0}),
            ("create_glow_circle", {"radius": -5, "r": 255, "g": 255, "b": 255, "glow_radius": 5}),
            ("create_glow_circle", {"radius": 5, "r": 255, "g": 255, "b": 255, "glow_radius": -1}),
            ("create_glow_circle", {"radius": 0, "r": 255, "g": 255, "b": 255, "glow_radius": 5}),
        ],
    )
    def test_rust_and_fallback_return_empty(self, fallback_bindings, func_name, kwargs):
        rust_func = getattr(rust_core, func_name)
        fb_func = getattr(fallback_bindings, func_name)
        assert rust_func(**kwargs) == b""
        assert fb_func(**kwargs) == b""


class TestColorClamping:
    """G3: out-of-range color components are clamped to [0, 255]."""

    def test_create_glow_circle_no_overflow(self, fallback_bindings):
        # Previously Rust raised OverflowError for values outside u8.
        rust_result = rust_core.create_glow_circle(10, 300, -10, 128, 2)
        fb_result = fallback_bindings.create_glow_circle(10, 300, -10, 128, 2)
        assert len(rust_result) > 0
        assert len(fb_result) > 0

    def test_batch_render_particles_color_clamped(self, fallback_bindings):
        particles = [(50.0, 50.0, 5.0, 2.0, 1.0, 300, -10, 128)]
        rust_result = rust_core.batch_render_particles(particles, 100, 100)
        fb_result = fallback_bindings.batch_render_particles(particles, 100, 100)
        assert rust_result == fb_result


class TestStarfieldNegativePhase:
    """G4: negative phase uses Euclidean modulo in both paths."""

    def test_negative_phase_matches_fallback(self, fallback_bindings):
        stars = [(0.5, 0.5, 2.0, 1.0, 1.0, 0.0)]
        sin_table = [0.0, 0.5, 1.0, 0.5]
        args = (stars, 0.0, 1920.0, 1080.0, -1.0, sin_table, 4, 3, 128, 2, 200)
        rust_result = rust_core.compute_starfield_positions(*args)
        fb_result = fallback_bindings.compute_starfield_positions(*args)
        assert rust_result == fb_result


class TestAbiMismatchFallback:
    """G5: signature mismatch causes core_bindings to fall back to pure Python."""

    def test_abi_mismatch_uses_fallback(self, restore_core_bindings):
        fake = ModuleType("airwar_core")
        for name in core_bindings._RUST_NAMES:
            # Present but with wrong arity -> ABI mismatch.
            setattr(fake, name, lambda *args, **kwargs: None)
        sys.modules["airwar_core"] = fake
        reloaded = importlib.reload(core_bindings)
        assert reloaded.RUST_AVAILABLE is False
