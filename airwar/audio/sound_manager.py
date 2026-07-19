"""Sound manager for AirWar.

Lazy :mod:`pygame.mixer` initialization, shipped ``bullet_fire`` laser
SFX (sfxr-style zap, round-robin variants) with a procedural fallback
generated in-code via :mod:`pygame.sndarray`, and graceful no-op
fallback when no audio device is available.

Design notes
------------
- **Lazy init** — ``pygame.mixer`` is only touched on the first audio
  call. Importing this module is side-effect free.
- **Failure tolerant** — if ``pygame.mixer.init()`` fails because no audio
  device is available, the manager logs
  a single warning and silently turns every public method into a
  no-op. Game logic must not depend on audio succeeding.
- **Global singleton** — :func:`get_sound_manager` returns the
  module-level instance.
- **Shipped assets with procedural fallback** — ``bullet_fire`` loads
  fixed WAV variants from ``airwar/assets/audio/`` (identical timbre on
  every platform); when the files are missing, the same zap recipe is
  synthesized at the mixer rate.
"""

from __future__ import annotations

import logging
import math
import os
from typing import ClassVar

import pygame

logger = logging.getLogger(__name__)

# Default sample rate matches pygame.mixer's default (44100 Hz, 16-bit,
# stereo). Mixed down to mono after generation to halve the buffer.
_DEFAULT_SAMPLE_RATE = 22050
_DEFAULT_SFX_DURATION_MS = 60
_BULLET_FIRE_DURATION_MS = 90
# Fallback gain matches the shipped WAV's 0.5 peak so asset and
# procedural paths have the same loudness.
_BULLET_FIRE_GAIN = 1.0
# sfxr "Laser/Shoot" recipe: exponential downward sweep with a short
# noise transient (mirrors scripts/generate_bullet_fire_wav.py).
_BULLET_FIRE_START_HZ = 760.0
_BULLET_FIRE_END_HZ = 170.0
_BULLET_FIRE_NOISE_MS = 5.0
_BULLET_FIRE_NOISE_GAIN = 0.25
_SFX_MIN_INTERVAL_MS = {
    "bullet_fire": 150,
}

# Shipped bullet_fire variants, cycled round-robin so consecutive shots
# never sound identical (anti repetition-fatigue at ~7 shots/sec).
_ASSETS_AUDIO_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "audio")
_BULLET_FIRE_FILES = ("bullet_fire.wav", "bullet_fire_b.wav", "bullet_fire_c.wav")


