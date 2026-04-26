"""Input package — keyboard/mouse input handling and coordination."""
from .input_handler import InputHandler, PygameInputHandler, MockInputHandler

__all__ = ['InputHandler', 'PygameInputHandler', 'MockInputHandler']
