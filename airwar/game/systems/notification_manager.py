import pygame
from typing import Optional


class NotificationManager:
    def __init__(self, duration: int = 90):
        self.current_notification: Optional[str] = None
        self.timer: int = 0
        self.duration = duration
        pygame.font.init()
        self.notif_font = pygame.font.Font(None, 32)

    def show(self, message: str, duration: int = None) -> None:
        self.current_notification = message
        self.timer = duration or self.duration

    def update(self) -> None:
        if self.timer > 0:
            self.timer -= 1

    def render(self, surface: pygame.Surface) -> None:
        if self.timer > 0 and self.current_notification:
            alpha = min(255, self.timer * 4)
            color = (0, 255, 150) if alpha > 150 else (150, 255, 200)
            text = self.notif_font.render(self.current_notification, True, color)
            text.set_alpha(alpha)
            x = surface.get_width() // 2 - text.get_width() // 2
            y = 100
            surface.blit(text, (x, y))