class SoundManager:
    """Manages SFX playback and BGM channel state.

    All public methods are safe to call even when audio init failed;
    they degrade to silent no-ops.
    """

    _singleton: ClassVar[SoundManager | None] = None

    def __init__(self) -> None:
        self._initialized: bool = False
        self._init_failed: bool = False
        self._volume: float = 0.6
        self._muted: bool = False
        self._sfx_cache: dict[str, pygame.mixer.Sound | list[pygame.mixer.Sound] | None] = {}
        self._sfx_last_play_ms: dict[str, int] = {}
        # Round-robin cursors for SFX that ship multiple variants.
        self._sfx_variant_idx: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def init(self) -> bool:
        """Lazily initialize :mod:`pygame.mixer`.

        Returns ``True`` when audio is usable, ``False`` when init
        failed (subsequent calls become no-ops).
        """
        if self._initialized or self._init_failed:
            return self._initialized

        # The OS selects the default audio driver unless the user overrides it.
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except pygame.error as exc:
            logger.warning("pygame.mixer init failed; audio disabled: %s", exc)
            self._init_failed = True
            return False

        self._initialized = True
        self._apply_volume()
        return True

    def _ensure_init(self) -> bool:
        """Internal helper: init if needed, return success flag."""
        if self._initialized:
            return True
        if self._init_failed:
            return False
        return self.init()

    # ------------------------------------------------------------------
    # SFX
    # ------------------------------------------------------------------

    def play_sfx(self, name: str) -> None:
        """Play a short SFX by name.

        ``"bullet_fire"`` ships as multiple WAV variants cycled
        round-robin. Unknown names log at debug level and return
        without error.
        """
        if not self._ensure_init():
            return
        if self._muted:
            return

        entry: pygame.mixer.Sound | list[pygame.mixer.Sound] | None
        if name in self._sfx_cache:
            entry = self._sfx_cache[name]
        else:
            entry = self._build_sfx(name)
            self._sfx_cache[name] = entry  # cache even if None to avoid retrying
        if entry is None:
            return
        if isinstance(entry, list):
            if not entry:
                return
            idx = self._sfx_variant_idx.get(name, 0) % len(entry)
            self._sfx_variant_idx[name] = idx + 1
            sound = entry[idx]
        else:
            sound = entry
        min_interval_ms = _SFX_MIN_INTERVAL_MS.get(name, 0)
        if min_interval_ms > 0:
            now = pygame.time.get_ticks()
            last_play_ms = self._sfx_last_play_ms.get(name)
            if last_play_ms is not None and now - last_play_ms < min_interval_ms:
                return
            self._sfx_last_play_ms[name] = now
        sound.set_volume(self._volume)
        sound.play()

    def _build_sfx(self, name: str) -> pygame.mixer.Sound | list[pygame.mixer.Sound] | None:
        """Generate (or look up) a sound for the given name."""
        if name == "bullet_fire":
            variants = self._load_bullet_fire_variants()
            if variants:
                return variants
            zap = _generate_laser_zap(
                start_hz=_BULLET_FIRE_START_HZ,
                end_hz=_BULLET_FIRE_END_HZ,
                duration_ms=_BULLET_FIRE_DURATION_MS,
                sample_rate=_DEFAULT_SAMPLE_RATE,
                gain=_BULLET_FIRE_GAIN,
            )
            return [zap] if zap is not None else None
        if name == "player_hit":
            # Low, long beep on player damage — feedback for the hit-stop +
            # damage_intensity flash. 110 Hz (A2) is harsh and noticeable.
            return _generate_beep(
                frequency_hz=110.0,
                duration_ms=180,
                sample_rate=_DEFAULT_SAMPLE_RATE,
            )
        logger.debug("SFX %r has no implementation; ignoring", name)
        return None

    def _load_bullet_fire_variants(self) -> list[pygame.mixer.Sound]:
        """Load the shipped bullet_fire WAV variants (empty list if absent)."""
        sounds: list[pygame.mixer.Sound] = []
        for filename in _BULLET_FIRE_FILES:
            path = os.path.join(_ASSETS_AUDIO_DIR, filename)
            if not os.path.isfile(path):
                continue
            try:
                sounds.append(pygame.mixer.Sound(path))
            except pygame.error:
                logger.warning("Failed to load SFX asset %s", path)
        if sounds and len(sounds) < len(_BULLET_FIRE_FILES):
            logger.info("Loaded %d/%d bullet_fire variants", len(sounds), len(_BULLET_FIRE_FILES))
        return sounds

    # ------------------------------------------------------------------
    # Volume / mute
    # ------------------------------------------------------------------

    def set_volume(self, volume: float) -> None:
        """Set master volume in ``[0.0, 1.0]``. Out-of-range values clamp."""
        self._volume = max(0.0, min(1.0, float(volume)))
        if self._initialized:
            self._apply_volume()

    def get_volume(self) -> float:
        """Return the current master volume in ``[0.0, 1.0]``."""
        return self._volume

    def _apply_volume(self) -> None:
        """Push current volume to all cached sounds."""
        for entry in self._sfx_cache.values():
            if entry is None:
                continue
            sounds = entry if isinstance(entry, list) else [entry]
            for sound in sounds:
                sound.set_volume(self._volume)

    def mute_toggle(self) -> bool:
        """Flip the muted flag. Returns the new muted state."""
        self._muted = not self._muted
        if self._initialized and self._muted:
            # Stop any in-flight SFX on mute-on.
            pygame.mixer.stop()
        logger.debug("Audio muted=%s", self._muted)
        return self._muted

    def is_muted(self) -> bool:
        """Return whether audio is currently muted."""
        return self._muted

# ----------------------------------------------------------------------
# Module-level singleton
# ----------------------------------------------------------------------


def get_sound_manager() -> SoundManager:
    """Return the module-level :class:`SoundManager` singleton."""
    if SoundManager._singleton is None:
        SoundManager._singleton = SoundManager()
    return SoundManager._singleton


# ----------------------------------------------------------------------
# Procedural SFX
# ----------------------------------------------------------------------


