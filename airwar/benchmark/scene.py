"""In-game benchmark launcher scene.

A self-contained :class:`Scene` that exposes a single
"进入自动化测试" button.  Clicking it runs the full benchmark
suite (scenarios + invariants + fuzz) in a background thread,
shows live progress, and finally a results panel with a
"返回" button to go back to wherever the user came from.

The scene is wired into the :class:`airwar.game.Game` scene
manager under the name ``"benchmark"``; the
:class:`airwar.scenes.welcome_scene.WelcomeScene` shows a button
to enter it.

Implementation notes:

* Each scenario runs in its own subprocess (via
  :func:`run_scenario_in_subprocess`) because the SDL dummy
  driver only allows one window per process.
* The worker thread writes progress events to a
  :class:`queue.Queue`; the scene's :meth:`update` drains the
  queue and updates the UI without ever blocking the main loop.
* The thread is ``daemon=True`` and the scene's :meth:`exit`
  joins it with a short timeout, so a stuck benchmark cannot
  prevent the player from quitting.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import subprocess
import sys
import tempfile
import textwrap
import threading
from dataclasses import dataclass

import pygame

from ..config.design_tokens import SceneColors, get_design_tokens
from ..i18n import t
from ..ui.chamfered_panel import draw_chamfered_panel
from ..ui.menu_background import MenuBackground
from ..ui.particles import ParticleSystem
from ..utils.fonts import get_cjk_font
from ..utils.mouse_interaction import MouseInteractiveMixin
from ..utils.responsive import ResponsiveHelper
from .harness import ScenarioResult
from .runner import BenchmarkReport, LayerResult
from .scenarios import ALL_SCENARIOS

from ..scenes.scene import Scene

logger = logging.getLogger(__name__)


# -- Worker-thread plumbing ----------------------------------------------


@dataclass
class BenchProgress:
    """Progress event posted by the benchmark worker thread."""

    layer: str
    current: int
    total: int
    detail: str = ""


@dataclass
class BenchDone:
    """Final result posted when the benchmark worker finishes."""

    report: BenchmarkReport
    error: str | None = None


def _run_one_scenario_subprocess(scenario_name: str, *, timeout: int = 120) -> tuple[bool, str, int]:
    """Run a single scenario in a subprocess; return (passed, message, frames)."""
    env = os.environ.copy()
    env.setdefault("SDL_VIDEODRIVER", "dummy")
    env.setdefault("SDL_AUDIODRIVER", "dummy")
    code = textwrap.dedent(
        f"""
        import sys, os
        sys.path.insert(0, '.')
        import logging
        logging.disable(logging.CRITICAL)
        import pygame
        pygame.init()
        from airwar.game import Game
        from airwar.benchmark.scenarios import ALL_SCENARIOS, run_scenario
        for mod in ('basic','pause','death','mothership','boss','save_load'):
            __import__('airwar.benchmark.scenarios.' + mod, fromlist=['*'])
        target = next((s for s in ALL_SCENARIOS if s.name == {scenario_name!r}), None)
        if target is None:
            print('NOT_FOUND'); sys.exit(0)
        g = Game()
        try:
            res = run_scenario(target, g, max_frames=target.frames)
            flag = 'PASS' if res.passed else 'FAIL'
            print(f'{{flag}} {{res.frames_run}} {{res.message or ""}}')
        finally:
            try: g._window.close()
            except Exception: pass
        """
    )
    completed = subprocess.run(
        [sys.executable, "-W", "ignore", "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    out = completed.stdout.strip().splitlines()
    if not out:
        return False, f"subprocess produced no output: {completed.stderr[-200:]}", 0
    last = out[-1]
    parts = last.split(maxsplit=2)
    if len(parts) >= 2 and parts[0] in ("PASS", "FAIL"):
        passed = parts[0] == "PASS"
        try:
            frames = int(parts[1])
        except ValueError:
            frames = 0
        msg = parts[2] if len(parts) > 2 else ""
        return passed, msg, frames
    return False, last, 0


def _run_scenario_with_snapshots(scenario_name: str, *, timeout: int = 120) -> tuple[ScenarioResult, list[dict]]:
    """Run one scenario in a subprocess; return (parsed result, snapshot list)."""
    env = os.environ.copy()
    env.setdefault("SDL_VIDEODRIVER", "dummy")
    env.setdefault("SDL_AUDIODRIVER", "dummy")
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp:
        path = tmp.name
    try:
        code = textwrap.dedent(
            f"""
            import sys, os, json
            sys.path.insert(0, '.')
            import logging
            logging.disable(logging.CRITICAL)
            import pygame
            pygame.init()
            from airwar.game import Game
            from airwar.benchmark.scenarios import ALL_SCENARIOS, run_scenario
            for mod in ('basic','pause','death','mothership','boss','save_load'):
                __import__('airwar.benchmark.scenarios.' + mod, fromlist=['*'])
            target = next((s for s in ALL_SCENARIOS if s.name == {scenario_name!r}), None)
            if target is None:
                sys.exit(0)
            g = Game()
            try:
                res = run_scenario(target, g, max_frames=target.frames)
                with open({path!r}, 'w') as f:
                    json.dump({{
                        'scenario': target.name,
                        'passed': res.passed,
                        'message': res.message,
                        'frames_run': res.frames_run,
                        'snapshots': [s.to_dict() for s in res.snapshots],
                    }}, f)
            finally:
                try: g._window.close()
                except Exception: pass
            """
        )
        completed = subprocess.run(
            [sys.executable, "-W", "ignore", "-c", code],
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if not os.path.exists(path):
            return (
                ScenarioResult(
                    name=scenario_name,
                    passed=False,
                    message=f"subprocess failed: {completed.stderr[-200:]}",
                ),
                [],
            )
        with open(path) as f:
            data = json.load(f)
        result = ScenarioResult(
            name=data["scenario"],
            passed=data["passed"],
            message=data.get("message", ""),
            frames_run=data.get("frames_run", 0),
        )
        return result, data.get("snapshots", [])
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


# -- Scene ---------------------------------------------------------------


class BenchmarkScene(Scene, MouseInteractiveMixin):
    """Scene that runs the full benchmark suite via a single "Enter" button.

    Three substates:

    * ``idle``     -- shows the "进入自动化测试" + "返回" buttons.
    * ``running``  -- shows a progress bar and the current scenario.
    * ``results``  -- shows a pass/fail summary and a "返回" button.

    The :meth:`_start_benchmark` method spawns a daemon thread that
    runs every scenario in its own subprocess, collecting results
    and posting :class:`BenchProgress` / :class:`BenchDone` events
    to a queue.  :meth:`update` drains the queue each frame.
    """

    ENTER_BUTTON = "benchmark_enter"
    BACK_BUTTON = "benchmark_back"

    def __init__(self):
        Scene.__init__(self)
        MouseInteractiveMixin.__init__(self)
        self._state: str = "idle"
        self._report: BenchmarkReport | None = None
        self._events: queue.Queue = queue.Queue()
        self._worker: threading.Thread | None = None
        self._current_scenario: str = ""
        self._current_layer: str = ""
        self._current_step: int = 0
        self._total_steps: int = 0
        self._scroll_offset: int = 0
        self._animation_time: int = 0
        self._tokens = get_design_tokens()
        self._background: MenuBackground | None = None
        self._particles: ParticleSystem | None = None
        self.running = True
        self._wants_to_leave: bool = False

    # -- Lifecycle --------------------------------------------------------

    def enter(self, **kwargs) -> None:
        self._state = "idle"
        self._report = None
        self._events = queue.Queue()
        self._current_scenario = ""
        self._current_step = 0
        self._total_steps = 0
        self._scroll_offset = 0
        self._animation_time = 0
        self.running = True
        self._wants_to_leave = False
        self.clear_hover()
        self.clear_buttons()

        # Force-import all scenario modules so ALL_SCENARIOS is populated
        # for the worker thread.  Done here (rather than at import time)
        # so the scene is usable in isolation.
        for mod in (
            "basic",
            "pause",
            "death",
            "mothership",
            "boss",
            "save_load",
        ):
            __import__(f"airwar.benchmark.scenarios.{mod}", fromlist=["*"])

        pygame.font.init()
        self.title_font = get_cjk_font(self._tokens.typography.TITLE_SIZE)
        self.button_font = get_cjk_font(self._tokens.typography.BODY_SIZE)
        self.hint_font = get_cjk_font(self._tokens.typography.HUD_SIZE)
        self.body_font = get_cjk_font(self._tokens.typography.TINY_SIZE)
        self._background = MenuBackground()
        self._particles = ParticleSystem()
        self._particles.reset(self._tokens.components.PARTICLE_COUNT, "particle")

    def exit(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            # Don't block the scene exit on a stuck worker; the
            # daemon thread will die with the process.
            self._events.put(BenchDone(report=BenchmarkReport(passed=False, layers=[]), error="cancelled"))

    def is_running(self) -> bool:
        return self.running

    def is_ready(self) -> bool:
        return self._wants_to_leave

    # -- Event / update --------------------------------------------------

    def handle_events(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._wants_to_leave = True
                self.running = False
                return
            if event.key == pygame.K_RETURN and self._state == "idle":
                self._on_enter_clicked()
                return
            if event.key in (pygame.K_UP, pygame.K_PAGEUP) and self._state == "results":
                self._scroll_offset = max(0, self._scroll_offset - 1)
            if event.key in (pygame.K_DOWN, pygame.K_PAGEDOWN) and self._state == "results":
                self._scroll_offset += 1
            return
        if event.type == pygame.MOUSEMOTION:
            self.handle_mouse_motion(event.pos)
            return
        if event.type == pygame.MOUSEBUTTONDOWN and self.handle_mouse_click(event.pos):
            btn = self.get_hovered_button()
            if btn == self.ENTER_BUTTON and self._state == "idle":
                self._on_enter_clicked()
            elif btn == self.BACK_BUTTON and self._state in ("idle", "results"):
                self._wants_to_leave = True
                self.running = False

    def update(self, *args, **kwargs) -> None:
        self._animation_time += 1
        if self._background is not None:
            self._background._animation_time = self._animation_time
            self._background.update()
        if self._particles is not None:
            self._particles._animation_time = self._animation_time
            self._particles.update(direction=-1)
        # Drain worker events.
        try:
            while True:
                ev = self._events.get_nowait()
                if isinstance(ev, BenchProgress):
                    self._current_layer = ev.layer
                    self._current_step = ev.current
                    self._total_steps = ev.total
                    self._current_scenario = ev.detail
                elif isinstance(ev, BenchDone):
                    self._state = "results"
                    self._report = ev.report
                    if ev.error:
                        self._report.layers.append(
                            LayerResult(name="worker", passed=False, details=[f"FAIL worker: {ev.error}"])
                        )
        except queue.Empty:
            pass

    # -- Render ----------------------------------------------------------

    def render(self, surface: pygame.Surface) -> None:
        SC = SceneColors
        sw, sh = surface.get_size()
        if self._background is not None:
            self._background.render_themed_style(
                surface,
                {"bg": SC.BG_PRIMARY, "bg_gradient": SC.BG_PANEL},
            )
        if self._particles is not None:
            self._particles.render(surface, "particle")
        self._render_title(surface, sw, sh)
        if self._state == "idle":
            self._render_idle(surface, sw, sh)
        elif self._state == "running":
            self._render_running(surface, sw, sh)
        elif self._state == "results":
            self._render_results(surface, sw, sh)

    def _render_title(self, surface, sw, sh):
        SC = SceneColors
        title_surf = self.title_font.render(t("benchmark.title"), True, SC.GOLD_PRIMARY)
        surface.blit(title_surf, title_surf.get_rect(center=(sw // 2, 80)))

    def _render_idle(self, surface, sw, sh):
        SC = SceneColors
        scale = ResponsiveHelper.get_scale_factor(sw, sh)
        # Subtitle
        subtitle = self.hint_font.render(t("benchmark.subtitle"), True, SC.TEXT_DIM)
        surface.blit(subtitle, subtitle.get_rect(center=(sw // 2, 140)))

        # Enter button
        enter_w = ResponsiveHelper.scale(360, scale)
        enter_h = ResponsiveHelper.scale(80, scale)
        enter_rect = pygame.Rect(0, 0, enter_w, enter_h)
        enter_rect.center = (sw // 2, sh // 2 - 20)
        self.register_button(self.ENTER_BUTTON, enter_rect)
        enter_hover = self.is_button_hovered(self.ENTER_BUTTON)
        # Pulse the enter button.
        pulse = (math.sin(self._animation_time * 0.06) + 1) * 0.5
        enter_color = (
            int(SC.GOLD_PRIMARY[0] * (0.7 + 0.3 * pulse)),
            int(SC.GOLD_PRIMARY[1] * (0.7 + 0.3 * pulse)),
            int(SC.GOLD_PRIMARY[2] * (0.7 + 0.3 * pulse)),
        )
        draw_chamfered_panel(
            surface,
            enter_rect.x,
            enter_rect.y,
            enter_rect.width,
            enter_rect.height,
            SC.BG_PANEL_LIGHT if enter_hover else SC.BG_PANEL,
            enter_color if enter_hover else SC.GOLD_PRIMARY,
            None,
            10,
        )
        enter_surf = self.button_font.render(t("benchmark.enter_button"), True, SC.TEXT_PRIMARY)
        surface.blit(enter_surf, enter_surf.get_rect(center=enter_rect.center))

        # Keyboard hint directly under the button (separate from the
        # body-font "info.lines" pair so the hint is visually anchored
        # to the button, not to the page-level description).
        hint_surf = self.hint_font.render(t("benchmark.enter_hint"), True, SC.TEXT_DIM)
        surface.blit(hint_surf, hint_surf.get_rect(center=(sw // 2, enter_rect.bottom + 24)))

        # Back button
        back_w = ResponsiveHelper.scale(160, scale)
        back_h = ResponsiveHelper.scale(50, scale)
        back_rect = pygame.Rect(0, 0, back_w, back_h)
        back_rect.center = (sw // 2, sh - 80)
        self.register_button(self.BACK_BUTTON, back_rect)
        back_hover = self.is_button_hovered(self.BACK_BUTTON)
        draw_chamfered_panel(
            surface,
            back_rect.x,
            back_rect.y,
            back_rect.width,
            back_rect.height,
            SC.BG_PANEL_LIGHT if back_hover else SC.BG_PANEL,
            SC.GOLD_PRIMARY if back_hover else SC.BORDER_DIM,
            None,
            6,
        )
        back_surf = self.hint_font.render(t("benchmark.back"), True, SC.TEXT_PRIMARY)
        surface.blit(back_surf, back_surf.get_rect(center=back_rect.center))

        # Info text below the enter button
        info_lines = [
            t("benchmark.info.line1"),
            t("benchmark.info.line2"),
        ]
        for i, line in enumerate(info_lines):
            surf = self.body_font.render(line, True, SC.TEXT_DIM)
            surface.blit(surf, surf.get_rect(center=(sw // 2, sh // 2 + 100 + i * 22)))

    def _render_running(self, surface, sw, sh):
        SC = SceneColors
        scale = ResponsiveHelper.get_scale_factor(sw, sh)
        # Status label
        label = t("benchmark.running")
        label_surf = self.button_font.render(label, True, SC.GOLD_PRIMARY)
        surface.blit(label_surf, label_surf.get_rect(center=(sw // 2, sh // 2 - 80)))

        # Progress bar
        bar_w = ResponsiveHelper.scale(640, scale)
        bar_h = ResponsiveHelper.scale(24, scale)
        bar_rect = pygame.Rect(0, 0, bar_w, bar_h)
        bar_rect.center = (sw // 2, sh // 2)
        draw_chamfered_panel(
            surface, bar_rect.x, bar_rect.y, bar_rect.width, bar_rect.height,
            SC.BG_PANEL, SC.BORDER_DIM, None, 4,
        )
        if self._total_steps > 0:
            progress = min(1.0, self._current_step / self._total_steps)
            fill_rect = pygame.Rect(bar_rect.x + 2, bar_rect.y + 2,
                                    int((bar_rect.width - 4) * progress), bar_rect.height - 4)
            pygame.draw.rect(surface, SC.GOLD_PRIMARY, fill_rect)

        # Progress text
        if self._total_steps > 0:
            pct = int(100 * self._current_step / self._total_steps)
            pct_text = f"{self._current_step}/{self._total_steps}  {pct}%"
        else:
            pct_text = "..."
        pct_surf = self.hint_font.render(pct_text, True, SC.TEXT_PRIMARY)
        surface.blit(pct_surf, pct_surf.get_rect(center=(sw // 2, bar_rect.bottom + 30)))

        # Current scenario
        if self._current_scenario:
            cur = self.body_font.render(self._current_scenario, True, SC.TEXT_DIM)
            surface.blit(cur, cur.get_rect(center=(sw // 2, bar_rect.bottom + 60)))

    def _render_results(self, surface, sw, sh):
        SC = SceneColors
        scale = ResponsiveHelper.get_scale_factor(sw, sh)
        if self._report is None:
            return
        # Verdict banner
        verdict_color = SC.FOREST_GREEN if self._report.passed else SC.DANGER_RED
        verdict = "PASS" if self._report.passed else "FAIL"
        verdict_surf = self.title_font.render(verdict, True, verdict_color)
        surface.blit(verdict_surf, verdict_surf.get_rect(center=(sw // 2, 130)))

        # Stats line
        passed = sum(d.count("PASS") for layer in self._report.layers for d in layer.details)
        failed = sum(d.count("FAIL") for layer in self._report.layers for d in layer.details)
        stats = f"{passed} passed, {failed} failed, {self._report.duration_s:.1f}s"
        stats_surf = self.hint_font.render(stats, True, SC.TEXT_PRIMARY)
        surface.blit(stats_surf, stats_surf.get_rect(center=(sw // 2, 180)))

        # Detail list
        list_x = 60
        list_y = 220
        list_w = sw - 120
        list_h = sh - list_y - 130
        draw_chamfered_panel(surface, list_x, list_y, list_w, list_h, SC.BG_PANEL, SC.BORDER_DIM, None, 4)

        line_h = 22
        max_lines = list_h // line_h
        all_lines: list[tuple[str, str]] = []  # (verdict, text)
        for layer in self._report.layers:
            for d in layer.details:
                if d.startswith("PASS"):
                    all_lines.append(("PASS", d))
                elif d.startswith("FAIL"):
                    all_lines.append(("FAIL", d))
        start = min(self._scroll_offset, max(0, len(all_lines) - max_lines))
        visible = all_lines[start : start + max_lines]
        for i, (verdict, line) in enumerate(visible):
            color = SC.FOREST_GREEN if verdict == "PASS" else SC.DANGER_RED
            truncated = line if len(line) < 90 else line[:87] + "..."
            text_surf = self.body_font.render(truncated, True, color)
            surface.blit(text_surf, (list_x + 16, list_y + 8 + i * line_h))

        # Back button
        back_w = ResponsiveHelper.scale(160, scale)
        back_h = ResponsiveHelper.scale(50, scale)
        back_rect = pygame.Rect(0, 0, back_w, back_h)
        back_rect.center = (sw // 2, sh - 60)
        self.register_button(self.BACK_BUTTON, back_rect)
        back_hover = self.is_button_hovered(self.BACK_BUTTON)
        draw_chamfered_panel(
            surface,
            back_rect.x,
            back_rect.y,
            back_rect.width,
            back_rect.height,
            SC.BG_PANEL_LIGHT if back_hover else SC.BG_PANEL,
            SC.GOLD_PRIMARY if back_hover else SC.BORDER_DIM,
            None,
            6,
        )
        back_surf = self.hint_font.render(t("benchmark.back"), True, SC.TEXT_PRIMARY)
        surface.blit(back_surf, back_surf.get_rect(center=back_rect.center))

    # -- Worker ----------------------------------------------------------

    def _on_enter_clicked(self) -> None:
        if self._state != "idle":
            return
        self._state = "running"
        self._current_step = 0
        self._total_steps = len(ALL_SCENARIOS) + 1  # +1 for invariants
        self._current_scenario = ""
        self._events = queue.Queue()
        self._worker = threading.Thread(
            target=self._worker_main, name="benchmark-worker", daemon=True
        )
        self._worker.start()

    def _worker_main(self) -> None:
        """Run all scenarios + invariants; post progress and final report."""
        all_snaps: list = []
        layer_results: list[LayerResult] = []
        try:
            # Scenarios layer
            for i, scenario in enumerate(ALL_SCENARIOS, start=1):
                self._events.put(
                    BenchProgress(
                        layer="scenarios",
                        current=i - 1,
                        total=len(ALL_SCENARIOS),
                        detail=f"running {scenario.name}",
                    )
                )
                result, snaps = _run_scenario_with_snapshots(scenario.name)
                all_snaps.extend(snaps)
                if result.passed:
                    layer_results.append(
                        LayerResult(
                            name="scenarios",
                            passed=True,
                            details=[f"PASS  {scenario.name}  ({result.frames_run} frames)"],
                        )
                    )
                else:
                    layer_results.append(
                        LayerResult(
                            name="scenarios",
                            passed=False,
                            details=[f"FAIL  {scenario.name}  {result.message or ''}"],
                        )
                    )
            # Invariants layer
            self._events.put(
                BenchProgress(
                    layer="invariants",
                    current=len(ALL_SCENARIOS),
                    total=len(ALL_SCENARIOS) + 1,
                    detail="running invariants",
                )
            )
            from .snapshot import GameSnapshot
            from .invariants import InvariantSuite

            snapshots = [GameSnapshot(**d) for d in all_snaps]
            suite = InvariantSuite()
            violations = suite.check_all(snapshots)
            details = [
                f"PASS  invariant:{name}  ({count} checks)"
                for name, count in suite.check_counts.items()
            ]
            for v in violations:
                details.append(f"FAIL  invariant:{v.rule}  frame={v.frame}  {v.message[:80]}")
            layer_results.append(
                LayerResult(name="invariants", passed=not violations, details=details)
            )

            report = BenchmarkReport(
                passed=all(layer.passed for layer in layer_results),
                layers=layer_results,
                snapshots=all_snaps,
                duration_s=0.0,
            )
            self._events.put(BenchDone(report=report, error=None))
        except Exception as exc:  # noqa: BLE001
            logger.exception("benchmark worker crashed")
            self._events.put(
                BenchDone(
                    report=BenchmarkReport(
                        passed=False,
                        layers=layer_results,
                        snapshots=all_snaps,
                        duration_s=0.0,
                    ),
                    error=f"worker exception: {exc!r}",
                )
            )


# We need a math import for the pulsing animation.
import math  # noqa: E402
