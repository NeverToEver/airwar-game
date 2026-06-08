"""Property-based tests for EVENT_REGISTRY and UpdatePipeline invariants.

Two distinct registries, both designed in the Phase 3 refactor to be the
single source of truth for their respective surfaces:

* ``EVENT_REGISTRY`` in ``airwar.game.mother_ship.event_bus`` documents
  every event the mothership event bus can publish/subscribe to.
* ``PIPELINE_ORDER`` / ``SHORT_CIRCUIT_STEPS`` in
  ``airwar.scenes.update_pipeline`` document the per-frame subsystem
  execution order.

The properties below pin the structural invariants of both registries
so future edits cannot silently break the contract.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from hypothesis import given, settings
from hypothesis import strategies as st

from airwar.game.mother_ship import event_bus as eb
from airwar.scenes.update_pipeline import (
    PIPELINE_ORDER,
    SHORT_CIRCUIT_STEPS,
    UpdatePipeline,
)

# ---------------------------------------------------------------------------
# Property 1: every EVENT_* constant is in EVENT_REGISTRY.
# ---------------------------------------------------------------------------


# Strategy: every public, all-caps attribute defined on the event_bus
# module that begins with EVENT_ must be in the registry.
def _collect_event_constants() -> list[str]:
    return [
        name
        for name in dir(eb)
        if name.startswith("EVENT_")
        and isinstance(getattr(eb, name), (str, type(eb.EVENT_STATE_CHANGED)))
        and name != "EVENT_STATE_CHANGED"  # EVENT_STATE_CHANGED is a str, no issue
    ]


def test_every_event_constant_is_in_registry() -> None:
    """EVENT_* constants on the module must all appear in EVENT_REGISTRY.

    This guards against the failure mode where a publisher adds a new
    EVENT_FOO constant and forgets to document it in the registry.
    """
    event_constants = _collect_event_constants()
    assert event_constants, "No EVENT_* constants found — collector may be broken"
    for name in event_constants:
        assert name in eb.EVENT_REGISTRY, f"{name} is defined on the event_bus module but missing from EVENT_REGISTRY"


# ---------------------------------------------------------------------------
# Property 2: every registry entry has payload_schema dict.
# ---------------------------------------------------------------------------


def test_every_registry_entry_has_payload_schema_dict() -> None:
    """Pinned: every value in EVENT_REGISTRY is a dict with a 'payload_schema' key."""
    for event_name, entry in eb.EVENT_REGISTRY.items():
        assert isinstance(entry, dict), f"{event_name}: entry is not a dict"
        assert "payload_schema" in entry, f"{event_name}: missing payload_schema"
        assert isinstance(entry["payload_schema"], dict), f"{event_name}: payload_schema is not a dict"


# ---------------------------------------------------------------------------
# Property 3: subscribers_known is a list of strings (or absent).
# ---------------------------------------------------------------------------


def test_every_registry_entry_has_subscribers_known_list() -> None:
    """Pinned: every entry has a 'subscribers_known' key whose value is a list of strings."""
    for event_name, entry in eb.EVENT_REGISTRY.items():
        assert "subscribers_known" in entry, f"{event_name}: missing subscribers_known"
        subs = entry["subscribers_known"]
        assert isinstance(subs, list), f"{event_name}: subscribers_known is not a list"
        for sub in subs:
            assert isinstance(sub, str), f"{event_name}: subscriber entry {sub!r} is not a string"


# ---------------------------------------------------------------------------
# Property 4: PIPELINE_ORDER has no duplicates.
# ---------------------------------------------------------------------------


def test_pipeline_order_has_no_duplicates() -> None:
    """Each subsystem name must appear at most once in PIPELINE_ORDER."""
    assert len(PIPELINE_ORDER) == len(set(PIPELINE_ORDER)), (
        f"Duplicate steps in PIPELINE_ORDER: {[s for s in PIPELINE_ORDER if PIPELINE_ORDER.count(s) > 1]}"
    )


# ---------------------------------------------------------------------------
# Property 5: SHORT_CIRCUIT_STEPS is a subset of PIPELINE_ORDER.
# ---------------------------------------------------------------------------


def test_short_circuit_steps_are_subset_of_pipeline_order() -> None:
    """Every short-circuit step must be a real step in PIPELINE_ORDER."""
    missing = SHORT_CIRCUIT_STEPS - set(PIPELINE_ORDER)
    assert not missing, f"Short-circuit steps not in PIPELINE_ORDER: {missing}"


# ---------------------------------------------------------------------------
# Property 6: execute() visits every step in PIPELINE_ORDER when all are
# registered and no short-circuit fires.
# ---------------------------------------------------------------------------


def test_execute_visits_every_pipeline_step_in_order() -> None:
    """If every step is registered with a non-short-circuiting callable,
    the last_executed list must equal PIPELINE_ORDER exactly.
    """
    pipeline = UpdatePipeline()
    for name in PIPELINE_ORDER:
        # Returning True (or None) means "continue the pipeline".
        pipeline.add_step(name, lambda n=name: True)

    pipeline.execute()

    assert pipeline.last_executed == PIPELINE_ORDER


@given(st.permutations(list(PIPELINE_ORDER)))
@settings(max_examples=20)
def test_execute_preserves_pipeline_order_regardless_of_registration_order(perm):
    """The registration order of steps does not affect execution order.

    The pipeline must always run steps in PIPELINE_ORDER, not in the
    order they were added.
    """
    pipeline = UpdatePipeline()
    for name in perm:
        pipeline.add_step(name, lambda: True)

    pipeline.execute()

    assert pipeline.last_executed == PIPELINE_ORDER


# ---------------------------------------------------------------------------
# Property 7: a step that returns False from a SHORT_CIRCUIT_STEPS entry
# must halt the pipeline at that point.
# ---------------------------------------------------------------------------


def test_short_circuit_halts_pipeline_at_step() -> None:
    """When a short-circuit step returns False, no later step runs."""
    pipeline = UpdatePipeline()
    halted_at: list[str] = []
    for name in PIPELINE_ORDER:
        if name in SHORT_CIRCUIT_STEPS:
            pipeline.add_step(name, lambda n=name: halted_at.append(n) or False)
        else:
            pipeline.add_step(name, lambda: True)

    # The first short-circuit step in PIPELINE_ORDER halts the rest.
    first_sc = next(n for n in PIPELINE_ORDER if n in SHORT_CIRCUIT_STEPS)

    pipeline.execute()

    assert halted_at == [first_sc]
    # Steps after the first short-circuit must not have run.
    first_sc_index = PIPELINE_ORDER.index(first_sc)
    expected_executed = PIPELINE_ORDER[: first_sc_index + 1]
    assert pipeline.last_executed == expected_executed


# ---------------------------------------------------------------------------
# Property 8: an unregistered step is silently skipped, not executed.
# ---------------------------------------------------------------------------


def test_unregistered_steps_are_skipped() -> None:
    """If a PIPELINE_ORDER step is not registered, execute() must skip it
    silently (per the docstring) and continue with the rest.
    """
    pipeline = UpdatePipeline()
    # Register only a subset.
    registered = ["aim_assist", "collision", "auto_save"]
    for name in registered:
        pipeline.add_step(name, lambda: True)

    pipeline.execute()

    # Only the registered steps should have been recorded.
    assert pipeline.last_executed == registered
    # The unwired-steps helper should report the missing names.
    unwired = pipeline.get_unwired_steps()
    assert set(unwired) == set(PIPELINE_ORDER) - set(registered)
