"""Scene orchestration -- manages scene transitions and lifecycle.

Slim coordinator (Phase 4 W-β). All 40 logic methods are 1-line
forwarders to one of three component classes held as private
attributes:

* :class:`SceneSwitcher` -- welcome/tutorial/game flow + per-scene main loop.
* :class:`SceneStatePersistence` -- save / restore / clear game state.
* :class:`SceneAchievementBridge` -- achievement registry, event-bus wiring, evaluation.

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

from ..scenes import GameScene, SceneManager
from ..scenes.scene import PauseAction
from ..utils.database import DatabaseError
from .achievements import AchievementRegistry
from .mother_ship import GameSaveData, PersistenceManager
from .mother_ship.interfaces import IEventBus
from .scaled_viewport import ScaledViewport
from .scene_director_components import SceneAchievementBridge, SceneStatePersistence, SceneSwitcher


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
        viewport: ScaledViewport = None,
    ):
        self._logger = logging.getLogger(self.__class__.__name__)
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
        # Achievement system — populated by _create_achievement_registry
        # after a successful welcome flow. None for guest sessions or
        # when no UserDB is wired up.
        self._achievement_registry: AchievementRegistry | None = None
        # Per-run counter incremented on EVENT_DOCKING_COMPLETE.
        # Reset to 0 in _run_welcome_flow on every welcome iteration
        # so a restart-from-menu starts fresh.
        self._mothership_dock_count: int = 0

        # Phase 4 components
        self._switcher = SceneSwitcher(self, self._scene_manager, self._viewport)
        self._persistence = SceneStatePersistence(self)
        self._achievements = SceneAchievementBridge(self)

        self._switcher.update_viewport_from_window()

    @property
    def current_user(self) -> str | None:
        return self._current_user

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

    # -- Achievement bridge forwarders ------------------------------------------

    def _create_achievement_registry(self) -> None:
        self._achievements.create_achievement_registry()

    def _acquire_event_bus(self) -> IEventBus | None:
        return self._achievements.acquire_event_bus()

    def _on_mothership_docking_complete(self, **_kwargs: object) -> None:
        self._achievements.on_mothership_docking_complete(**_kwargs)

    def _evaluate_achievements(self, game_scene: GameScene) -> list[str]:
        return self._achievements.evaluate_achievements(game_scene)

    def _update_user_stats(self, score: int, kills: int) -> int | None:
        return self._achievements.update_user_stats(score, kills)

    def _submit_leaderboard_score(self, score: int) -> int:
        return self._achievements.submit_leaderboard_score(score)
