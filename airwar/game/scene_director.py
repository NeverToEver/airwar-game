from typing import Optional, List
import pygame
from airwar.scenes import SceneManager, GameScene, MenuScene
from airwar.scenes.scene import PauseAction
from airwar.ui.game_over_screen import GameOverScreen, ScreenAction


class SceneDirector:
    def __init__(self, window, scene_manager: SceneManager, game_over_screen: GameOverScreen,
                 user_db=None):
        self._window = window
        self._scene_manager = scene_manager
        self._game_over_screen = game_over_screen
        self._user_db = user_db
        self._running = True
        self._current_user: Optional[str] = None
        self._selected_difficulty: str = 'medium'

    @property
    def current_user(self) -> Optional[str]:
        return self._current_user

    def run(self) -> None:
        self._running = True
        while self._running:
            if not self._run_login_flow():
                break
            if not self._run_menu_flow():
                continue
            if not self._run_game_flow():
                break

    def stop(self) -> None:
        self._running = False

    def _run_login_flow(self) -> bool:
        self._scene_manager.switch("login")
        login_scene = self._scene_manager.get_current_scene()

        while self._running and (login_scene.is_running()
                if hasattr(login_scene, 'is_running') else not login_scene.is_ready()):
            events = self._poll_events()
            if not self._check_quit(events):
                return False
            self._handle_resize_if_needed(events)
            self._handle_scene_events(events)
            self._scene_manager.update()
            self._scene_manager.render(self._window.get_surface())
            self._window.flip()
            self._window.tick(60)

        if hasattr(login_scene, 'should_quit') and login_scene.should_quit():
            return False
        if hasattr(login_scene, 'get_username') and login_scene.is_ready():
            self._current_user = login_scene.get_username()
        return True

    def _run_menu_flow(self) -> bool:
        self._scene_manager.switch("menu")
        back_to_login = False

        while self._running:
            events = self._poll_events()
            if not self._check_quit(events):
                return False
            self._handle_resize_if_needed(events)
            self._handle_scene_events(events)
            self._scene_manager.update()
            self._scene_manager.render(self._window.get_surface())
            self._window.flip()
            self._window.tick(60)

            if isinstance(self._scene_manager.get_current_scene(), MenuScene):
                ms = self._scene_manager.get_current_scene()
                if ms.should_go_back():
                    back_to_login = True
                    break
                if ms.is_selection_confirmed():
                    self._selected_difficulty = ms.get_difficulty()
                    break

        return not back_to_login

    def _run_game_flow(self) -> bool:
        self._scene_manager.switch("game",
                                  difficulty=self._selected_difficulty,
                                  username=self._current_user or 'Guest')

        while self._running:
            escape_handled = False
            current_scene = self._scene_manager.get_current_scene()

            events = self._poll_events()
            if not self._check_quit(events):
                return False
            self._handle_resize_if_needed(events)

            if isinstance(current_scene, GameScene):
                escape_handled = self._handle_pause_toggle(events, current_scene)

            self._handle_scene_events(events, escape_handled)
            self._scene_manager.update()
            self._scene_manager.render(self._window.get_surface())
            self._window.flip()
            self._window.tick(60)

            if isinstance(current_scene, GameScene):
                if current_scene.is_game_over():
                    return self._handle_game_over(current_scene)

        return True

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

    def _handle_pause_toggle(self, events: List[pygame.event.Event], game_scene: GameScene) -> bool:
        escape_handled = False
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if game_scene.is_paused():
                    game_scene.resume()
                    escape_handled = True
                else:
                    game_scene.pause()
                    action = self._show_pause_menu(game_scene)
                    if action == PauseAction.RESUME:
                        game_scene.resume()
                    elif action == PauseAction.MAIN_MENU:
                        return False
                    elif action == PauseAction.QUIT:
                        self._running = False
                        return True
                    escape_handled = True
        return escape_handled

    def _show_pause_menu(self, game_scene: GameScene) -> PauseAction:
        pause_scene = self._scene_manager._scenes.get("pause")
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
            self._window.tick(60)

        result = pause_scene.get_result()
        return result if result else PauseAction.RESUME

    def _handle_game_over(self, game_scene: GameScene) -> bool:
        final_score = game_scene.get_score()
        kills = game_scene.get_kills()
        high_score = self._update_user_stats(final_score, kills)
        action = self._game_over_screen.show(
            final_score, kills, self._current_user, high_score)
        return action == ScreenAction.RETURN_TO_MENU

    def _update_user_stats(self, score: int, kills: int) -> Optional[int]:
        if not self._current_user or not self._user_db:
            return None
        user_data = self._user_db.get_user_data(self._current_user)
        new_high = max(score, user_data.get('high_score', 0))
        self._user_db.update_user_data(self._current_user, {
            'high_score': new_high,
            'total_kills': user_data.get('total_kills', 0) + kills,
            'games_played': user_data.get('games_played', 0) + 1
        })
        return new_high

    def _handle_scene_events(self, events: List[pygame.event.Event], skip_escape: bool = False) -> None:
        for event in events:
            if skip_escape and hasattr(event, 'key') and event.key == pygame.K_ESCAPE:
                continue
            self._scene_manager.handle_events(event)

    def _handle_resize(self, width: int, height: int) -> None:
        from airwar.config import set_screen_size
        set_screen_size(width, height)
