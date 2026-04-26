"""Constants access layer — breaks circular dependency between game.constants and entities.

This module provides a lazy accessor for GAME_CONSTANTS that avoids the circular
import that would occur if entities/player.py or entities/enemy.py imported
directly from airwar.game.constants.
"""
_GAME_CONSTANTS_REF = None


def get_game_constants():
    """Return the global GAME_CONSTANTS instance.

    This function exists to break the circular import between entities modules
    and game.constants. Importing GAME_CONSTANTS directly in player.py or enemy.py
    would create a cycle because those modules are imported by game.constants.

    The import is deferred until first access to avoid loading game.constants
    at module load time.
    """
    global _GAME_CONSTANTS_REF
    if _GAME_CONSTANTS_REF is None:
        from airwar.game.constants import GAME_CONSTANTS
        _GAME_CONSTANTS_REF = GAME_CONSTANTS
    return _GAME_CONSTANTS_REF
