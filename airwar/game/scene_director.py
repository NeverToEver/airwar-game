"""Scene orchestration -- manages scene transitions and lifecycle.

Slim coordinator (Phase 4 W-β). Logic methods are 1-line
forwarders to one of two component classes held as private
attributes:

* :class:`SceneSwitcher` -- welcome/tutorial/game flow + per-scene main loop.
* :class:`SceneStatePersistence` -- save / restore / clear game state.

The pause/menu action dispatch (``_handle_pause_toggle``,
``_pause_action_result``, ``_dispatch_pause_result``,
``_dispatch_pause_action``) and the user-settings loader
(``_load_user_settings`` / ``_apply_settings_to_player``) stay in
this module: they bridge between the switcher and the persistence
layer and were not large enough to warrant a fourth component.

Public API (3) is preserved: ``run``, ``stop``, ``current_user``.
"""

import logging

import pygame

from .._log import register_crash_context_provider
from ..scenes import GameScene, SceneManager
from ..scenes.scene import PauseAction
from ..utils.database import DatabaseError
from .mother_ship import GameSaveData, PersistenceManager
from .scaled_viewport import ScaledViewport
from .scene_director_components import SceneStatePersistence, SceneSwitcher
from airwar.leaderboard import LeaderboardService


class SceneDirector:
    """Scene director -- orchestrates scene transitions and lifecycle.

    Manages the high-level scene flow: Welcome -> Game, with support
    for pause, death, and exit confirmation overlays. Preserves scene
    state across transitions via SceneManager.

    Attributes:
        _window: Pygame display window reference.
        _scene_manager: SceneManager for registration and switching.
    """

    def __init__(
        self,
        window,
        scene_manager: SceneManager,
        user_db=None,
        viewport: ScaledViewport | None = None,
    ):
        # Child of the "airwar" logger so --debug also covers this module
        # and records propagate to the root file handler.
        self._logger = logging.getLogger(f"airwar.{self.__class__.__name__}")
        self._window = window
        self._scene_manager = scene_manager
        self._user_db = user_db
        self._viewport = viewport or ScaledViewport()
        self._running = True
        self._current_user: str | None = None
        self._selected_difficulty: str = "medium"
        self._pending_save_data = None
        self._save_dir = None
        self._settings_ref = {"ctrl_mode": "hold", "shift_boost_mode": "hold"}
        self._leaderboard_service = (
            LeaderboardService(user_db) if user_db is not None else None
        )

        # Phase 4 components
        self._switcher = SceneSwitcher(self, self._scene_manager, self._viewport)
        self._persistence = SceneStatePersistence(self)

        self._switcher.update_viewport_from_window()

        # Attach live game state to crash dumps (invoked at crash time only).
        register_crash_context_provider(self._crash_context)

    @property
    def current_user(self) -> str | None:
        return self._current_user

    def _crash_context(self) -> dict:
        """Live game state merged into crash dumps (called at crash time only)."""
        return {
            "scene": self._scene_manager.get_current_scene_name(),
            "running": self._running,
            "user": self._current_user,
            "difficulty": self._selected_difficulty,
            "frames_since_reset": self._switcher._frames_advanced,
            "consecutive_frame_errors": self._switcher._consecutive_frame_errors,
        }

    # -- Public API (3) ---------------------------------------------------------

    def run(self) -> None:
        self._running = True
        while self._running:
            welcome_ok, save_data = self._run_welcome_flow()
            if not welcome_ok:
                break
            self._pending_save_data = save_data
            result = self._run_game_flow()
            if result == "quit":
                break
            if result in ("main_menu", "restart"):
                self._pending_save_data = None
                continue

    def stop(self) -> None:
        self._running = False

    # -- Switcher forwarders ----------------------------------------------------

    def _run_welcome_flow(self) -> tuple:
        return self._switcher.run_welcome_flow()

    def _run_tutorial_flow(self) -> str:
        return self._switcher.run_tutorial_flow()

    def _run_game_flow(self) -> str:
        return self._switcher.run_game_flow()

    def _run_scene_loop(self, scene, *, escape_handled: bool = False) -> str:
        return self._switcher._run_scene_loop(scene, escape_handled=escape_handled)

    def _poll_events(self) -> list:
        return self._switcher._poll_events()

    def _check_quit(self, events: list) -> bool:
        return self._switcher._check_quit(events)

    def _handle_resize_if_needed(self, events: list) -> None:
        self._switcher._handle_resize_if_needed(events)

    def _handle_scene_events(self, events: list, skip_escape: bool = False) -> None:
        self._switcher._handle_scene_events(events, skip_escape)

    def _handle_resize(self, width: int, height: int) -> None:
        self._switcher._handle_resize(width, height)

    def _update_viewport_from_window(self) -> None:
        self._switcher.update_viewport_from_window()

    def _map_mouse_event(self, event):
        return self._switcher._map_mouse_event(event)

    def _render_current_scene(self) -> None:
        self._switcher._render_current_scene()

    def _render_scene(self, scene) -> None:
        self._switcher._render_scene(scene)

    def _show_settings_menu(self, game_scene=None) -> bool:
        return self._switcher._show_settings_menu(game_scene=game_scene)

    def _show_pause_menu(self, game_scene: GameScene) -> PauseAction:
        return self._switcher._show_pause_menu(game_scene)

    def _show_exit_confirm(self, saved: bool) -> str:
        return self._switcher._show_exit_confirm(saved)

    def _handle_game_over(self, game_scene: GameScene) -> bool:
        return self._switcher._handle_game_over(game_scene)

    # -- Pause dispatch (kept in main director) --------------------------------

    def _handle_pause_toggle(self, events: list, game_scene: GameScene) -> str:
        if getattr(game_scene, "is_homecoming_locked", lambda: False)():
            return "none"

        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if game_scene.paused:
                    game_scene.resume()
                    return "resume"
                else:
                    game_scene.pause()
                    action = self._show_pause_menu(game_scene)
                    return self._pause_action_result(action, game_scene)
        return "none"

    def _pause_action_result(self, action: PauseAction, game_scene: GameScene) -> str:
        if action == PauseAction.RESUME:
            game_scene.resume()
            return "resume"
        if action == PauseAction.MAIN_MENU:
            return "main_menu"
        if action == PauseAction.SAVE_AND_QUIT:
            return "save_and_quit"
        if action == PauseAction.QUIT_WITHOUT_SAVING:
            return "quit_without_saving"
        if action == PauseAction.QUIT:
            # 保存并退出（映射到 save_and_quit）
            return "save_and_quit"
        return "none"

    def _dispatch_pause_result(
        self,
        result: str,
        current_scene: GameScene,
        *,
        source: str = "",
    ) -> str | None:
        if result in ("resume", "none"):
            return None
        if result == "main_menu":
            self._clear_saved_game()
            self._logger.info("Game flow ended%s: main_menu", source)
            return "main_menu"
        if result == "save_and_quit":
            saved = self._persistence.save_and_quit(current_scene)
            self._logger.info("Game flow ended%s: save_and_quit", source)
            return self._show_exit_confirm(saved=saved)
        if result == "quit_without_saving":
            self._clear_saved_game()
            self._logger.info("Game flow ended%s: quit_without_saving", source)
            return self._show_exit_confirm(saved=False)
        return None

    def _dispatch_pause_action(
        self,
        action: PauseAction,
        current_scene: GameScene,
        *,
        from_mouse: bool = False,
    ) -> str | None:
        result = self._pause_action_result(action, current_scene)
        if result == "main_menu":
            current_scene.resume()
        source = " from pause" if from_mouse else ""
        return self._dispatch_pause_result(result, current_scene, source=source)

    # -- User settings (kept in main director) ---------------------------------

    def _load_user_settings(self) -> None:
        if not self._current_user or self._current_user == "Guest" or not self._user_db:
            return
        try:
            saved = self._user_db.get_user_settings(self._current_user)
            if saved:
                self._settings_ref.update(saved)
        except DatabaseError:
            self._logger.warning("Failed to load user settings", exc_info=True)

    def _apply_settings_to_player(self, player) -> None:
        player.apply_settings(self._settings_ref)

    def _update_user_stats(self, score: int, kills: int) -> int | None:
        if not self._current_user or not self._user_db:
            return None
        try:
            user_data = self._user_db.get_user_data(self._current_user)
            new_high = max(score, user_data.get("high_score", 0))
            self._user_db.update_user_data(
                self._current_user,
                {
                    "high_score": new_high,
                    "total_kills": user_data.get("total_kills", 0) + kills,
                    "games_played": user_data.get("games_played", 0) + 1,
                },
            )
            return new_high
        except DatabaseError:
            self._logger.warning("Failed to update user stats", exc_info=True)
            return None

    def _submit_leaderboard_score(self, score: int) -> int:
        if not self._user_db or self._leaderboard_service is None:
            return 0
        name = self._current_user or "Guest"
        try:
            return self._leaderboard_service.submit_score(name, score)
        except DatabaseError:
            self._logger.warning("Failed to submit leaderboard score", exc_info=True)
            return 0

    # -- Persistence forwarders -------------------------------------------------

    def _check_and_get_saved_game(self, username: str) -> GameSaveData | None:
        return self._persistence.check_and_get_saved_game(username)

    def _perform_save(self, game_scene: GameScene) -> bool:
        return self._persistence.perform_save(game_scene)

    def _save_game_on_quit(self, game_scene: GameScene) -> None:
        self._persistence.save_game_on_quit(game_scene)

    def _clear_saved_game(self) -> None:
        self._persistence.clear_saved_game()

    def _candidate_persistence_managers(self, username: str) -> list[PersistenceManager]:
        return self._persistence._candidate_persistence_managers(username)

    def _save_and_quit(self, game_scene: GameScene) -> bool:
        return self._persistence.save_and_quit(game_scene)

    def _quit_without_saving(self) -> None:
        self._persistence.quit_without_saving()
