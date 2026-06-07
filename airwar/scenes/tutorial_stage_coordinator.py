"""Tutorial stage machine coordinator.

The TutorialScene used to keep all stage logic inline in a single
1.3k-line file. After the Phase 4 split, the stage machine
(loading, advancing, transitioning, fading) lives in
:class:`TutorialStageCoordinator`. The scene keeps lifecycle
(:meth:`enter`, :meth:`exit`, :meth:`update`, :meth:`render`,
:meth:`handle_events`) but delegates per-frame stage progression
to the coordinator.

Why this split?
    The seven tutorial stages (movement, aim, boost, combat, docking,
    homecoming, boss) each have a small but non-trivial update
    method. Keeping them all in the scene class made it hard to
    review. The coordinator is a single file with a single dispatch
    table (``_STAGE_HANDLERS``); new stages just add an entry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .tutorial_scene import TutorialScene


class TutorialStageCoordinator:
    """Per-frame stage progression for :class:`TutorialScene`.

    Owns:
        * ``stage_index`` and ``pending_stage_index``
        * the fade in/out animation
        * stage-completion check + delay-then-advance
        * per-stage dispatch table

    Reads from the scene every frame; writes back via the scene's
    mutator methods (``_start_stage_transition``,
    ``_load_stage``, ``_on_*_stage_completed``).
    """

    # Each stage id maps to a method on the scene that drives its
    # per-frame logic. ``None`` means "no per-frame update needed".
    _STAGE_HANDLERS: dict[str, str] = {
        "movement": "_update_movement_stage",
        "aim": "_update_aim_stage",
        "boost": "_update_boost_stage",
        "combat": "_update_combat_stage",
        "mothership_docking": "_update_docking_stage",
        "homecoming_base": "_update_homecoming_stage",
        "boss": "_update_boss_stage",
    }

    def __init__(self, scene: TutorialScene) -> None:
        self._scene = scene

    def update_stage(self) -> None:
        """Run the per-frame stage logic and check for completion."""
        scene = self._scene
        if not scene._stage:
            return
        stage_id = scene._stage.id
        # Stages that have no per-frame update (e.g. intro/movement)
        # still get a completion check.
        handler_name = self._STAGE_HANDLERS.get(stage_id)
        if handler_name is not None and hasattr(scene, handler_name):
            handler = getattr(scene, handler_name)
            handler()
        scene._check_stage_completion()
        if scene._stage_completed and stage_id in (
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
