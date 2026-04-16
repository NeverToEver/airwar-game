from typing import Dict, List, Callable, Any
from .interfaces import IEventBus


class EventBus(IEventBus):
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
                    print(f"Event callback error [{event}]: {e}")
