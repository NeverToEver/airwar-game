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
from ...scenes.scene import ExitConfirmAction, PauseAction
from ..scaled_viewport import ScaledViewport


class SceneSwitcher:
    """Run welcome/tutorial/game flow and per-scene main loops.

    All public attributes here are read or mutated by the parent
    :class:`SceneDirector`; the director holds a reference to a single
    ``SceneSwitcher`` instance and forwards each public method to it.
    """

    def __init__(self, director, scene_manager: SceneManager, viewport: ScaledViewport) -> None:
        self._director = director
        self._logger = logging.getLogger(director.__class__.__name__)
        self._scene_manager = scene_manager
        self._viewport = viewport

    # -- Scene-flow entry points -------------------------------------------------

    def run_welcome_flow(self) -> tuple:
        """Single-page beginner interface: login + difficulty + controls in one screen."""
        while self._director._running:
            self._scene_manager.switch("welcome", viewport=self._viewport)
            welcome = self._scene_manager.get_current_scene()

            result = self._run_scene_loop(welcome)
            if result == "quit":
                return (False, None)

            if hasattr(welcome, "should_quit") and welcome.should_quit():
                return (False, None)
            if hasattr(welcome, "should_open_tutorial") and welcome.should_open_tutorial():
                result = self._run_tutorial_flow()
                if result == "quit":
                    return (False, None)
                continue
            if hasattr(welcome, "should_open_settings") and welcome.should_open_settings():
                if not self._show_settings_menu():
                    return (False, None)
                continue
            if welcome.is_ready():
                self._director._current_user = welcome.get_username()
                self._director._selected_difficulty = welcome.get_difficulty()
                # Reset per-run achievement state so a restart-from-menu
                # does not carry over the previous run's dock count or
                # registry reference.
                self._director._mothership_dock_count = 0
                self._director._achievement_registry = None
                self._director._load_user_settings()
                self._director._create_achievement_registry()
                save_data = self._director._check_and_get_saved_game(self._director._current_user)
                return (True, save_data)
            return (True, None)
        return (False, None)

    def run_tutorial_flow(self) -> str:
        tutorial = self._scene_manager.get_scene("tutorial")
        if not tutorial:
            return "main_menu"

        self._scene_manager.switch("tutorial", viewport=self._viewport)
        tutorial = self._scene_manager.get_current_scene()

        result = self._run_scene_loop(tutorial)
        return "quit" if result == "quit" else "main_menu"

    def run_game_flow(self) -> str:
        self._logger.info(
            f"Starting game flow: difficulty={self._director._selected_difficulty}, user={self._director._current_user}"
        )
        self._scene_manager.switch(
            "game",
            difficulty=self._director._selected_difficulty,
            username=self._director._current_user or "Guest",
            settings_ref=self._director._settings_ref,
            viewport=self._viewport,
        )

        current_scene = self._scene_manager.get_current_scene()
        if self._director._pending_save_data and isinstance(current_scene, GameScene):
            current_scene.restore_from_save(self._director._pending_save_data)
            self._director._pending_save_data = None
            self._logger.info("Game restored from pending save data")

        while self._director._running:
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

            self._handle_scene_events(events, escape_handled)

            # Check for pause requests triggered by mouse click
            if isinstance(current_scene, GameScene) and not escape_handled:
                if not current_scene.is_homecoming_locked() and current_scene.consume_pause_request():
                    current_scene.pause()
                    action = self._show_pause_menu(current_scene)
                    result = self._director._dispatch_pause_action(action, current_scene, from_mouse=True)
                    if result:
                        return result

            self._scene_manager.update()
            self._render_current_scene()
            self._director._window.flip()
            self._director._window.tick(FPS)

            if isinstance(current_scene, GameScene) and current_scene.is_game_over():
                self._director._clear_saved_game()
                result = self._handle_game_over(current_scene)
                if result:
                    return "main_menu"
                else:
                    return "quit"

        return "quit"

    # -- Per-scene main loop ----------------------------------------------------

    def _run_scene_loop(self, scene, *, escape_handled: bool = False) -> str:
        """Run the standard poll→update→render loop until scene exits or user quits.

        Args:
            scene: The scene instance to run.
            escape_handled: If True, skip ESC key in event dispatch.

        Returns:
            "quit" if the user closed the window, "ended" if the scene exited normally.
        """
        while self._director._running and scene.is_running():
            events = self._poll_events()
            if not self._check_quit(events):
                return "quit"
            self._handle_resize_if_needed(events)
            self._handle_scene_events(events, escape_handled)
            scene.update()
            self._render_scene(scene)
            self._director._window.flip()
            self._director._window.tick(FPS)
        return "quit" if not self._director._running else "ended"

    # -- Event polling and dispatch ---------------------------------------------

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

    def _handle_scene_events(self, events: list[pygame.event.Event], skip_escape: bool = False) -> None:
        for event in events:
            if skip_escape and hasattr(event, "key") and event.key == pygame.K_ESCAPE:
                continue
            self._scene_manager.handle_events(event)

    def _map_mouse_event(self, event: pygame.event.Event) -> pygame.event.Event:
        if not hasattr(event, "pos"):
            return event
        attrs = getattr(event, "dict", {}).copy()
        attrs["pos"] = self._viewport.screen_to_logical(*event.pos)
        return pygame.event.Event(event.type, attrs)

    # -- Resize / viewport ------------------------------------------------------

    def _handle_resize(self, width: int, height: int) -> None:
        set_display_size(width, height)
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
        result = self._run_scene_loop(settings_scene)
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

            result = self._run_scene_loop(pause_scene)
            if result == "quit":
                return PauseAction.QUIT

            result = pause_scene.get_result()
            pause_scene.exit()

            if result == "settings":
                if not self._show_settings_menu(game_scene=game_scene):
                    return PauseAction.QUIT
                continue

            return result if result else PauseAction.RESUME

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

        loop_result = self._run_scene_loop(exit_scene)
        if loop_result == "quit":
            return "quit"

        result = exit_scene.get_result()
        exit_scene.exit()
        if result == ExitConfirmAction.RETURN_TO_MENU:
            if not saved:
                self._director._clear_saved_game()
            return "main_menu"
        elif result == ExitConfirmAction.START_NEW_GAME:
            self._director._clear_saved_game()
            return "restart"
        else:
            if not saved:
                self._director._clear_saved_game()
            return "quit"

    def _handle_game_over(self, game_scene: GameScene) -> bool:
        final_score = game_scene.score
        kills = game_scene.get_kill_count()
        boss_kills = game_scene.get_boss_kill_count()
        self._director._update_user_stats(final_score, kills)
        self._director._submit_leaderboard_score(final_score)
        # Final achievement pass — must run before the death scene so
        # any per-run unlocks are evaluated against the final stats.
        newly_unlocked = self._director._evaluate_achievements(game_scene)

        death_scene = self._scene_manager.get_scene("death")
        if not death_scene:
            return False

        death_scene.enter(
            score=final_score,
            kills=kills,
            boss_kills=boss_kills,
            username=self._director._current_user,
            newly_unlocked_achievements=newly_unlocked,
        )

        self._run_scene_loop(death_scene)

        result = death_scene.get_result()
        death_scene.exit()
        return result == "return_to_menu"
