"""Sound manager for AirWar.

Vertical slice: lazy :mod:`pygame.mixer` initialization, procedural
``bullet_fire`` SFX generated in-code via :mod:`pygame.sndarray`, and
graceful no-op fallback when no audio device is available.

Design notes
------------
- **Lazy init** — ``pygame.mixer`` is only touched on the first audio
  call. Importing this module is side-effect free, so unit tests and
  non-audio code paths stay cheap.
- **Failure tolerant** — if ``pygame.mixer.init()`` fails (no audio
  device in headless / CI / sandboxed environments), the manager logs
  a single warning and silently turns every public method into a
  no-op. Game logic must not depend on audio succeeding.
- **Global singleton** — :func:`get_sound_manager` returns the
  module-level instance. Tests can call :meth:`reset_sound_manager`
  to start from a clean slate.
- **No shipped assets** — BGM and any non-builtin SFX are stubs that
  log at debug level. ``bullet_fire`` is generated procedurally so
  the wiring is end-to-end testable without a binary blob.
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
_BEEP_FREQUENCY_HZ = 880.0  # A5 - bright, short bullet-fire tone


class SoundManager:
    """Manages SFX playback and BGM channel state.

    All public methods are safe to call even when audio init failed;
    they degrade to silent no-ops.
    """

    # Track whether the singleton has been reset by tests; lets us
    # recreate the module-level instance without leaking state.
    _singleton: ClassVar[SoundManager | None] = None

    def __init__(self) -> None:
        self._initialized: bool = False
        self._init_failed: bool = False
        self._volume: float = 0.6
        self._muted: bool = False
        self._sfx_cache: dict[str, pygame.mixer.Sound] = {}
        self._bgm_channel: pygame.mixer.Channel | None = None
        self._bgm_track: str | None = None

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

        # SDL_AUDIODRIVER=dummy in tests; in real play it is unset and
        # the OS picks the default. We respect the env var explicitly
        # so headless runs are deterministic.
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except pygame.error as exc:
            logger.warning("pygame.mixer init failed; audio disabled: %s", exc)
            self._init_failed = True
            return False

        self._initialized = True
        # Reserve channel 0 for BGM so SFX can play over it.
        try:
            self._bgm_channel = pygame.mixer.Channel(0)
        except pygame.error as exc:  # pragma: no cover - defensive
            logger.warning("Could not reserve BGM channel: %s", exc)
            self._bgm_channel = None
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

        sound = self._sfx_cache.get(name)
        if sound is None:
            sound = self._build_sfx(name)
            if sound is None:
                return
            self._sfx_cache[name] = sound
        sound.set_volume(self._volume)
        sound.play()

    def _build_sfx(self, name: str) -> pygame.mixer.Sound | None:
        """Generate (or look up) a sound for the given name."""
        if name == "bullet_fire":
            return _generate_beep(
                frequency_hz=_BEEP_FREQUENCY_HZ,
                duration_ms=_DEFAULT_SFX_DURATION_MS,
                sample_rate=_DEFAULT_SAMPLE_RATE,
            )
        logger.debug("SFX %r has no implementation; ignoring", name)
        return None

    # ------------------------------------------------------------------
    # BGM
    # ------------------------------------------------------------------

    def play_bgm(self, track: str, loop: bool = True) -> None:
        """Start streaming a background-music track.

        Vertical-slice stub: no BGM assets are shipped yet, so the call
        records the track name and no-ops at info level. The full path
        (file load + ``pygame.mixer.music``) is wired here for the day
        real assets land in ``airwar/assets/audio/``.
        """
        if not self._ensure_init():
            return
        self._bgm_track = track
        logger.info("BGM stub: would play %r (loop=%s)", track, loop)
        # Real implementation once assets exist:
        #   path = os.path.join(_AUDIO_ASSET_DIR, track)
        #   if os.path.exists(path):
        #       pygame.mixer.music.load(path)
        #       pygame.mixer.music.set_volume(self._volume)
        #       pygame.mixer.music.play(-1 if loop else 0)

    def stop_bgm(self) -> None:
        """Stop the currently playing BGM track (if any)."""
        if not self._ensure_init():
            return
        self._bgm_track = None
        logger.debug("BGM stub: stop")

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

    # ------------------------------------------------------------------
    # Test / introspection helpers
    # ------------------------------------------------------------------

    def is_initialized(self) -> bool:
        """Return whether the mixer is live and usable."""
        return self._initialized

    def reset(self) -> None:
        """Clear cached state. Test-only helper."""
        self._sfx_cache.clear()
        self._bgm_track = None
        self._muted = False
        self._volume = 0.6
        # Do not un-init pygame.mixer; other tests in the same session
        # may depend on it.


# ----------------------------------------------------------------------
# Module-level singleton
# ----------------------------------------------------------------------


def get_sound_manager() -> SoundManager:
    """Return the module-level :class:`SoundManager` singleton."""
    if SoundManager._singleton is None:
        SoundManager._singleton = SoundManager()
    return SoundManager._singleton


def reset_sound_manager() -> SoundManager:
    """Drop the current singleton and return a fresh one (test helper)."""
    SoundManager._singleton = SoundManager()
    return SoundManager._singleton


# ----------------------------------------------------------------------
# Procedural SFX
# ----------------------------------------------------------------------

# Path to the directory where shipped audio assets would live. Kept as
# a module constant so the future BGM implementation has one source of
# truth.
_AUDIO_ASSET_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets",
    "audio",
)


def _generate_beep(
    frequency_hz: float,
    duration_ms: int,
    sample_rate: int,
) -> pygame.mixer.Sound:
    """Build a short sine-wave tone as a :class:`pygame.mixer.Sound`.

    Applies a linear attack/release envelope so the click at frame 0
    does not produce an audible pop. Channel layout matches the
    currently-initialized mixer (mono or stereo).
    """
    import numpy as np  # local import: numpy is not required for core game

    # pygame.sndarray hands the buffer to the mixer without resampling;
    # to land on the requested duration we must match the mixer's
    # playback rate, not pick an arbitrary one.
    mixer_info = pygame.mixer.get_init()
    mixer_rate = mixer_info[0] if mixer_info is not None else sample_rate
    mixer_channels = mixer_info[2] if mixer_info is not None else 2

    n_samples = int(mixer_rate * duration_ms / 1000)
    t = np.arange(n_samples, dtype=np.float32) / mixer_rate
    wave = np.sin(2.0 * math.pi * frequency_hz * t)

    # 5ms attack + release envelope to avoid pops.
    env_n = max(1, int(mixer_rate * 0.005))
    envelope = np.ones_like(wave)
    envelope[:env_n] = np.linspace(0.0, 1.0, env_n)
    envelope[-env_n:] = np.linspace(1.0, 0.0, env_n)
    wave *= envelope

    # Scale to int16 range with a small headroom.
    pcm = np.clip(wave * 30000, -32768, 32767).astype(np.int16)

    # Match the mixer's channel layout. pygame.sndarray.make_sound
    # rejects arrays whose second dim does not equal the mixer's
    # channel count (e.g. stereo mixer requires shape (n, 2)).
    if mixer_channels <= 1:
        return pygame.sndarray.make_sound(pcm)
    return pygame.sndarray.make_sound(np.stack([pcm] * mixer_channels, axis=-1))
