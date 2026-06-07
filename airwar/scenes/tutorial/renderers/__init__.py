"""Tutorial scene renderer sub-components.

Split from the original ``tutorial_scene_renderer.py`` (Phase 4 Wave
alpha). Each renderer is pure: takes the scene as a read-only context
and draws onto a pygame surface. No state mutation, no event handling.
"""

from __future__ import annotations

from .background_renderer import BackgroundRenderer
from .effect_renderer import EffectRenderer
from .entity_renderer import EntityRenderer
from .ui_renderer import UIRenderer

__all__ = [
    "BackgroundRenderer",
    "EffectRenderer",
    "EntityRenderer",
    "UIRenderer",
]
