"""P3 regression tests: shipped bullet_fire laser SFX.

Covers the WAV asset contract (44100 Hz / 16-bit / mono), the
file-first / procedural-fallback build path, and the round-robin
variant cycling that fights repetition fatigue at ~7 shots/sec.
"""

import os
import wave
from types import SimpleNamespace

import pygame
import pytest

from airwar.audio import sound_manager as sm

ASSETS_AUDIO_DIR = os.path.join(os.path.dirname(sm.__file__), "..", "assets", "audio")


class TestBulletFireAssets:
    @pytest.mark.parametrize("filename", sm._BULLET_FIRE_FILES)
    def test_wav_exists_with_expected_format(self, filename):
        path = os.path.join(ASSETS_AUDIO_DIR, filename)
        assert os.path.isfile(path), f"missing shipped asset: {path}"
        with wave.open(path) as fh:
            assert fh.getframerate() == 44100
            assert fh.getnchannels() == 1
            assert fh.getsampwidth() == 2  # 16-bit
            duration_ms = fh.getnframes() / fh.getframerate() * 1000
            assert 50 <= duration_ms <= 150  # short zap, not a droning beep


@pytest.fixture()
def _mixer(monkeypatch):
    """Ensure pygame.mixer is initialized (dummy driver headless)."""
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    if not pygame.mixer.get_init():
        pygame.mixer.init()
    return pygame.mixer


class TestBulletFireBuildPath:
    def test_loads_shipped_wav_variants(self, _mixer):
        manager = sm.SoundManager()
        variants = manager._load_bullet_fire_variants()
        assert len(variants) == len(sm._BULLET_FIRE_FILES)
        assert all(isinstance(s, pygame.mixer.Sound) for s in variants)

    def test_build_sfx_prefers_shipped_files(self, _mixer):
        manager = sm.SoundManager()
        entry = manager._build_sfx("bullet_fire")
        assert isinstance(entry, list)
        assert len(entry) == len(sm._BULLET_FIRE_FILES)

    def test_build_sfx_falls_back_to_procedural_when_files_missing(self, _mixer, monkeypatch, tmp_path):
        monkeypatch.setattr(sm, "_ASSETS_AUDIO_DIR", str(tmp_path))
        manager = sm.SoundManager()
        entry = manager._build_sfx("bullet_fire")
        assert isinstance(entry, list)
        assert len(entry) == 1
        assert isinstance(entry[0], pygame.mixer.Sound)


class _FakeSound:
    def __init__(self, log, tag):
        self._log = log
        self._tag = tag

    def set_volume(self, volume):
        pass

    def play(self):
        self._log.append(self._tag)


class TestRoundRobin:
    def _manager(self, monkeypatch, variants, now):
        manager = sm.SoundManager()
        manager._initialized = True  # bypass mixer
        monkeypatch.setattr(pygame.time, "get_ticks", lambda: now[0])
        manager._sfx_cache["bullet_fire"] = variants
        return manager

    def test_variants_cycle_round_robin(self, monkeypatch):
        plays = []
        now = [0]
        manager = self._manager(
            monkeypatch,
            [_FakeSound(plays, "a"), _FakeSound(plays, "b"), _FakeSound(plays, "c")],
            now,
        )
        for _ in range(4):
            manager.play_sfx("bullet_fire")
            now[0] += 200  # beyond the 150ms min interval
        assert plays == ["a", "b", "c", "a"]

    def test_min_interval_suppresses_rapid_fire(self, monkeypatch):
        plays = []
        now = [0]
        manager = self._manager(monkeypatch, [_FakeSound(plays, "a")], now)
        manager.play_sfx("bullet_fire")
        now[0] += 50  # within the 150ms min interval
        manager.play_sfx("bullet_fire")
        assert plays == ["a"]

    def test_apply_volume_handles_variant_lists(self):
        manager = sm.SoundManager()
        volumes = []
        fake = SimpleNamespace(set_volume=lambda v: volumes.append(v))
        manager._sfx_cache["bullet_fire"] = [fake, fake]
        manager._sfx_cache["player_hit"] = fake
        manager._volume = 0.3
        manager._apply_volume()
        assert volumes == [0.3, 0.3, 0.3]
