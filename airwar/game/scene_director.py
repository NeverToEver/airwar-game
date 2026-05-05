"""Scene orchestration -- manages scene transitions and lifecycle."""
from typing import Optional, List
import pygame
import logging
from ..config import FPS, set_screen_size
from ..scenes import SceneManager, GameScene
from ..scenes.scene import PauseAction, ExitConfirmAction
from .mother_ship import PersistenceManager, GameSaveData
from ..utils.database import DatabaseError


class SceneDirector:
    """Scene director -- orchestrates scene transitions and lifecycle.

        Manages the high-level scene flow: Welcome -> Game, with support
        for pause, death, and exit confirmation overlays. Preserves scene
        state across transitions via SceneManager.

        Attributes:
            _window: Pygame display window reference.
            _scene_manager: SceneManager for registration and switching.
        """
    def __init__(self, window, scene_manager: SceneManager, user_db=None):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._window = window
        self._scene_manager = scene_manager
        self._user_db = user_db
        self._running = True
        self._current_user: Optional[str] = None
        self._selected_difficulty: str = 'medium'
        self._pending_save_data = None
        self._save_dir = None

    @property
    def current_user(self) -> Optional[str]:
        return self._current_user

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

    def _run_welcome_flow(self) -> tuple:
        """Single-page beginner interface: login + difficulty + controls in one screen."""
        self._scene_manager.switch("welcome")
        welcome = self._scene_manager.get_current_scene()

        while self._running and welcome.is_running():
            events = self._poll_events()
            if not self._check_quit(events):
                return (False, None)
            self._handle_resize_if_needed(events)
            self._handle_scene_events(events)
            self._scene_manager.update()
            self._scene_manager.render(self._window.get_surface())
            self._window.flip()
            self._window.tick(FPS)

        if hasattr(welcome, 'should_quit') and welcome.should_quit():
            return (False, None)
        if welcome.is_ready():
            self._current_user = welcome.get_username()
            self._selected_difficulty = welcome.get_difficulty()
            save_data = self._check_and_get_saved_game(self._current_user)
            return (True, save_data)
        return (True, None)

    def _run_game_flow(self) -> str:
        self._logger.info(f"Starting game flow: difficulty={self._selected_difficulty}, user={self._current_user}")
        self._scene_manager.switch("game",
                                  difficulty=self._selected_difficulty,
                                  username=self._current_user or 'Guest')

        current_scene = self._scene_manager.get_current_scene()
        if self._pending_save_data and isinstance(current_scene, GameScene):
            current_scene.restore_from_save(self._pending_save_data)
            self._pending_save_data = None
            self._logger.info("Game restored from pending save data")

        while self._running:
            escape_handled = False
            current_scene = self._scene_manager.get_current_scene()

            events = self._poll_events()
            if not self._check_quit(events):
                if isinstance(current_scene, GameScene):
                    self._save_game_on_quit(current_scene)
                self._logger.info("Game flow ended: quit")
                return "quit"
            self._handle_resize_if_needed(events)

            if isinstance(current_scene, GameScene):
                result = self._handle_pause_toggle(events, current_scene)
                dispatched = self._dispatch_pause_result(result, current_scene)
                if dispatched:
                    return dispatched
                escape_handled = result == "resume"

            self._handle_scene_events(events, escape_handled)

            # Check for pause requests triggered by mouse click
            if isinstance(current_scene, GameScene) and not escape_handled:
                if not current_scene.is_homecoming_locked() and current_scene.consume_pause_request():
                    current_scene.pause()
                    action = self._show_pause_menu(current_scene)
                    result = self._dispatch_pause_action(action, current_scene, from_mouse=True)
                    if result:
                        return result

            self._scene_manager.update()
            self._scene_manager.render(self._window.get_surface())
            self._window.flip()
            self._window.tick(FPS)

            if isinstance(current_scene, GameScene) and current_scene.is_game_over():
                self._clear_saved_game()
                result = self._handle_game_over(current_scene)
                if result:
                    return "main_menu"
                else:
                    return "quit"

        return "quit"

    def _poll_events(self) -> List[pygame.event.Event]:
        return pygame.event.get()

    def _check_quit(self, events: List[pygame.event.Event]) -> bool:
        for event in events:
            if event.type == pygame.QUIT:
                self._running = False
                return False
        return True

    def _handle_resize_if_needed(self, events: List[pygame.event.Event]) -> None:
        for event in events:
            if event.type == pygame.VIDEORESIZE:
                self._window.resize(event.w, event.h)
                self._handle_resize(event.w, event.h)

    def _handle_pause_toggle(self, events: List[pygame.event.Event], game_scene: GameScene) -> str:
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
    ) -> Optional[str]:
        if result in ("resume", "none"):
            return None
        if result == "main_menu":
            self._clear_saved_game()
            self._logger.info("Game flow ended%s: main_menu", source)
            return "main_menu"
        if result == "save_and_quit":
            saved = self._save_and_quit(current_scene)
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
    ) -> Optional[str]:
        result = self._pause_action_result(action, current_scene)
        if result == "main_menu":
            current_scene.resume()
        source = " from pause" if from_mouse else ""
        return self._dispatch_pause_result(result, current_scene, source=source)

    def _show_pause_menu(self, game_scene: GameScene) -> PauseAction:
        pause_scene = self._scene_manager.get_scene("pause")
        if not pause_scene:
            return PauseAction.QUIT
        pause_scene.enter()

        while pause_scene.running:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self._running = False
                    return PauseAction.QUIT
                if event.type == pygame.VIDEORESIZE:
                    self._window.resize(event.w, event.h)
                    self._handle_resize(event.w, event.h)
            for event in events:
                pause_scene.handle_events(event)
            pause_scene.update()
            pause_scene.render(self._window.get_surface())
            self._window.flip()
            self._window.tick(FPS)

        result = pause_scene.get_result()
        pause_scene.exit()
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

        exit_scene.enter(saved=saved, difficulty=self._selected_difficulty)

        while exit_scene.is_running():
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self._running = False
                    return "quit"
                if event.type == pygame.VIDEORESIZE:
                    self._window.resize(event.w, event.h)
                    self._handle_resize(event.w, event.h)
                exit_scene.handle_events(event)
            exit_scene.update()
            exit_scene.render(self._window.get_surface())
            self._window.flip()
            self._window.tick(FPS)

        result = exit_scene.get_result()
        exit_scene.exit()
        if result == ExitConfirmAction.RETURN_TO_MENU:
            if not saved:
                self._clear_saved_game()
            return "main_menu"
        elif result == ExitConfirmAction.START_NEW_GAME:
            self._clear_saved_game()
            return "restart"
        else:
            if not saved:
                self._clear_saved_game()
            return "quit"

    def _handle_game_over(self, game_scene: GameScene) -> bool:
        final_score = game_scene.score
        kills = game_scene.get_kill_count()
        boss_kills = game_scene.get_boss_kill_count()
        self._update_user_stats(final_score, kills)

        death_scene = self._scene_manager.get_scene("death")
        if not death_scene:
            return False

        death_scene.enter(score=final_score, kills=kills, boss_kills=boss_kills, username=self._current_user)

        while death_scene.is_running():
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self._running = False
                    death_scene.running = False
                    break
                if event.type == pygame.VIDEORESIZE:
                    self._window.resize(event.w, event.h)
                    self._handle_resize(event.w, event.h)
                death_scene.handle_events(event)

            death_scene.update()
            death_scene.render(self._window.get_surface())
            self._window.flip()
            self._window.tick(FPS)

        result = death_scene.get_result()
        death_scene.exit()
        return result == 'return_to_menu'

    def _update_user_stats(self, score: int, kills: int) -> Optional[int]:
        if not self._current_user or not self._user_db:
            return None
        try:
            user_data = self._user_db.get_user_data(self._current_user)
            new_high = max(score, user_data.get('high_score', 0))
            self._user_db.update_user_data(self._current_user, {
                'high_score': new_high,
                'total_kills': user_data.get('total_kills', 0) + kills,
                'games_played': user_data.get('games_played', 0) + 1
            })
            return new_high
        except DatabaseError:
            self._logger.warning("Failed to update user stats", exc_info=True)
            return None

    def _handle_scene_events(self, events: List[pygame.event.Event], skip_escape: bool = False) -> None:
        for event in events:
            if skip_escape and hasattr(event, 'key') and event.key == pygame.K_ESCAPE:
                continue
            self._scene_manager.handle_events(event)

    def _handle_resize(self, width: int, height: int) -> None:
        set_screen_size(width, height)

    def _check_and_get_saved_game(self, username: str) -> Optional[GameSaveData]:
        if not username:
            return None
        for persistence_manager in self._candidate_persistence_managers(username):
            save_data = persistence_manager.load_game()
            if save_data and save_data.username == username:
                return save_data
        return None

    def _perform_save(self, game_scene: GameScene) -> bool:
        if not game_scene:
            return False
        save_data = game_scene.create_save_data()
        if not save_data:
            return False
        if not game_scene.is_mothership_docked():
            save_data.is_in_mothership = False
        persistence_manager = PersistenceManager(save_dir=self._save_dir, username=save_data.username)
        return persistence_manager.save_game(save_data)

    def _save_game_on_quit(self, game_scene: GameScene) -> None:
        if not self._perform_save(game_scene):
            self._logger.warning("Failed to save game during quit")

    def _clear_saved_game(self) -> None:
        for persistence_manager in self._candidate_persistence_managers(self._current_user):
            save_data = persistence_manager.load_game()
            if save_data and save_data.username == self._current_user:
                persistence_manager.delete_save()

    def _candidate_persistence_managers(self, username: str) -> list[PersistenceManager]:
        return [
            PersistenceManager(save_dir=self._save_dir, username=username),
            PersistenceManager(save_dir=self._save_dir),
        ]

    def _save_and_quit(self, game_scene: GameScene) -> bool:
        saved = self._perform_save(game_scene)
        if not saved:
            self._logger.warning("Failed to save game before quitting")
        return saved

    def _quit_without_saving(self) -> None:
        self._clear_saved_game()
