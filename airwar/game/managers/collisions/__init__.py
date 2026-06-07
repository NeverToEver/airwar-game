"""Collision strategies — Phase 4 god-class split (2.5).

Splits the 33-method ``CollisionController`` god class into 4 focused
strategy classes:

* :class:`BulletVsEntitiesStrategy` -- player bullets vs enemies + boss,
  Rust spatial-hash acceleration.
* :class:`EnemyBulletVsPlayerStrategy` -- enemy bullets vs player,
  Rust spatial-hash acceleration.
* :class:`BossVsPlayerStrategy` -- boss body vs player body.
* :class:`CollisionEventDispatcher` -- ``CollisionEvent`` type + the
  player-hit handler closure factory.

The legacy ``CollisionController`` (in ``airwar/game/managers/``) owns
one instance of each strategy and delegates the public API to them.
Callers import through the parent module path to remain backward
compatible:

    from airwar.game.managers.collision_controller import CollisionController

The strategies here are also importable directly for fine-grained use:

    from airwar.game.managers.collisions import (
        BulletVsEntitiesStrategy,
        EnemyBulletVsPlayerStrategy,
        BossVsPlayerStrategy,
        CollisionEventDispatcher,
        CollisionEvent,
    )
"""

from .boss_vs_player import BossVsPlayerStrategy
from .bullet_vs_entities import BulletVsEntitiesStrategy
from .collision_event_dispatcher import CollisionEvent, CollisionEventDispatcher
from .enemy_bullet_vs_player import EnemyBulletVsPlayerStrategy

__all__ = [
    "BossVsPlayerStrategy",
    "BulletVsEntitiesStrategy",
    "CollisionEvent",
    "CollisionEventDispatcher",
    "EnemyBulletVsPlayerStrategy",
]
