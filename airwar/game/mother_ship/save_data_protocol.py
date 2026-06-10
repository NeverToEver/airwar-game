"""Save data Protocol — formal contract for game save data structures.

47 模糊点 F.I4 (Phase 6 §6.2): this module formalizes the save-data
contract as a runtime-checkable :class:`Protocol`, similar to
:class:`airwar.game.protocols.LockRequestProtocol`. The Protocol
describes the structural shape of any object that can be serialized
to disk and reloaded by the persistence manager. The concrete
:class:`airwar.game.mother_ship.mother_ship_state.GameSaveData`
dataclass already satisfies this contract by structural typing, so
no runtime changes are needed for production code; this Protocol is
here so test doubles and alternative save formats (e.g. cloud
saves, replay exports) can declare conformance explicitly.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ISaveData(Protocol):
    """Structural contract for serializable game save data.

    F06 I4: this Protocol lets the persistence layer be tested with
    a duck-typed mock object (``isinstance(data, ISaveData) == True``)
    instead of having to import the concrete ``GameSaveData``
    dataclass. Production code passes the dataclass directly; tests
    can substitute a ``SimpleNamespace`` with the same attributes.

    The fields listed below are the minimum set required for a
    complete save: scoring, progression, player vitals, position,
    mothership status, and metadata (version, timestamp,
    difficulty, username). New fields are non-breaking as long as
    the ``from_dict`` / ``to_dict`` round-trip still works.
    """

    # --- Metadata ---
    version: int
    timestamp: float
    difficulty: str
    username: str

    # --- Progression ---
    score: int
    cycle_count: int
    kill_count: int
    boss_kill_count: int
    requisition_points: int

    # --- Player vitals ---
    player_health: int
    player_max_health: int
    player_x: float
    player_y: float
    is_in_mothership: bool
    mothership_state: str
    mothership_cooldown_progress: float
    mothership_stay_progress: float

    # --- Talent / loadout ---
    unlocked_buffs: list[str]
    buff_levels: dict[str, int]
    earned_buff_levels: dict[str, int]
    talent_loadout: dict[str, str]

    # --- Round-trip API ---
    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dict."""
        ...

    @classmethod
    def from_dict(cls, data: dict) -> ISaveData:
        """Deserialize from a dict (raises :class:`SaveDataCorruptedError` on bad data)."""
        ...


__all__ = ["ISaveData"]
