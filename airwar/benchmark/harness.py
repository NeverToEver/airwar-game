"""Frame-accurate driver for end-to-end game scenarios.

The :class:`ScenarioRunner` is the bridge between deterministic
test inputs and the live :class:`airwar.game.Game` main loop.  It:

* Bypasses the welcome flow (so a scenario can start directly in
  GameScene without UI input).
* Drives exactly N frames via a manual per-frame loop that
  posts synthetic events, calls ``scene.handle_events`` /
  ``scene.update`` / ``scene.render``, then captures a snapshot.
* Returns the full :class:`GameSnapshot` history so the test or the
  in-game launcher can post-hoc assert on any frame.

The runner does **not** spawn a thread; it runs the loop synchronously
in the calling thread.  This keeps the timing model simple: every
call to :meth:`advance` corresponds to exactly N game frames.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

import pygame

from .snapshot import GameSnapshot, take_snapshot


# Callback signature: ``(runner, frame) -> None``.  Used by scenarios
# to perform frame-conditional actions (e.g. pause at frame 10).
OnFrameCallback = Callable[["ScenarioRunner", int], None]

logger = logging.getLogger(__name__)


# -- Input specification ---------------------------------------------------


@dataclass(frozen=True)
class InputEvent:
    """A single synthetic event scheduled to be posted at ``at_frame``.

    ``factory`` is a zero-arg callable that returns a fresh
    :class:`pygame.event.Event`; we use a factory rather than a
    pre-built event because pygame events carry transient state and
    a fresh object is the only way to be sure the queue accepts it
    twice (e.g. KEYDOWN + KEYUP pairs).

    Attributes:
        at_frame: 0-indexed frame at which to post the event.
        factory: Zero-arg callable producing a :class:`pygame.event.Event`.
        description: Human-readable label for logs / failure reports.
    """

    at_frame: int
    factory: Callable[[], pygame.event.Event]
    description: str = ""


def _key_event(kind: int, key: int) -> pygame.event.Event:
    return pygame.event.Event(
        kind, {"key": key, "mod": 0, "unicode": "", "scancode": 0}
    )


def key_down(key: int, *, at: int = 0, description: str = "") -> InputEvent:
    """Build a :class:`InputEvent` for a key-down."""
    label = description or f"KEYDOWN({pygame.key.name(key)})"
    return InputEvent(at, lambda k=key: _key_event(pygame.KEYDOWN, k), label)


def key_up(key: int, *, at: int = 0, description: str = "") -> InputEvent:
    """Build a :class:`InputEvent` for a key-up."""
    label = description or f"KEYUP({pygame.key.name(key)})"
    return InputEvent(at, lambda k=key: _key_event(pygame.KEYUP, k), label)


def mouse_motion(pos: tuple[int, int], *, at: int = 0, description: str = "") -> InputEvent:
    """Build a :class:`InputEvent` for a mouse motion."""
    label = description or f"MOUSEMOTION{pos}"
    return InputEvent(
        at,
        lambda p=pos: pygame.event.Event(
            pygame.MOUSEMOTION, {"pos": p, "buttons": (0, 0, 0), "rel": (0, 0)}
        ),
        label,
    )


def mouse_click(pos: tuple[int, int], *, at: int = 0, button: int = 1, description: str = "") -> InputEvent:
    """Build a :class:`InputEvent` for a mouse button down + up pair.

    The mouse-click posts two events: ``MOUSEBUTTONDOWN`` then
    ``MOUSEBUTTONUP`` in the same frame.  Tests usually need both for
    the UI to register a click.
    """
    label = description or f"CLICK@{pos}"

    def _factory() -> pygame.event.Event:
        # Returning a single Event object; we need the runner to fire
        # the down and the up.  Use a sentinel list: the runner will
        # treat factories returning a list specially.
        return [  # type: ignore[return-value]
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": button}),
            pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": pos, "button": button}),
        ]

    return InputEvent(at, _factory, label)


# -- Result type -----------------------------------------------------------


@dataclass
class ScenarioResult:
    """Outcome of running a single scenario.

    Attributes:
        name: Scenario identifier (e.g. ``"death.basic"``).
        passed: ``True`` if the scenario completed without raising.
        snapshots: All snapshots taken during the run, in order.
        error: Exception instance if the scenario raised, else ``None``.
        message: Optional human-readable summary (e.g. "death scene reached at frame 47").
        frames_run: Total number of frames actually advanced.
    """

    name: str
    passed: bool
    snapshots: list[GameSnapshot] = field(default_factory=list)
    error: BaseException | None = None
    message: str = ""
    frames_run: int = 0

    def first(self, predicate: Callable[[GameSnapshot], bool]) -> GameSnapshot | None:
        """Return the first snapshot matching ``predicate``, or ``None``."""
        for snap in self.snapshots:
            if predicate(snap):
                return snap
        return None

    def last(self, predicate: Callable[[GameSnapshot], bool]) -> GameSnapshot | None:
        """Return the last snapshot matching ``predicate``, or ``None``."""
        for snap in reversed(self.snapshots):
            if predicate(snap):
                return snap
        return None

    def all_matching(self, predicate: Callable[[GameSnapshot], bool]) -> list[GameSnapshot]:
        """Return all snapshots matching ``predicate`` in order."""
        return [s for s in self.snapshots if predicate(s)]


# -- Runner -----------------------------------------------------------------


class ScenarioRunner:
    """Drive a real :class:`airwar.game.Game` instance frame-by-frame.

    Typical use from a scenario function::

        def scenario_death_basic(runner: ScenarioRunner) -> ScenarioResult:
            runner.feed(key_down(pygame.K_w, at=2))
            result = runner.advance(120)
            death = result.first(lambda s: s.scene_name == "death")
            assert death is not None, "expected to reach death scene"
            return ScenarioResult(name="death.basic", passed=True, snapshots=result)

    Or from a pytest test::

        def test_death(runner):
            res = scenario_death_basic(runner)
            assert res.passed, res.error
    """

    def __init__(
        self,
        game,
        *,
        seed: int = 42,
        max_frames: int = 1200,
        target_scene: str = "game",
        username: str = "benchmark",
        difficulty: str = "medium",
    ):
        self.game = game
        self.seed = seed
        self.max_frames = max_frames
        self.target_scene = target_scene
        self.username = username
        self.difficulty = difficulty
        self._frame = 0
        self._inputs: list[InputEvent] = []
        self._on_frame: list[OnFrameCallback] = []
        self._snapshots: list[GameSnapshot] = []
        self._start_time = time.monotonic()
        self._initialized = False
        self._init_error: BaseException | None = None

    # -- Setup -----------------------------------------------------------

    def setup(self) -> None:
        """Bypass welcome flow and switch directly to ``target_scene``.

        Mirrors the smoke-test trick at
        ``airwar/tests/smoke_real_machine.py:104-109``: monkey-patch
        the welcome flow to return success immediately, set the
        current user / difficulty, then call ``run()`` to start the
        game flow -- but the welcome part is a no-op so the director
        drops straight into the game scene.

        Idempotent: calling twice is a no-op.
        """
        if self._initialized:
            return
        if self._init_error is not None:
            raise self._init_error
        try:
            self._initialize()
            self._initialized = True
        except BaseException as exc:  # noqa: BLE001
            self._init_error = exc
            raise

    def _initialize(self) -> None:
        import random

        random.seed(self.seed)
        director = self.game._director
        director._current_user = self.username
        director._selected_difficulty = self.difficulty
        director._pending_save_data = None

        def _fake_welcome_flow() -> tuple:
            return (True, None)

        director._run_welcome_flow = _fake_welcome_flow  # type: ignore[assignment]

        # Force the target scene to enter so its update() can be called
        # directly.  We must NOT call director.run() because that would
        # block on the main loop; we drive frames ourselves.
        scene_manager = director._scene_manager
        # Run enter() on the target scene if it isn't already active.
        if scene_manager.get_current_scene_name() != self.target_scene:
            scene_manager.switch(self.target_scene)

    # -- Input scheduling -----------------------------------------------

    def feed(self, *events: InputEvent) -> None:
        """Schedule one or more :class:`InputEvent` to be posted during advance()."""
        self._inputs.extend(events)

    def feed_all(self, events: Iterable[InputEvent]) -> None:
        """Schedule an iterable of :class:`InputEvent`."""
        self._inputs.extend(events)

    def clear_inputs(self) -> None:
        """Discard all scheduled inputs (not yet posted)."""
        self._inputs.clear()

    def on_frame(self, callback: OnFrameCallback) -> None:
        """Register ``callback(runner, frame)`` to run every frame.

        Callbacks fire *after* the frame's events are dispatched and
        *after* the scene's update / render, so they observe a fully
        ticked state.  Useful for frame-conditional actions that the
        scene's normal event flow can't express (e.g. directly
        toggling a lock layer, or asserting the lock manager's state
        mid-run).
        """
        self._on_frame.append(callback)

    # -- Per-frame loop -------------------------------------------------

    def advance(self, n_frames: int = 1) -> list[GameSnapshot]:
        """Advance the game by exactly ``n_frames`` frames.

        Posts any scheduled events whose ``at_frame`` matches the
        current frame, then runs one frame of the per-scene loop
        (handle_events -> update -> render -> snapshot).

        Returns:
            The new snapshots taken during this call, oldest first.
        """
        self.setup()
        director = self.game._director
        scene_manager = director._scene_manager
        viewport = director._viewport
        new_snaps: list[GameSnapshot] = []

        for _ in range(n_frames):
            current_frame = self._frame
            # Post any inputs scheduled for this frame.
            due = [ev for ev in self._inputs if ev.at_frame == current_frame]
            if due:
                self._inputs = [ev for ev in self._inputs if ev.at_frame > current_frame]
                for ev in due:
                    produced = ev.factory()
                    if isinstance(produced, list):
                        for item in produced:
                            pygame.event.post(item)
                    else:
                        pygame.event.post(produced)

            scene = scene_manager.get_current_scene()
            if scene is None:
                # Director has not entered any scene; treat as a no-op frame.
                snap = take_snapshot(self.game, current_frame, time.monotonic() - self._start_time)
                self._snapshots.append(snap)
                new_snaps.append(snap)
                self._frame += 1
                continue

            # Drain pygame queue into scene.handle_events.
            for raw_event in pygame.event.get():
                # Map mouse coordinates through the viewport.
                if hasattr(raw_event, "pos"):
                    attrs = getattr(raw_event, "dict", {}).copy()
                    attrs["pos"] = viewport.screen_to_logical(*raw_event.pos)
                    event = pygame.event.Event(raw_event.type, attrs)
                else:
                    event = raw_event
                scene.handle_events(event)

            # Update.
            scene.update()

            # Render onto the viewport's logical surface.  Render
            # failures (e.g. CJK font issues in headless mode) must
            # not abort the scenario; we catch broadly and let the
            # snapshot layer / invariant suite catch semantic issues.
            try:
                viewport.logical_surface.fill((0, 0, 0))
                scene.render(viewport.logical_surface)
                viewport.present(director._window.get_surface())
                director._window.flip()
            except Exception as exc:
                if not getattr(self, "_render_warned", False):
                    logger.warning(
                        "render failed in scenario runner (frame %d): %s; "
                        "further render failures will be silent",
                        current_frame,
                        exc,
                    )
                    self._render_warned = True

            snap = take_snapshot(self.game, current_frame, time.monotonic() - self._start_time)
            self._snapshots.append(snap)
            new_snaps.append(snap)
            self._frame += 1

            # Run on_frame callbacks AFTER the snapshot so they can
            # observe a fully updated state.  We schedule them by
            # *previous* frame index so callbacks that fire on frame
            # N see the snapshot from frame N.
            for cb in list(self._on_frame):
                cb(self, current_frame)

            if self._frame >= self.max_frames:
                break

        return new_snaps

    def run_until(
        self,
        predicate: Callable[[GameSnapshot], bool],
        *,
        timeout_frames: int | None = None,
    ) -> ScenarioResult:
        """Advance frames until ``predicate`` matches a snapshot.

        Args:
            predicate: Callable returning ``True`` on the first
                matching snapshot.  The matching snapshot is included
                in the returned snapshots list.
            timeout_frames: Maximum frames to advance.  Defaults to
                ``self.max_frames - self._frame``.

        Returns:
            A :class:`ScenarioResult` with ``passed=True`` if the
            predicate was satisfied, else ``passed=False`` with a
            message describing the timeout.
        """
        self.setup()
        budget = timeout_frames if timeout_frames is not None else (self.max_frames - self._frame)
        for _ in range(budget):
            snaps = self.advance(1)
            if snaps and predicate(snaps[-1]):
                return ScenarioResult(
                    name=getattr(predicate, "__name__", "predicate"),
                    passed=True,
                    snapshots=list(self._snapshots),
                    message=f"predicate satisfied at frame {self._frame - 1}",
                    frames_run=self._frame,
                )
        last_scene = self._snapshots[-1].scene_name if self._snapshots else "?"
        return ScenarioResult(
            name=getattr(predicate, "__name__", "predicate"),
            passed=False,
            snapshots=list(self._snapshots),
            message=(
                f"predicate not satisfied within {budget} frames (last scene={last_scene})"
            ),
            frames_run=self._frame,
        )

    # -- Accessors -------------------------------------------------------

    @property
    def frame(self) -> int:
        return self._frame

    @property
    def snapshots(self) -> list[GameSnapshot]:
        return list(self._snapshots)

    def current_scene(self) -> Any:
        """Return the currently active scene (or ``None``)."""
        return self.game._director._scene_manager.get_current_scene()
