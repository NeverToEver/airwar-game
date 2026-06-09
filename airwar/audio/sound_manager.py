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

import io
import logging
import math
import os
from typing import IO, ClassVar, cast

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
        self._bgm_track: str | None = None
        self._bgm_volume: float = 0.5

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
    # BGM
    # ------------------------------------------------------------------

    def play_bgm(self, track: str, loop: bool = True) -> None:
        """Start streaming a background-music track.

        Uses :mod:`pygame.mixer.music` to loop a stream. Real audio
        files are looked up under ``airwar/assets/audio/``; when none is
        shipped for ``track`` we synthesise a short sine-wave loop into
        an in-memory WAV buffer and stream that, so the wiring is
        end-to-end testable without binary assets.

        On init failure, an unknown track that cannot be synthesised, or
        any mixer error, the call degrades to a no-op and ``_bgm_track``
        is left as ``None`` so callers can introspect failure.
        """
        if not self._ensure_init():
            return
        if self._muted:
            # Honour the mute toggle: refuse to start a new track while
            # muted. The previous track (if any) was already stopped by
            # ``mute_toggle`` / ``set_volume``.
            self._bgm_track = None
            return

        stream = _resolve_bgm_stream(track)
        if stream is None:
            logger.debug("BGM %r has no implementation; ignoring", track)
            return

        # ``pygame.mixer.music.load`` accepts a path-like or file-like input.
        # The resolver above returns ``io.IOBase | str``; mypy --strict sees
        # the union as incompatible with the stub's ``FileArg`` alias (which
        # expects ``IO[bytes] | IO[str]`` for the stream branch), so cast to
        # a ``Union[str, IO[bytes]]`` that matches what the stub actually
        # accepts at runtime.
        load_arg: str | IO[bytes] = cast("str | IO[bytes]", stream)
        try:
            pygame.mixer.music.load(load_arg)
            pygame.mixer.music.set_volume(self._bgm_volume)
            pygame.mixer.music.play(-1 if loop else 0)
        except pygame.error as exc:
            logger.warning("BGM %r failed to play: %s", track, exc)
            return

        self._bgm_track = track
        logger.info("BGM playing %r (loop=%s)", track, loop)

    def stop_bgm(self) -> None:
        """Stop the currently playing BGM track (if any)."""
        if self._bgm_track is None:
            return
        if self._initialized:
            try:
                pygame.mixer.music.stop()
            except pygame.error as exc:
                logger.debug("BGM stop failed: %s", exc)
        self._bgm_track = None

    def set_bgm_volume(self, volume: float) -> None:
        """Set BGM channel volume in ``[0.0, 1.0]``. Out-of-range clamps."""
        self._bgm_volume = max(0.0, min(1.0, float(volume)))
        if self._initialized:
            try:
                pygame.mixer.music.set_volume(self._bgm_volume)
            except pygame.error as exc:
                logger.debug("BGM set_volume failed: %s", exc)

    def get_bgm_volume(self) -> float:
        """Return the current BGM channel volume in ``[0.0, 1.0]``."""
        return self._bgm_volume

    def get_bgm_track(self) -> str | None:
        """Return the currently playing BGM track name, or ``None``."""
        return self._bgm_track

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
        self._bgm_volume = 0.5
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

# Length of the synthesised BGM loop in milliseconds. Short enough to
# keep the in-memory WAV buffer tiny (< 20 KB) and long enough that the
# loop seam is not obvious at low frequency.
_BGM_LOOP_DURATION_MS = 2000
_BGM_LOOP_SAMPLE_RATE = 22050


def _resolve_bgm_stream(track: str) -> io.IOBase | str | None:
    """Return a file-like object (or path) suitable for ``music.load``.

    Tries, in order:
    1. ``airwar/assets/audio/<track>`` on disk.
    2. An in-memory WAV synthesised from a deterministic sine wave
       keyed off ``track`` so different track names sound different.

    Returns ``None`` when neither path produces a usable stream.
    """
    candidate = os.path.join(_AUDIO_ASSET_DIR, track)
    if os.path.isfile(candidate):
        return candidate

    return _synthesise_bgm_wav(track)


def _synthesise_bgm_wav(track: str) -> io.BytesIO | None:
    """Build a 2-second looping WAV in memory for the given track name."""
    import wave

    import numpy as np  # local import: numpy is not required for core game

    frequency_hz = _track_frequency(track)
    if frequency_hz is None:
        return None

    n_samples = int(_BGM_LOOP_SAMPLE_RATE * _BGM_LOOP_DURATION_MS / 1000)
    t = np.arange(n_samples, dtype=np.float32) / _BGM_LOOP_SAMPLE_RATE
    # Layer the carrier with a soft sub-octave so the loop has a touch
    # of musicality rather than a flat tone.
    wave_data = 0.6 * np.sin(2.0 * math.pi * frequency_hz * t) + 0.3 * np.sin(2.0 * math.pi * frequency_hz * 0.5 * t)
    # 10 ms fade-in/out at the loop seam to avoid clicks.
    env_n = max(1, int(_BGM_LOOP_SAMPLE_RATE * 0.010))
    envelope = np.ones_like(wave_data)
    envelope[:env_n] = np.linspace(0.0, 1.0, env_n)
    envelope[-env_n:] = np.linspace(1.0, 0.0, env_n)
    wave_data *= envelope

    pcm = np.clip(wave_data * 20000, -32768, 32767).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(_BGM_LOOP_SAMPLE_RATE)
        wf.writeframes(pcm.tobytes())
    buf.seek(0)
    return buf


def _track_frequency(track: str) -> float | None:
    """Map a track name to a carrier frequency, or ``None`` to reject it.

    ``None`` is reserved for track names explicitly marked as
    unimplemented (empty string or starting with ``__``); every other
    name gets a deterministic frequency in the audible range.
    """
    if not track or track.startswith("__"):
        return None
    # Hash the name into [220, 880] Hz (A3..A5) so each track sounds
    # distinct. The range sits comfortably above any SFX we ship.
    digest = sum(ord(c) for c in track)
    return 220.0 + (digest * 7 % 661)


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
