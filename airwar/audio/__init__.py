"""Audio subsystem for AirWar.

Provides a lazily initialized :class:`SoundManager` that gracefully
no-ops when no audio device is available. The ``bullet_fire`` SFX ships
as fixed WAV variants (sfxr-style laser zap, cycled round-robin) with
a same-recipe procedural fallback via :mod:`pygame.sndarray`; stubbed
``play_bgm`` / ``stop_bgm`` APIs activate once BGM assets are shipped.

Importing this package must not touch ``pygame.mixer``; mixer is only
initialized on the first audio call (lazy init).
"""

from airwar.audio.sound_manager import SoundManager, get_sound_manager

__all__ = ["SoundManager", "get_sound_manager"]
