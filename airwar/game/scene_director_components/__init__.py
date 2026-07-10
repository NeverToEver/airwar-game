"""Internal package -- components extracted from :class:`SceneDirector`.

Phase 4 W-β: re-export the component classes. The slim
:class:`airwar.game.scene_director.SceneDirector` module (sitting
alongside this package) owns these as private attributes; downstream
callers should keep importing ``SceneDirector`` from
:mod:`airwar.game.scene_director`.
"""

from __future__ import annotations

from .scene_state_persistence import SceneStatePersistence
from .scene_switcher import SceneSwitcher

__all__ = [
    "SceneStatePersistence",
    "SceneSwitcher",
]
