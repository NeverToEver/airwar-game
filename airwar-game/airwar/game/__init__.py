__all__ = ['Game']


def __getattr__(name):
    if name == 'Game':
        from airwar.game.game import Game
        return Game
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(__all__)