def _generate_beep(
    frequency_hz: float,
    duration_ms: int,
    sample_rate: int,
    *,
    gain: float = 1.0,
    harmonics: tuple[float, ...] = (1.0,),
) -> pygame.mixer.Sound | None:
    """Build a short sine-wave tone as a :class:`pygame.mixer.Sound`.

    Applies a linear attack/release envelope so the click at frame 0
    does not produce an audible pop. Channel layout matches the
    currently-initialized mixer (mono or stereo).

    Returns ``None`` when ``numpy`` is not installed (SFX are optional).
    """
    try:
        import numpy as np  # local import: numpy is not required for core game
    except ImportError:
        return None

    # pygame.sndarray hands the buffer to the mixer without resampling;
    # to land on the requested duration we must match the mixer's
    # playback rate, not pick an arbitrary one.
    mixer_info = pygame.mixer.get_init()
    mixer_rate = mixer_info[0] if mixer_info is not None else sample_rate
    mixer_channels = mixer_info[2] if mixer_info is not None else 2

    n_samples = int(mixer_rate * duration_ms / 1000)
    t = np.arange(n_samples, dtype=np.float32) / mixer_rate
    wave = np.zeros_like(t)
    harmonic_weight = 0.0
    for multiplier, amplitude in enumerate(harmonics, start=1):
        wave += amplitude * np.sin(2.0 * math.pi * frequency_hz * multiplier * t)
        harmonic_weight += abs(amplitude)
    if harmonic_weight > 0.0:
        wave /= harmonic_weight

    # 5ms attack + release envelope to avoid pops.
    env_n = max(1, int(mixer_rate * 0.005))
    envelope = np.ones_like(wave)
    envelope[:env_n] = np.linspace(0.0, 1.0, env_n)
    envelope[-env_n:] = np.linspace(1.0, 0.0, env_n)
    wave *= envelope

    # Scale to int16 range with a small headroom.
    pcm = np.clip(wave * 30000 * max(0.0, gain), -32768, 32767).astype(np.int16)

    # Match the mixer's channel layout. pygame.sndarray.make_sound
    # rejects arrays whose second dim does not equal the mixer's
    # channel count (e.g. stereo mixer requires shape (n, 2)).
    if mixer_channels <= 1:
        return pygame.sndarray.make_sound(pcm)
    return pygame.sndarray.make_sound(np.stack([pcm] * mixer_channels, axis=-1))


def _generate_laser_zap(
    start_hz: float,
    end_hz: float,
    duration_ms: int,
    sample_rate: int,
    *,
    gain: float = 1.0,
    noise_ms: float = _BULLET_FIRE_NOISE_MS,
    noise_gain: float = _BULLET_FIRE_NOISE_GAIN,
) -> pygame.mixer.Sound | None:
    """Procedural fallback for the shipped ``bullet_fire`` WAV.

    Mirrors the recipe in ``scripts/generate_bullet_fire_wav.py``
    (sfxr-style "Laser/Shoot"): square-wave carrier with an exponential
    downward pitch sweep, 2ms attack + exponential decay envelope, and
    a short white-noise transient. Generated at the mixer playback rate
    so the pitch is correct on every platform.

    Returns ``None`` when ``numpy`` is not installed (SFX are optional).
    """
    try:
        import numpy as np  # local import: numpy is not required for core game
    except ImportError:
        return None

    mixer_info = pygame.mixer.get_init()
    mixer_rate = mixer_info[0] if mixer_info is not None else sample_rate
    mixer_channels = mixer_info[2] if mixer_info is not None else 2

    n = int(mixer_rate * duration_ms / 1000)
    t = np.arange(n, dtype=np.float64) / mixer_rate
    total = n / mixer_rate

    # Exponential sweep: f(t) = f0 * ratio**(t/T); phase is its integral.
    ratio = end_hz / start_hz
    phase = 2.0 * math.pi * start_hz * total / math.log(ratio) * (np.power(ratio, t / total) - 1.0)
    cycles = phase / (2.0 * math.pi)
    wave = np.where(cycles % 1.0 < 0.5, 1.0, -1.0)

    # 2ms attack + exponential decay envelope.
    envelope = np.exp(-t / (total * 0.32))
    attack_n = max(1, int(mixer_rate * 0.002))
    envelope[:attack_n] *= np.linspace(0.0, 1.0, attack_n)
    wave *= envelope

    # Noise transient for the attack crack.
    noise_n = int(mixer_rate * noise_ms / 1000)
    if noise_n > 0 and noise_gain > 0:
        rng = np.random.default_rng(20260719)
        noise = rng.uniform(-1.0, 1.0, noise_n) * np.linspace(1.0, 0.0, noise_n)
        wave[:noise_n] += noise_gain * noise

    # Peak-normalize, then scale to int16 with headroom.
    max_abs = np.max(np.abs(wave))
    if max_abs > 0:
        wave = wave / max_abs
    pcm = np.clip(wave * 0.5 * 32767 * max(0.0, gain), -32768, 32767).astype(np.int16)

    if mixer_channels <= 1:
        return pygame.sndarray.make_sound(pcm)
    return pygame.sndarray.make_sound(np.stack([pcm] * mixer_channels, axis=-1))
