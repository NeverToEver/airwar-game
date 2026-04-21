from typing import Optional, List
import pygame
from airwar.scenes import SceneManager, GameScene, MenuScene
from airwar.scenes.scene import PauseAction, ExitConfirmAction
from airwar.game.mother_ship import PersistenceManager, GameSaveData


class SceneDirector:
    def __init__(self, window, scene_manager: SceneManager, user_db=None):
        self._window = window
        self._scene_manager = scene_manager
        self._user_db = user_db
        self._running = True
        self._current_user: Optional[str] = None
        self._selected_difficulty: str = 'medium'
        self._pending_save_data = None

    @property
    def current_user(self) -> Optional[str]:
        return self._current_user

    def run(self) -> None:
        self._running = True
        while self._running:
            login_result, save_data = self._run_login_flow()
            if not login_result:
                break
            self._pending_save_data = save_data
            if not self._run_menu_flow():
                continue
            result = self._run_game_flow()
            if result == "quit":
                break
            if result == "main_menu":
                self._pending_save_data = None
                continue
            if result == "restart":
                self._pending_save_data = None
                continue

    def stop(self) -> None:
        self._running = False

    def _run_login_flow(self) -> tuple:
        self._scene_manager.switch("login")
        login_scene = self._scene_manager.get_current_scene()

        while self._running and (login_scene.is_running()
                if hasattr(login_scene, 'is_running') else not login_scene.is_ready()):
            events = self._poll_events()
            if not self._check_quit(events):
                return (False, None)
            self._handle_resize_if_needed(events)
            self._handle_scene_events(events)
            self._scene_manager.update()
            self._scene_manager.render(self._window.get_surface())
            self._window.flip()
            self._window.tick(60)

        if hasattr(login_scene, 'should_quit') and login_scene.should_quit():
            return (False, None)
        if hasattr(login_scene, 'get_username') and login_scene.is_ready():
            self._current_user = login_scene.get_username()
            save_data = self._check_and_get_saved_game(self._current_user)
            return (True, save_data)
        return (True, None)

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
                    selected_option = ms.get_selected_option()
                    if selected_option == 'tutorial':
                        self._run_tutorial_flow()
                        self._scene_manager.switch("menu")
                    else:
                        self._selected_difficulty = ms.get_difficulty()
                        break

        return not back_to_login

    def _run_tutorial_flow(self) -> None:
        """Run the tutorial flow."""
        self._scene_manager.switch("tutorial")
        tutorial_scene = self._scene_manager.get_current_scene()
        pygame.event.set_grab(True)
        
        try:
            while tutorial_scene.is_running() and self._running:
                events = self._poll_events()
                
                if not self._check_quit(events):
                    return
                self._handle_resize_if_needed(events)
                
                for event in events:
                    tutorial_scene.handle_events(event)
                
                tutorial_scene.update()
                tutorial_scene.render(self._window.get_surface())
                self._window.flip()
                self._window.tick(60)
                
                if tutorial_scene.should_quit():
                    break
        finally:
            pygame.event.set_grab(False)
            tutorial_scene.exit()
            self._window.get_surface().fill((0, 0, 0))
            pygame.display.flip()
            pygame.time.delay(100)

    def _run_game_flow(self) -> str:
        self._scene_manager.switch("game",
                                  difficulty=self._selected_difficulty,
                                  username=self._current_user or 'Guest')

        current_scene = self._scene_manager.get_current_scene()
        if self._pending_save_data and isinstance(current_scene, GameScene):
            current_scene.restore_from_save(self._pending_save_data)
            self._pending_save_data = None

        while self._running:
            escape_handled = False
            current_scene = self._scene_manager.get_current_scene()

            events = self._poll_events()
            if not self._check_quit(events):
                if isinstance(current_scene, GameScene):
                    self._save_game_on_quit(current_scene)
                return "quit"
            self._handle_resize_if_needed(events)

            if isinstance(current_scene, GameScene):
                result = self._handle_pause_toggle(events, current_scene)
                if result == "main_menu":
                    self._clear_saved_game()
                    return "main_menu"
                elif result == "save_and_quit":
                    self._save_and_quit(current_scene)
                    return self._show_exit_confirm(saved=True)
                elif result == "quit_without_saving":
                    return self._show_exit_confirm(saved=False)
                elif result == "quit":
                    self._save_and_quit(current_scene)
                    return self._show_exit_confirm(saved=True)
                escape_handled = result is True

            self._handle_scene_events(events, escape_handled)
            self._scene_manager.update()
            self._scene_manager.render(self._window.get_surface())
            self._window.flip()
            self._window.tick(60)

            if isinstance(current_scene, GameScene):
                if current_scene.is_game_over():
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
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if game_scene.is_paused():
                    game_scene.resume()
                    return "resume"
                else:
                    game_scene.pause()
                    action = self._show_pause_menu(game_scene)
                    if action == PauseAction.RESUME:
                        game_scene.resume()
                        return "resume"
                    elif action == PauseAction.MAIN_MENU:
                        return "main_menu"
                    elif action == PauseAction.SAVE_AND_QUIT:
                        return "save_and_quit"
                    elif action == PauseAction.QUIT_WITHOUT_SAVING:
                        return "quit_without_saving"
                    elif action == PauseAction.QUIT:
                        return "save_and_quit"
        return "none"

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

    def _show_exit_confirm(self, saved: bool) -> str:
        """显示退出确认菜单

        在玩家选择保存退出或不保存退出后显示，
        允许玩家选择返回主菜单、开始新游戏或真正退出游戏。

        Args:
            saved: 是否已经保存了游戏进度

        Returns:
            str: 'main_menu' 返回主菜单, 'restart' 重新开始, 'quit' 退出游戏
        """
        exit_scene = self._scene_manager._scenes.get("exit_confirm")
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
            self._window.tick(60)

        result = exit_scene.get_result()
        if result == ExitConfirmAction.RETURN_TO_MENU:
            self._clear_saved_game()
            return "main_menu"
        elif result == ExitConfirmAction.START_NEW_GAME:
            self._clear_saved_game()
            return "restart"
        else:
            return "quit"

    def _handle_game_over(self, game_scene: GameScene) -> bool:
        final_score = game_scene.score
        kills = game_scene.cycle_count
        high_score = self._update_user_stats(final_score, kills)

        death_scene = self._scene_manager._scenes.get("death")
        if not death_scene:
            return False

        death_scene.enter(score=final_score, kills=kills, username=self._current_user)

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
            self._window.tick(60)

        result = death_scene.get_result()
        return result == 'return_to_menu'

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

    def _check_and_get_saved_game(self, username: str) -> Optional[GameSaveData]:
        if not username:
            return None
        persistence_manager = PersistenceManager()
        save_data = persistence_manager.load_game()
        if save_data and save_data.username == username:
            return save_data
        return None

    def _save_game_on_quit(self, game_scene: GameScene) -> None:
        if not game_scene or not game_scene._mother_ship_integrator:
            return

        save_data = game_scene._mother_ship_integrator.create_save_data()
        if save_data:
            if not game_scene._mother_ship_integrator.is_docked():
                save_data.is_in_mothership = False
            persistence_manager = PersistenceManager()
            persistence_manager.save_game(save_data)

    def _clear_saved_game(self) -> None:
        persistence_manager = PersistenceManager()
        persistence_manager.delete_save()

    def _save_and_quit(self, game_scene: GameScene) -> None:
        """保存游戏并退出

        将当前游戏状态保存到文件，然后退出游戏。
        保存内容包括分数、击杀数、buff效果、玩家生命值等所有进度数据。

        Args:
            game_scene: 当前游戏场景实例
        """
        if not game_scene or not game_scene._mother_ship_integrator:
            return

        save_data = game_scene._mother_ship_integrator.create_save_data()
        if save_data:
            if not game_scene._mother_ship_integrator.is_docked():
                save_data.is_in_mothership = False
            persistence_manager = PersistenceManager()
            persistence_manager.save_game(save_data)

    def _quit_without_saving(self) -> None:
        """清除存档并退出，不保存当前进度

        删除已存在的存档文件，确保下次进入游戏时从头开始。
        用于玩家明确选择不保存当前进度的场景。
        """
        self._clear_saved_game()
