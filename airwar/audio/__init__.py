"""Audio subsystem for AirWar.

Provides a minimal vertical slice of SFX/BGM infrastructure: a lazily
initialized :class:`SoundManager` that gracefully no-ops when no audio
device is available, a single procedurally generated SFX (``bullet_fire``)
created in-code via :mod:`pygame.sndarray`, and stubbed ``play_bgm`` /
``stop_bgm`` APIs that activate once audio assets are shipped.

Importing this package must not touch ``pygame.mixer``; mixer is only
initialized on the first audio call (lazy init).
"""

from airwar.audio.sound_manager import SoundManager, get_sound_manager

__all__ = ["SoundManager", "get_sound_manager"]
