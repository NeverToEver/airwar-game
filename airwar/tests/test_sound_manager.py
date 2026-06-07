"""Unit tests for :mod:`airwar.audio.sound_manager`."""

from __future__ import annotations

import logging
from unittest.mock import patch

import pygame
import pytest

from airwar.audio.sound_manager import (
    SoundManager,
    _generate_beep,
    get_sound_manager,
    reset_sound_manager,
)


@pytest.fixture(autouse=True)
def _ensure_pygame_mixer():
    """Pygame + mixer must be live for most tests; conftest sets
    SDL_AUDIODRIVER=dummy so this is purely synthetic but valid."""
    if not pygame.get_init():
        pygame.init()
    if not pygame.mixer.get_init():
        pygame.mixer.init()
    return
    # No teardown — other tests in the same session rely on the
    # mixer staying initialized.


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Each test gets a fresh singleton so internal state is isolated."""
    reset_sound_manager()
    yield
    reset_sound_manager()


# ----------------------------------------------------------------------
# Init / failure
# ----------------------------------------------------------------------


def test_init_lazily_initializes_pygame_mixer():
    manager = SoundManager()
    assert manager.is_initialized() is False
    assert manager.init() is True
    assert manager.is_initialized() is True


def test_init_returns_false_when_mixer_init_fails():
    manager = SoundManager()
    # The conftest pre-initializes the mixer, so the SoundManager's
    # `if mixer is live, skip` short-circuit would bypass the patch.
    # Patch get_init to look uninitialized so the manager actually
    # calls mixer.init() (which then raises).
    with patch.object(pygame.mixer, "get_init", return_value=None), \
         patch.object(pygame.mixer, "init", side_effect=pygame.error("no device")):
        assert manager.init() is False
        assert manager.is_initialized() is False
    # Subsequent calls must remain no-ops and stay in failed state.
    assert manager.init() is False


def test_init_swallows_mixer_error_logged_as_warning(caplog):
    manager = SoundManager()
    with caplog.at_level(logging.WARNING, logger="airwar.audio.sound_manager"), \
         patch.object(pygame.mixer, "get_init", return_value=None), \
         patch.object(pygame.mixer, "init", side_effect=pygame.error("nope")):
        manager.init()
    assert any("mixer init failed" in rec.message for rec in caplog.records)


# ----------------------------------------------------------------------
# play_sfx
# ----------------------------------------------------------------------


def test_play_sfx_with_no_mixer_is_silent_noop():
    manager = SoundManager()
    # Mark init as failed (e.g. headless box) without touching mixer.
    manager._init_failed = True
    manager.play_sfx("bullet_fire")  # must not raise
    assert manager._sfx_cache == {}


def test_play_sfx_unknown_name_does_not_raise(caplog):
    manager = SoundManager()
    manager.init()
    with caplog.at_level(logging.DEBUG, logger="airwar.audio.sound_manager"):
        manager.play_sfx("definitely_not_a_real_sfx")
    assert "no implementation" in caplog.text


def test_play_sfx_bullet_fire_populates_cache():
    manager = SoundManager()
    manager.init()
    manager.play_sfx("bullet_fire")
    assert "bullet_fire" in manager._sfx_cache


# ----------------------------------------------------------------------
# BGM
# ----------------------------------------------------------------------


def test_bgm_api_noop_with_no_mixer():
    manager = SoundManager()
    manager._init_failed = True
    manager.play_bgm("main_theme.ogg")
    manager.stop_bgm()
    assert manager._bgm_track is None


def test_bgm_api_records_track_when_initialized():
    manager = SoundManager()
    manager.init()
    manager.play_bgm("title_screen.ogg", loop=True)
    assert manager._bgm_track == "title_screen.ogg"
    manager.stop_bgm()
    assert manager._bgm_track is None


# ----------------------------------------------------------------------
# Volume / mute
# ----------------------------------------------------------------------


def test_volume_default_and_setter_clamps():
    manager = SoundManager()
    assert manager.get_volume() == 0.6
    manager.set_volume(0.25)
    assert manager.get_volume() == 0.25
    manager.set_volume(1.5)
    assert manager.get_volume() == 1.0
    manager.set_volume(-0.3)
    assert manager.get_volume() == 0.0


def test_mute_toggle_flips_state():
    manager = SoundManager()
    assert manager.is_muted() is False
    assert manager.mute_toggle() is True
    assert manager.is_muted() is True
    assert manager.mute_toggle() is False


def test_mute_blocks_sfx_playback():
    manager = SoundManager()
    manager.init()
    manager.mute_toggle()  # mute on
    manager.play_sfx("bullet_fire")
    assert "bullet_fire" not in manager._sfx_cache


# ----------------------------------------------------------------------
# Procedural beep
# ----------------------------------------------------------------------


def test_generate_beep_returns_pygame_sound():
    sound = _generate_beep(frequency_hz=440.0, duration_ms=50, sample_rate=22050)
    assert isinstance(sound, pygame.mixer.Sound)
    # pygame.sndarray.make_sound resamples to the active mixer's
    # rate; the resulting buffer is at most the requested duration.
    # The conftest mixes at 44100 Hz, so 50ms ± a few ms is the
    # expected range.
    duration_ms = sound.get_length() * 1000
    assert 40 < duration_ms < 60


def test_generate_beep_does_not_clamp_full_amplitude():
    """A pure sine at full scale would clip — the generator scales to
    30000/32767 to leave headroom. Sanity check the headroom is
    present so downstream mixers are not pegged."""
    import numpy as np

    pcm = pygame.sndarray.samples(_generate_beep(440.0, 50, 22050))
    assert int(np.abs(pcm).max()) < 32767


# ----------------------------------------------------------------------
# Singleton
# ----------------------------------------------------------------------


def test_get_sound_manager_returns_singleton():
    a = get_sound_manager()
    b = get_sound_manager()
    assert a is b


def test_reset_sound_manager_returns_fresh_instance():
    a = get_sound_manager()
    a.init()
    b = reset_sound_manager()
    assert a is not b
    assert b.is_initialized() is False
