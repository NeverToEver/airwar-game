"""Sound manager for AirWar.

Vertical slice: lazy :mod:`pygame.mixer` initialization, procedural
``bullet_fire`` SFX generated in-code via :mod:`pygame.sndarray`, and
graceful no-op fallback when no audio device is available.

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
- **No shipped assets** — ``bullet_fire`` is generated procedurally so
  the game can run without a binary asset bundle.
"""

from __future__ import annotations

import logging
import math
from typing import ClassVar

import pygame

logger = logging.getLogger(__name__)

# Default sample rate matches pygame.mixer's default (44100 Hz, 16-bit,
# stereo). Mixed down to mono after generation to halve the buffer.
_DEFAULT_SAMPLE_RATE = 22050
_DEFAULT_SFX_DURATION_MS = 60
_BULLET_FIRE_DURATION_MS = 42
_BULLET_FIRE_FREQUENCY_HZ = 240.0
_BULLET_FIRE_GAIN = 0.28
_SFX_MIN_INTERVAL_MS = {
    "bullet_fire": 150,
}


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
        self._sfx_cache: dict[str, pygame.mixer.Sound | None] = {}
        self._sfx_last_play_ms: dict[str, int] = {}

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

        Currently only ``"bullet_fire"`` is implemented; it is generated
        procedurally on first use. Unknown names log at debug level and
        return without error.
        """
        if not self._ensure_init():
            return
        if self._muted:
            return

        sound: pygame.mixer.Sound | None
        if name in self._sfx_cache:
            sound = self._sfx_cache[name]
        else:
            sound = self._build_sfx(name)
            self._sfx_cache[name] = sound  # cache even if None to avoid retrying
        if sound is None:
            return
        min_interval_ms = _SFX_MIN_INTERVAL_MS.get(name, 0)
        if min_interval_ms > 0:
            now = pygame.time.get_ticks()
            last_play_ms = self._sfx_last_play_ms.get(name)
            if last_play_ms is not None and now - last_play_ms < min_interval_ms:
                return
            self._sfx_last_play_ms[name] = now
        sound.set_volume(self._volume)
        sound.play()

    def _build_sfx(self, name: str) -> pygame.mixer.Sound | None:
        """Generate (or look up) a sound for the given name."""
        if name == "bullet_fire":
            return _generate_beep(
                frequency_hz=_BULLET_FIRE_FREQUENCY_HZ,
                duration_ms=_BULLET_FIRE_DURATION_MS,
                sample_rate=_DEFAULT_SAMPLE_RATE,
                gain=_BULLET_FIRE_GAIN,
                harmonics=(1.0, 0.35),
            )
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
        for sound in self._sfx_cache.values():
            if sound is not None:
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
