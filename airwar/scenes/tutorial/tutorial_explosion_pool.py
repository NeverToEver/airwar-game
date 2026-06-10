"""Explosion pool helpers for the tutorial scene.

Phase 4 Wave α: extracted from :mod:`airwar.scenes.tutorial_scene`
to slim the god class. The explosion pool owns the
``_tutorial_explosions`` list and its countdown ticker; it also
provides a factory for new explosion entries. The
:class:`airwar.scenes.tutorial_scene.TutorialScene` keeps a 1-line
forwarder to a single :class:`TutorialExplosionPool` instance.
"""

from __future__ import annotations

from dataclasses import dataclass

from airwar.scenes.tutorial.entities_core import TutorialExplosion


@dataclass
class TutorialExplosionData:
    """Local copy of the explosion entry used by this pool.

    Mirrors :class:`~airwar.scenes.tutorial.entities_core.TutorialExplosion`
    (kept for backward compat). The pool writes entries through
    the scene's own :class:`TutorialExplosion` dataclass so the
    renderer, which reads ``scene._tutorial_explosions``, keeps
    working unchanged.
    """

    center: tuple[int, int]
    timer: int = 28
    duration: int = 28


class TutorialExplosionPool:
    """Per-frame explosion tick + spawn helper.

    The scene keeps ``self._tutorial_explosions`` as a list of
    :class:`~airwar.scenes.tutorial.entities_core.TutorialExplosion`
    dataclasses (the renderer and collision code read it
    directly). This pool ticks timers and drops expired entries
    in-place, and spawns new entries via the scene dataclass.

    The dataclass is imported from the leaf
    :mod:`airwar.scenes.tutorial.entities_core` module (M-4) so the
    pool no longer needs a method-level local import.
    """

    def __init__(self, scene) -> None:
        self._scene = scene

    def update(self) -> None:
        """Tick explosion timers and drop expired explosions."""
        scene = self._scene
        for explosion in scene._tutorial_explosions:
            explosion.timer -= 1
        scene._tutorial_explosions[:] = [explosion for explosion in scene._tutorial_explosions if explosion.timer > 0]

    def spawn(self, center: tuple[int, int]) -> None:
        """Append a fresh explosion to ``scene._tutorial_explosions``."""
        self._scene._tutorial_explosions.append(TutorialExplosion(center))


__all__ = ["TutorialExplosionData", "TutorialExplosionPool"]
