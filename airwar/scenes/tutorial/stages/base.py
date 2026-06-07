"""Base class for per-frame tutorial stage logic.

The seven tutorial stages (movement, aim, boost, combat, mothership
docking, homecoming, boss) each have a small but non-trivial update
method. Before the split, those methods all lived on
:class:`airwar.scenes.tutorial_scene.TutorialScene` and were dispatched
from :mod:`airwar.scenes.tutorial_stage_coordinator` via a string
``stage_id -> method_name`` table.

After this refactor, each stage owns its per-frame logic in a
:class:`BaseStage` subclass. The scene keeps the lifecycle
(:meth:`enter`, :meth:`update`, :meth:`render`, ...) and the coordinator
just calls :meth:`BaseStage.tick`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..tutorial_scene import TutorialScene


class BaseStage(ABC):
    """Per-frame stage logic for one tutorial stage.

    Subclasses are constructed once per stage activation by
    :func:`build_stage` and reused for the lifetime of the active stage
    (typically a single stage's run; the scene re-builds on stage
    advance). They read scene state directly and mutate via the scene's
    existing mutator methods.
    """

    #: Dispatch id used by :class:`TutorialStageCoordinator`. Must match
    #: the keys in the legacy ``_STAGE_HANDLERS`` table so existing
    #: coordinator logic keeps working unchanged.
    stage_id: str = ""

    def __init__(self, scene: TutorialScene) -> None:
        self._scene = scene

    def tick(self) -> None:
        """Run one frame of stage logic.

        Default implementation just calls :meth:`update`. Subclasses
        override :meth:`update` -- ``tick`` exists so future hook points
        (timing, telemetry) can be added without breaking the
        coordinator contract.
        """
        self.update()

    @abstractmethod
    def update(self) -> None:
        """Per-frame stage update. Subclasses must implement."""

    def is_complete(self) -> bool:
        """Stage completion predicate.

        Default returns ``False`` -- the scene's existing
        :meth:`_check_stage_completion` owns the authoritative
        ``_stage_completed`` flag. Stages only override this when they
        need to short-circuit the dispatch (currently none do).
        """
        return False


__all__ = ["BaseStage"]
