"""Scene switching -- welcome/tutorial/game flow and per-frame event loop.

Extracted from :class:`airwar.game.scene_director.SceneDirector` (Phase 4 W-β).
Holds the orchestration for entering each scene, running its main loop,
dispatching pause/menu/exit-confirm flows, and rendering via the viewport.
"""

from __future__ import annotations

import logging

import pygame

from ...config import FPS, set_display_size
from ...scenes import GameScene, SceneManager
from ...scenes.scene import ExitConfirmAction, PauseAction, Scene
from ..frame_context import FrameClock, FrameContext
from ..scaled_viewport import ScaledViewport


class SceneSwitcher:
    """Run welcome/tutorial/game flow and per-scene main loops.

    All public attributes here are read or mutated by the parent
    :class:`SceneDirector`; the director holds a reference to a single
    ``SceneSwitcher`` instance and forwards each public method to it.
    """

    # Number of consecutive frames that may raise before the director gives up.
    _MAX_CONSECUTIVE_FRAME_ERRORS = 5

    def __init__(self, director, scene_manager: SceneManager, viewport: ScaledViewport) -> None:
        self._director = director
        # Child of the "airwar" logger so records propagate to the root
        # file handler (a bare class-name logger only reached stderr).
        self._logger = logging.getLogger(f"airwar.{director.__class__.__name__}")
        self._scene_manager = scene_manager
        self._viewport = viewport
        self._frame_clock = FrameClock()
        self._consecutive_frame_errors = 0
        self._frames_advanced = 0

    # -- Scene-flow entry points -------------------------------------------------

    def run_welcome_flow(self) -> tuple:
        """Single-page beginner interface: login + difficulty + controls in one screen."""
        # Switch to the welcome scene once, before the loop. Child flows
        # restore it through ``_resume_welcome_scene`` so the next
        # iteration always has a running welcome scene and no stale
        # one-shot navigation request.
        self._scene_manager.switch("welcome", viewport=self._viewport)
        welcome = self._scene_manager.get_current_scene()
        if welcome is None:
            raise RuntimeError("Welcome scene was not set after switch")
        while self._director._running:
            result = self._run_scene_loop(welcome)
            if result == "quit":
                return (False, None)

            if hasattr(welcome, "should_quit") and welcome.should_quit():
                return (False, None)
            if hasattr(welcome, "should_open_tutorial") and welcome.should_open_tutorial():
                result = self.run_tutorial_flow()
                if result == "quit":
                    return (False, None)
                self._resume_welcome_scene(welcome, "tutorial")
                continue
            if hasattr(welcome, "should_open_settings") and welcome.should_open_settings():
                self._consume_welcome_request(welcome, "settings")
                if not self._show_settings_menu():
                    return (False, None)
                self._resume_welcome_scene(welcome)
                continue
            if welcome.is_ready():
                self._director._current_user = welcome.get_username()
                self._director._selected_difficulty = welcome.get_difficulty()
                self._director._load_user_settings()
                save_data = self._director._check_and_get_saved_game(self._director._current_user)
                return (True, save_data)
            return (False, None)
        return (False, None)

    def _consume_welcome_request(self, welcome, request: str | None = None) -> None:
        """Clear one-shot welcome navigation flags before re-running welcome."""
        if request in (None, "tutorial") and hasattr(welcome, "tutorial_requested"):
            welcome.tutorial_requested = False
        if request in (None, "settings") and hasattr(welcome, "settings_requested"):
            welcome.settings_requested = False

    def _resume_welcome_scene(self, welcome, consumed_request: str | None = None) -> None:
        """Make the already-registered welcome scene ready for another loop."""
        self._consume_welcome_request(welcome, consumed_request)
        if hasattr(welcome, "running"):
            welcome.running = True
        if hasattr(welcome, "clear_hover"):
            welcome.clear_hover()
        if self._scene_manager.get_current_scene_name() != "welcome":
            self._scene_manager.switch("welcome", viewport=self._viewport)

    def run_tutorial_flow(self) -> str:
        tutorial = self._scene_manager.get_scene("tutorial")
        if not tutorial:
            return "main_menu"

        self._scene_manager.switch("tutorial", viewport=self._viewport)
        self._reset_game_timing()
        tutorial = self._scene_manager.get_current_scene()

        result = self._run_scene_loop(tutorial)
        return "quit" if result == "quit" else "main_menu"

    def run_game_flow(self) -> str:
        self._logger.info(
            f"Starting game flow: difficulty={self._director._selected_difficulty}, user={self._director._current_user}"
        )
        try:
            self._scene_manager.switch(
                "game",
                difficulty=self._director._selected_difficulty,
                username=self._director._current_user or "Guest",
                settings_ref=self._director._settings_ref,
                save_service=self._director._persistence.save_service,
                viewport=self._viewport,
            )
        except Exception:
            self._logger.exception("Failed to build game scene")
            self._director._pending_save_data = None
            return "main_menu"
        self._reset_game_timing()
        # Start each flow with a clean error budget: the counter is shared
        # across scene loops and must not carry over from a previous one
        # (an aborted game flow now returns to the menu instead of quitting).
        self._consecutive_frame_errors = 0

        current_scene = self._scene_manager.get_current_scene()
        if not isinstance(current_scene, GameScene):
            self._director._pending_save_data = None
            return "main_menu"

        if self._director._pending_save_data:
            try:
                current_scene.restore_from_save(self._director._pending_save_data)
                self._logger.info("Game restored from pending save data")
            except Exception:
                self._logger.exception("Save restore failed")
            self._director._pending_save_data = None
        while self._director._running:
            frame = self._next_frame(simulate=True)
            escape_handled = False
            current_scene = self._scene_manager.get_current_scene()

            events = self._poll_events()
            if not self._check_quit(events):
                if isinstance(current_scene, GameScene):
                    self._director._save_game_on_quit(current_scene)
                self._logger.info("Game flow ended: quit")
                return "quit"
            self._handle_resize_if_needed(events)

            if isinstance(current_scene, GameScene):
                result = self._director._handle_pause_toggle(events, current_scene)
                dispatched = self._director._dispatch_pause_result(result, current_scene)
                if dispatched:
                    return dispatched
                escape_handled = result == "resume"

            # Frame-level guard, mirroring ``_run_scene_loop``: a single bad
            # frame is logged with a full traceback and skipped instead of
            # killing the whole game session.
            try:
                self._handle_scene_events(events, escape_handled, target_scene=current_scene)
            except Exception:
                if self._handle_frame_error(current_scene, "handle_events"):
                    return self._abort_game_flow()
                continue

            # Check for pause requests triggered by mouse click
            if isinstance(current_scene, GameScene) and not escape_handled:
                if not current_scene.is_homecoming_locked() and current_scene.consume_pause_request():
                    current_scene.pause()
                    action = self._show_pause_menu(current_scene)
                    result = self._director._dispatch_pause_action(action, current_scene, from_mouse=True)
                    if result:
                        return result

            try:
                self._scene_manager.update(frame)
            except Exception:
                if self._handle_frame_error(current_scene, "update"):
                    return self._abort_game_flow()
                continue

            try:
                self._render_current_scene()
            except Exception:
                if self._handle_frame_error(current_scene, "render"):
                    return self._abort_game_flow()
                continue

            try:
                self._director._window.flip()
            except Exception:
                if self._handle_frame_error(current_scene, "flip"):
                    return self._abort_game_flow()
                continue

            # Successful frame: reset the error counter.
            self._consecutive_frame_errors = 0

            if isinstance(current_scene, GameScene) and current_scene.is_game_over():
                self._director._clear_saved_game()
                result = self._handle_game_over(current_scene)
                if result:
                    return "main_menu"
                else:
                    return "quit"

        return "quit"

    def _abort_game_flow(self) -> str:
        """Give up on the game flow after repeated frame errors.

        Returns the player to the main menu (rather than killing the whole
        app) so a persistent update/render defect does not cost them the
        session; the per-frame tracebacks are already in the log file.
        """
        self._logger.error("Aborting game flow after repeated frame errors; returning to main menu")
        self._consecutive_frame_errors = 0
        return "main_menu"

    # -- Per-scene main loop ----------------------------------------------------

    def _run_scene_loop(self, scene, *, escape_handled: bool = False) -> str:
        """Run the standard poll→update→render loop until scene exits or user quits.

        Args:
            scene: The scene instance to run.
            escape_handled: If True, skip ESC key in event dispatch.

        Returns:
            "quit" if the user closed the window, "ended" if the scene exited normally.
        """
        # Render once before the first dispatch so scenes that register
        # clickable buttons in ``render()`` (e.g. via the
        # ``MouseInteractiveMixin`` / ``register_button`` pattern) have
        # valid ``_button_rects`` when the first user click is
        # dispatched. Without this pre-render, scenes that call
        # ``self.clear_buttons()`` in ``enter()`` (to reset state from
        # a prior visit) would silently drop the first click because
        # the dispatch happens before the first render. See
        # Welcome and sub-scenes register clickable buttons during rendering.
        #
        # Gated on ``is_running()`` so an exited scene does not have its
        # pre-render fired before the loop bails out.
        #
        # Reset the shared error budget: an aborted game flow returns to the
        # menu (it no longer quits the app), so a previous flow's errors must
        # not bleed into this loop.
        self._consecutive_frame_errors = 0
        if scene.is_running():
            self._render_scene(scene)
        while self._director._running and scene.is_running():
            frame = self._next_frame(simulate=bool(getattr(scene, "uses_fixed_simulation", False)))
            events = self._poll_events()
            if not self._check_quit(events):
                return "quit"
            self._handle_resize_if_needed(events)
            # Dispatch events to the target scene directly. Sub-scene
            # flows (settings, pause, death, exit_confirm)
            # do not call ``scene_manager.switch`` before ``enter()``,
            # so ``SceneManager._current_scene`` is still the calling
            # scene (typically ``welcome`` or ``game``) and a naive
            # dispatch via ``scene_manager.handle_events`` would route
            # the click to the wrong scene. Routing through
            # ``target_scene`` here makes the dispatch explicit and
            # immune to that mismatch.
            try:
                self._handle_scene_events(events, skip_escape=escape_handled, target_scene=scene)
            except Exception:
                if self._handle_frame_error(scene, "handle_events"):
                    return "quit"
                continue

            try:
                scene.update(frame)
            except Exception:
                if self._handle_frame_error(scene, "update"):
                    return "quit"
                continue

            try:
                self._render_scene(scene)
            except Exception:
                if self._handle_frame_error(scene, "render"):
                    return "quit"
                continue

            try:
                self._director._window.flip()
            except Exception:
                if self._handle_frame_error(scene, "flip"):
                    return "quit"
                continue

            # Successful frame: reset the error counter.
            self._consecutive_frame_errors = 0
        return "quit" if not self._director._running else "ended"

    def _handle_frame_error(self, scene, operation: str) -> bool:
        """Log and swallow a single-frame exception, re-raising after too many.

        Returns:
            True if the error limit was exceeded and the loop should abort.
        """
        self._logger.exception("Frame error in %s.%s", scene.__class__.__name__, operation)
        self._consecutive_frame_errors += 1
        hook = getattr(scene, "on_frame_error", None)
        if hook is not None:
            try:
                hook(operation)
            except Exception:
                self._logger.exception("on_frame_error hook failed for %s", scene.__class__.__name__)
        if self._consecutive_frame_errors >= self._MAX_CONSECUTIVE_FRAME_ERRORS:
            self._logger.error(
                "Too many consecutive frame errors (%s), aborting scene loop",
                self._consecutive_frame_errors,
            )
            return True
        return False

    # -- Event polling and dispatch ---------------------------------------------

    def _reset_game_timing(self) -> None:
        self._frame_clock.reset()
        self._frames_advanced = 0
        reset_timing = getattr(self._director._window, "reset_timing", None)
        if reset_timing is not None:
            reset_timing()

    def _next_frame(self, *, simulate: bool) -> FrameContext:
        self._frames_advanced += 1
        return self._frame_clock.advance(self._director._window.tick(FPS), simulate=simulate)

    def _poll_events(self) -> list[pygame.event.Event]:
        return [self._map_mouse_event(event) for event in pygame.event.get()]

    def _check_quit(self, events: list[pygame.event.Event]) -> bool:
        for event in events:
            if event.type == pygame.QUIT:
                self._director._running = False
                return False
        return True

    def _handle_resize_if_needed(self, events: list[pygame.event.Event]) -> None:
        for event in events:
            if event.type == pygame.VIDEORESIZE:
                # With SCALED, SDL2 handles scaling — just update viewport
                # for coordinate conversion; don't recreate the display surface.
                self._handle_resize(event.w, event.h)

    def _handle_scene_events(
        self,
        events: list[pygame.event.Event],
        skip_escape: bool = False,
        *,
        target_scene: Scene,
    ) -> None:
        """Dispatch pygame events to the appropriate scene.

        Args:
            events: Pygame events to dispatch.
            skip_escape: If True, swallow ``pygame.K_ESCAPE`` events.
            target_scene: The scene to dispatch events to directly. Used by
                ``_run_scene_loop`` for sub-scenes (settings, pause, death,
                and exit-confirm) that do not call ``scene_manager.switch``
                before ``enter()`` and therefore do not become
                ``SceneManager._current_scene``.
        """
        for event in events:
            if skip_escape and hasattr(event, "key") and event.key == pygame.K_ESCAPE:
                continue
            target_scene.handle_events(event)

    def _map_mouse_event(self, event: pygame.event.Event) -> pygame.event.Event:
        if not hasattr(event, "pos"):
            return event
        attrs = getattr(event, "dict", {}).copy()
        attrs["pos"] = self._viewport.screen_to_logical(*event.pos)
        return pygame.event.Event(event.type, attrs)

    # -- Resize / viewport ------------------------------------------------------

    def _handle_resize(self, width: int, height: int) -> None:
        set_display_size(width, height)
        # The viewport must keep its logical surface at the actual
        # display size so the mouse-coordinate transform stays a no-op
        # (see airwar/game/scaled_viewport.py for the full discussion).
        # Without this, the first resize would reintroduce the coordinate
        # mismatch the Game constructor already guards against.
        self._viewport.logical_size = (width, height)
        self._viewport._logical_surface = pygame.Surface(
            (width, height), pygame.SRCALPHA,
        )
        self._viewport.update(width, height)

    def update_viewport_from_window(self) -> None:
        if not hasattr(self._director._window, "get_size"):
            return
        width, height = self._director._window.get_size()
        self._handle_resize(width, height)

    # -- Rendering --------------------------------------------------------------

    def _render_current_scene(self) -> None:
        self._viewport.logical_surface.fill((0, 0, 0))
        self._scene_manager.render(self._viewport.logical_surface)
        self._viewport.present(self._director._window.get_surface())

    def _render_scene(self, scene) -> None:
        self._viewport.logical_surface.fill((0, 0, 0))
        scene.render(self._viewport.logical_surface)
        self._viewport.present(self._director._window.get_surface())

    # -- Sub-scenes (settings / pause / exit confirm / game over) --------------

    def _show_settings_menu(self, game_scene=None) -> bool:
        """Show settings menu. Returns False if QUIT was triggered."""
        settings_scene = self._scene_manager.get_scene("settings")
        if not settings_scene:
            return True
        settings_scene.enter(
            db=self._director._user_db,
            username=self._director._current_user,
            settings_ref=self._director._settings_ref,
        )
        try:
            result = self._run_scene_loop(settings_scene)
        finally:
            settings_scene.exit()
        if result == "quit":
            return False
        if game_scene and hasattr(game_scene, "player") and game_scene.player:
            self._director._apply_settings_to_player(game_scene.player)
        return True

    def _show_pause_menu(self, game_scene: GameScene) -> PauseAction:
        while True:
            pause_scene = self._scene_manager.get_scene("pause")
            if not pause_scene:
                return PauseAction.QUIT
            pause_scene.enter()

            try:
                loop_result = self._run_scene_loop(pause_scene)
                if loop_result == "quit":
                    return PauseAction.QUIT
                result = pause_scene.get_result()
            finally:
                pause_scene.exit()

            if result == "settings":
                if not self._show_settings_menu(game_scene=game_scene):
                    return PauseAction.QUIT
                continue

            if isinstance(result, PauseAction):
                return result
            return PauseAction.RESUME

    def _show_exit_confirm(self, saved: bool) -> str:
        """Show exit confirmation menu.

        Displayed after the player chooses to save and quit or quit without saving.
        Allows the player to return to main menu, start a new game, or exit.

        Args:
            saved: Whether the game progress has been saved.

        Returns:
            str: 'main_menu' returns to main menu, 'restart' starts a new game, 'quit' exits.
        """
        exit_scene = self._scene_manager.get_scene("exit_confirm")
        if not exit_scene:
            return "quit"

        exit_scene.enter(saved=saved, difficulty=self._director._selected_difficulty)

        try:
            loop_result = self._run_scene_loop(exit_scene)
            if loop_result == "quit":
                return "quit"
            result = exit_scene.get_result()
        finally:
            exit_scene.exit()
        if result == ExitConfirmAction.RETURN_TO_MENU:
            if not saved:
                self._director._clear_saved_game()
            return "main_menu"
        elif result == ExitConfirmAction.START_NEW_GAME:
            self._director._clear_saved_game()
            return "restart"
        elif result == ExitConfirmAction.QUIT_GAME:
            if not saved:
                self._director._clear_saved_game()
            return "quit"
        else:
            self._director._logger.warning("Unexpected exit confirm result: %r", result)
            if not saved:
                self._director._clear_saved_game()
            return "quit"

    def _handle_game_over(self, game_scene: GameScene) -> bool:
        final_score = game_scene.score
        kills = game_scene.get_kill_count()
        boss_kills = game_scene.get_boss_kill_count()
        self._director._update_user_stats(final_score, kills)
        self._director._submit_leaderboard_score(final_score)

        death_scene = self._scene_manager.get_scene("death")
        if not death_scene:
            return False

        death_scene.enter(
            score=final_score,
            kills=kills,
            boss_kills=boss_kills,
            username=self._director._current_user,
        )

        try:
            loop_result = self._run_scene_loop(death_scene)
            if loop_result == "quit":
                return False
            result = death_scene.get_result()
        finally:
            death_scene.exit()
        return result == "return_to_menu"
