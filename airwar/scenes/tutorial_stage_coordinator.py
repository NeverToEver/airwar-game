"""Tutorial stage machine coordinator.

The TutorialScene used to keep all stage logic inline in a single
1.3k-line file. After the Phase 4 split, the stage machine
(loading, advancing, transitioning, fading) lives in
:class:`TutorialStageCoordinator`. The scene keeps lifecycle
(:meth:`enter`, :meth:`exit`, :meth:`update`, :meth:`render`,
:meth:`handle_events`) but delegates per-frame stage progression
to the coordinator.

After the stage-class split (this file's latest revision), the
coordinator no longer maintains a ``stage_id -> method_name`` table.
It calls :meth:`BaseStage.tick` on the scene's current
``_stage_instance``, which the scene builds via
:func:`airwar.scenes.tutorial.stages.build_stage` on every stage
load. The dispatch-id constants are still exported as
documentation of which stage ids are recognised.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from airwar.scenes.tutorial.stages import (
    BOOST_STAGE_ID,
    BOSS_STAGE_ID,
    COMBAT_STAGE_ID,
    HOMECOMING_STAGE_ID,
    MOTHERSHIP_STAGE_ID,
    MOVEMENT_STAGE_ID,
)

if TYPE_CHECKING:
    from .tutorial_scene import TutorialScene


class TutorialStageCoordinator:
    """Per-frame stage progression for :class:`TutorialScene`.

    Owns:
        * the per-frame stage dispatch (delegates to scene stage instance)
        * the fade in/out animation
        * stage-completion check + delay-then-advance

    Reads from the scene every frame; writes back via the scene's
    mutator methods (``_start_stage_transition``, ``_load_stage``).
    """

    # Recognised stage ids (kept here for documentation / introspection;
    # the dispatch itself reads them off the active ``BaseStage``).
    RECOGNISED_STAGE_IDS: tuple[str, ...] = (
        MOVEMENT_STAGE_ID,
        COMBAT_STAGE_ID,
        BOOST_STAGE_ID,
        MOTHERSHIP_STAGE_ID,
        HOMECOMING_STAGE_ID,
        BOSS_STAGE_ID,
    )

    def __init__(self, scene: TutorialScene) -> None:
        self._scene = scene

    def update_stage(self) -> None:
        """Run the per-frame stage logic and check for completion."""
        scene = self._scene
        stage_instance = getattr(scene, "_stage_instance", None)
        if stage_instance is not None:
            stage_instance.tick()
        scene._check_stage_completion()
        if scene._stage_completed and scene._stage.id in (
            "mothership_docking",
            "homecoming_base",
        ):
            scene._advance_after_delay()

    def update_fade(self) -> None:
        """Run the stage-card fade in/out animation."""
        self._scene._update_fade()

    def stage_id(self) -> str | None:
        return self._scene._stage.id if self._scene._stage else None


__all__ = ["TutorialStageCoordinator"]
