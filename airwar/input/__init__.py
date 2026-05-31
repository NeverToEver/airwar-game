"""Input package — keyboard/mouse input handling and coordination."""
from .input_handler import InputHandler, MockInputHandler, PygameInputHandler

__all__ = ['InputHandler', 'PygameInputHandler', 'MockInputHandler']
