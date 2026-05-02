"""Event bus — publish/subscribe messaging for mothership events."""
import logging
from typing import Dict, List, Callable
from .interfaces import IEventBus


class EventBus(IEventBus):
    """Event bus — publish/subscribe messaging for mothership events.
    
        Decouples mothership components by providing typed event channels
        for docking progress, state changes, and save completion.
        """
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event: str, callback: Callable) -> None:
        if event not in self._subscribers:
            self._subscribers[event] = []
        if callback not in self._subscribers[event]:
            self._subscribers[event].append(callback)

    def unsubscribe(self, event: str, callback: Callable) -> None:
        if event in self._subscribers:
            self._subscribers[event] = [
                cb for cb in self._subscribers[event] if cb != callback
            ]

    def publish(self, event: str, **kwargs) -> None:
        if event in self._subscribers:
            for callback in self._subscribers[event]:
                try:
                    callback(**kwargs)
                except Exception as e:
                    logging.error(f"Event callback error [{event}]: {e}")
