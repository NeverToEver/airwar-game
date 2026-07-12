"""GameSceneEventDispatcher — owns GameScene.handle_events() body.

Phase 5-ε: extracted from GameScene to slim the facade to ≤450 lines.
Mirrors the Boss / Homecoming / Mothership split pattern: facade +
sub-component with constructor injection of ``self`` (typed as
``object`` to avoid circular imports). The 26 IGameSceneProtocol
forwarders and the 8 properties stay on the facade.

The body is migrated verbatim from ``GameScene.handle_events`` (the
pre-extraction 19-line method at L231-250). The dispatcher reads scene
state via ``self._scene.<attr>`` and delegates per-event work to the
existing mixin + helper methods that stay on the facade
(``MouseInteractiveMixin.handle_mouse_motion`` / ``handle_mouse_click``,
``_sync_player_aim_target``, ``_handle_base_console_click``,
``_handle_button_click``).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from .game_scene_protocols import GameSceneProtocol

_logger = logging.getLogger(__name__)


class GameSceneEventDispatcher:
    """Per-event dispatch body extracted from GameScene (Phase 5-ε).

    Translates pygame events into scene state changes. Owns no state of
    its own — the dispatcher is stateless across frames; the scene owns
    the persistent state (pause request, hover, button registry, etc.).

    Exceptions raised by a single event handler are caught and logged so
    that one bad branch does not prevent the rest of the frame's events
    from being processed.
    """

    def __init__(self, scene: GameSceneProtocol) -> None:
        self._scene = scene

    def dispatch(self, event: pygame.event.Event) -> None:
        """Process one input event (verbatim migration of the pre-extraction body).

        L → toggle HUD (K_l)
        mouse motion → aim assist + talent console + mouse hover
        mouse button down → aim assist + base console click (early return)
            + scene mouse click + registered button click
        """
        scene = self._scene
        if scene._input_coordinator is None or scene.game_renderer is None:
            return
        try:
            scene._input_coordinator.handle_events(event)

            if event.type == pygame.KEYDOWN and event.key == pygame.K_l:
                if scene.game_renderer.integrated_hud:
                    scene.game_renderer.integrated_hud.toggle()
            elif event.type == pygame.MOUSEMOTION:
                scene._aim_assist.set_raw_aim_position(event.pos)
                scene._sync_player_aim_target()
                if scene._homecoming_base_pending and scene._base_talent_console:
                    scene._base_talent_console.handle_mouse_motion(event.pos)
                scene.handle_mouse_motion(event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                scene._aim_assist.set_raw_aim_position(event.pos)
                scene._sync_player_aim_target()
                if event.button == 1 and scene._homecoming_base_pending and scene._handle_base_console_click(event.pos):
                    return
                if event.button == 1 and scene.handle_mouse_click(event.pos):
                    scene._handle_button_click(scene.get_hovered_button())
        except Exception:
            _logger.exception("Unhandled exception dispatching event %s", event)


__all__ = ["GameSceneEventDispatcher"]
