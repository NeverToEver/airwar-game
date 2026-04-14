from airwar.scenes import SceneManager, GameScene, MenuScene, PauseScene, LoginScene
from airwar.utils.database import UserDB
from airwar.window import create_window


class Game:
    def __init__(self):
        from airwar.window import create_window
        from airwar.config import set_screen_size

        self.window = create_window(1200, 700, 'Air War - 飞机大战', resizable=True)
        self.screen_width = self.window.get_width()
        self.screen_height = self.window.get_height()
        set_screen_size(self.screen_width, self.screen_height)

        self.running = True
        self._quit_to_menu_requested = False
        self.db = UserDB()
        self.scene_manager = SceneManager()
        self.current_user = None
        self._register_scenes()

    def _handle_resize(self, width: int, height: int) -> None:
        self.screen_width = width
        self.screen_height = height
        set_screen_size(width, height)

    def _register_scenes(self) -> None:
        self.scene_manager.register("login", LoginScene())
        self.scene_manager.register("menu", MenuScene())
        self.scene_manager.register("game", GameScene())
        self.scene_manager.register("pause", PauseScene())

    def run(self) -> None:
        screen = self.window.get_surface()
        
        while self.running:
            self.scene_manager.switch("login")
            login_scene = self.scene_manager.get_current_scene()

            while login_scene.is_running() if hasattr(login_scene, 'is_running') else not login_scene.is_ready():
                quit, keydown, resize = self.window.process_events()
                if quit:
                    self.running = False
                    break
                if resize:
                    self._handle_resize(*resize)
                self.scene_manager.handle_events(self.window.get_events()[0] if self.window.get_events() else None)

                for event in self.window.get_events():
                    if event.type is not None:
                        self.scene_manager.handle_events(event)

                self.scene_manager.update()
                self.scene_manager.render(screen)
                self.window.flip()
                self.window.tick(60)

            if hasattr(login_scene, 'should_quit') and login_scene.should_quit():
                self.window.close()
                return

            if hasattr(login_scene, 'get_username') and login_scene.is_ready():
                self.current_user = login_scene.get_username()

            self.scene_manager.switch("menu")

            menu_running = True
            selected_difficulty = 'medium'
            back_to_login = False

            while menu_running and self.running:
                quit, keydown, resize = self.window.process_events()
                if quit:
                    self.running = False
                    break
                if resize:
                    self._handle_resize(*resize)

                for event in self.window.get_events():
                    self.scene_manager.handle_events(event)

                self.scene_manager.update()
                self.scene_manager.render(screen)
                self.window.flip()
                self.window.tick(60)

                if isinstance(self.scene_manager.get_current_scene(), MenuScene):
                    ms = self.scene_manager.get_current_scene()
                    if ms.should_go_back():
                        back_to_login = True
                        menu_running = False
                    elif ms.is_selection_confirmed():
                        selected_difficulty = ms.get_difficulty()
                        menu_running = False

            if not self.running:
                break

            if back_to_login:
                continue

            self.scene_manager.switch("game", difficulty=selected_difficulty, username=self.current_user or 'Guest')
            game_scene = self.scene_manager.get_current_scene()

            while self.running:
                escape_handled = False
                current_scene = self.scene_manager.get_current_scene()

                quit, keydown, resize = self.window.process_events()
                if quit:
                    self.running = False
                    break
                if resize:
                    self._handle_resize(*resize)

                if keydown and keydown.key == 27:
                    if isinstance(current_scene, GameScene):
                        if current_scene.is_paused():
                            current_scene.resume()
                        else:
                            current_scene.pause()
                            self._show_pause_menu()
                            escape_handled = True

                if not self.running:
                    break

                for event in self.window.get_events():
                    if escape_handled and hasattr(event, 'key') and event.key == 27:
                        continue
                    self.scene_manager.handle_events(event)

                self.scene_manager.update()
                self.scene_manager.render(screen)
                self.window.flip()
                self.window.tick(60)

                if isinstance(self.scene_manager.get_current_scene(), GameScene):
                    if self.scene_manager.get_current_scene().is_game_over():
                        self._handle_game_over()
                        self.running = False
                        break

                if self._quit_to_menu_requested:
                    self._quit_to_menu_requested = False
                    self.scene_manager.switch("menu")
                    break

        self.window.close()

    def _show_pause_menu(self) -> None:
        screen = self.window.get_surface()
        pause_scene = self.scene_manager._scenes.get("pause")
        if pause_scene:
            pause_scene.on_resume = lambda: self.scene_manager.get_current_scene().resume()
            pause_scene.on_quit = self._quit_to_menu
            pause_scene.enter()

        while pause_scene.is_paused() if hasattr(pause_scene, 'is_paused') else pause_scene.running:
            quit, keydown, resize = self.window.process_events()
            if quit:
                self.running = False
                return
            if resize:
                self._handle_resize(*resize)

            for event in self.window.get_events():
                pause_scene.handle_events(event)

            pause_scene.update()
            pause_scene.render(screen)
            self.window.flip()
            self.window.tick(60)

    def _handle_game_over(self) -> None:
        game_scene = self.scene_manager.get_current_scene()
        final_score = game_scene.get_score()
        kills = game_scene.get_kills()

        if self.current_user:
            user_data = self.db.get_user_data(self.current_user)
            self.db.update_user_data(self.current_user, {
                'high_score': max(final_score, user_data.get('high_score', 0)),
                'total_kills': user_data.get('total_kills', 0) + kills,
                'games_played': user_data.get('games_played', 0) + 1
            })

        self._show_game_over_screen(final_score, kills)

    def _show_game_over_screen(self, score: int, kills: int) -> None:
        import pygame
        screen = self.window.get_surface()
        pygame.font.init()

        font_large = pygame.font.Font(None, 72)
        font_medium = pygame.font.Font(None, 36)
        font_small = pygame.font.Font(None, 28)

        scale = self.screen_width / 800
        font_large = pygame.font.Font(None, int(72 * scale))
        font_medium = pygame.font.Font(None, int(36 * scale))
        font_small = pygame.font.Font(None, int(28 * scale))

        waiting = True
        return_to_menu = False
        while waiting:
            for event in self.window.get_events():
                if event.type == pygame.QUIT:
                    self.running = False
                    waiting = False
                elif event.type == pygame.VIDEORESIZE:
                    self._handle_resize(event.w, event.h)
                    scale = self.screen_width / 800
                    font_large = pygame.font.Font(None, int(72 * scale))
                    font_medium = pygame.font.Font(None, int(36 * scale))
                    font_small = pygame.font.Font(None, int(28 * scale))
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        return_to_menu = True
                        waiting = False
                    elif event.key == pygame.K_ESCAPE:
                        self.running = False
                        waiting = False

            if not self.running:
                break

            screen.fill((10, 10, 30))

            title = font_large.render("GAME OVER", True, (255, 80, 80))
            screen.blit(title, title.get_rect(center=(self.screen_width // 2, int(150 * scale))))

            score_text = font_medium.render(f"SCORE: {score}", True, (255, 255, 255))
            screen.blit(score_text, score_text.get_rect(center=(self.screen_width // 2, int(280 * scale))))

            kills_text = font_medium.render(f"KILLS: {kills}", True, (200, 200, 100))
            screen.blit(kills_text, kills_text.get_rect(center=(self.screen_width // 2, int(330 * scale))))

            if self.current_user:
                user_data = self.db.get_user_data(self.current_user)
                high_score = user_data.get('high_score', 0)
                hs_text = font_small.render(f"HIGH SCORE: {high_score}", True, (100, 255, 150))
                screen.blit(hs_text, hs_text.get_rect(center=(self.screen_width // 2, int(400 * scale))))

            hint = font_small.render("ENTER to menu | ESC to quit", True, (100, 100, 150))
            screen.blit(hint, hint.get_rect(center=(self.screen_width // 2, int(500 * scale))))

            self.window.flip()
            self.window.tick(60)

        if return_to_menu:
            self.scene_manager.switch("menu")

    def _quit_to_menu(self) -> None:
        self._quit_to_menu_requested = True