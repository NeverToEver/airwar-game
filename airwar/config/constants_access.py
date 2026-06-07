"""Constants access layer — breaks circular dependency between game.constants and entities.

This module provides a lazy accessor for ``GAME_CONSTANTS`` that avoids the
circular import that would occur if :mod:`airwar.entities` (player / enemy)
imported directly from :mod:`airwar.game.constants`.

Layer-violation status (Phase 2)
--------------------------------
The lazy ``from airwar.game.constants import GAME_CONSTANTS`` inside
``get_game_constants`` is a "push-pull" hybrid: the *config* package
reaches *into* the *game* package on first call. The design document
proposed a fully push-based model (``Game`` calls
``register_constants`` at startup) but the push model requires every
Game-derived scene to remember to call it; the lazy pull is simpler
and works because the access is deferred until first use, by which
time :mod:`airwar.game.constants` is fully initialised.

The ``_GAME_CONSTANTS_REF`` slot is intentionally module-private; no
config-side code can read it without going through this function, so
the *de facto* dependency direction is::

    airwar.config  ─┐
                    │  get_game_constants()  (lazy)
                    ▼
    airwar.game    ─┘

The strict, no-cross-layer goal can be revisited later if a clean
push-based replacement is needed.
"""

_GAME_CONSTANTS_REF = None


def get_game_constants():
    """Return the global ``GAME_CONSTANTS`` instance.

    The import is deferred until first access to avoid loading
    :mod:`airwar.game.constants` at module-load time. See the module
    docstring for the layer-violation rationale.
    """
    global _GAME_CONSTANTS_REF
    if _GAME_CONSTANTS_REF is None:
        from airwar.game.constants import GAME_CONSTANTS

        _GAME_CONSTANTS_REF = GAME_CONSTANTS
    return _GAME_CONSTANTS_REF
