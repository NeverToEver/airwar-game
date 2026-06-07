"""Reward click handler — input dispatch, hover, and selection confirmation.

Owns the input-side behavior: keyboard navigation (W/S/Up/Down/Enter/Space)
and the MouseSelectableMixin click/motion wiring. The handler keeps no
significant state of its own — it routes events into the parent
``RewardSelector`` so that the orchestrator remains the single source of
truth for ``selected_index`` and ``on_select``.
"""

import pygame


class RewardClickHandler:
    """Dispatch keyboard and mouse input to the reward selector state.

    The handler holds a back-reference to the orchestrator so it can
    call into the public methods (``_confirm_selection``,
    ``hide``) and read ``selected_index`` / ``options`` as needed.
    """

    def __init__(self, selector):
        self._selector = selector

    def handle_input(self, event: pygame.event.Event) -> None:
        """Route a single pygame event to keyboard or mouse handlers.

        Args:
            event: Pygame event to process.
        """
        selector = self._selector
        if not selector.visible:
            return

        if event.type == pygame.KEYDOWN:
            self._handle_keydown(event)
        elif event.type == pygame.MOUSEMOTION:
            selector.handle_mouse_motion(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and selector.handle_mouse_click(event.pos):
            selector._confirm_selection()

    def _handle_keydown(self, event: pygame.event.Event) -> None:
        """Handle keyboard navigation keys.

        Args:
            event: A KEYDOWN pygame event.
        """
        selector = self._selector
        if not selector.options:
            return
        if event.key in (pygame.K_UP, pygame.K_w):
            selector.selected_index = (selector.selected_index - 1) % len(selector.options)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            selector.selected_index = (selector.selected_index + 1) % len(selector.options)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            selector._confirm_selection()
