"""On-screen notification display and lifecycle management."""
import logging
import pygame
from airwar.utils.fonts import get_cjk_font
from typing import Optional
from ..constants import GAME_CONSTANTS

logger = logging.getLogger(__name__)


class NotificationManager:
    """Notification manager — on-screen message display and lifecycle.
    
        Manages timed notification messages that appear during gameplay
        (score popups, boss warnings, reward notifications).
    
        Attributes:
            current_notification: Currently displayed notification text.
            timer: Frames remaining for the current notification.
        """
    def __init__(self, duration: int = 90):
        self.current_notification: Optional[str] = None
        self.timer: int = 0
        self.duration = duration
        pygame.font.init()
        self.notif_font = get_cjk_font(32)

    def show(self, message: str, duration: int = None) -> None:
        self.current_notification = message
        self.timer = duration or self.duration

    def update(self) -> None:
        if self.timer > 0:
            self.timer -= 1

    def render(self, surface: pygame.Surface) -> None:
        if self.timer > 0 and self.current_notification:
            try:
                alpha = min(255, self.timer * 4)
                color = (0, 255, 150) if alpha > GAME_CONSTANTS.TIMING.NOTIFICATION_ALPHA_THRESHOLD else (150, 255, 200)
                text = self.notif_font.render(self.current_notification, True, color)
                text.set_alpha(alpha)
                x = surface.get_width() // 2 - text.get_width() // 2
                y = 100
                surface.blit(text, (x, y))
            except pygame.error:
                logger.warning("Failed to render notification text")
