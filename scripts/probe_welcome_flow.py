"""Headless flow probe: walks welcome -> game -> pause -> death, looking for
button overlap, missing scenes, focus cycle issues, etc.

Run with:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 /tmp/probe_flow.py
"""

from __future__ import annotations

import os
import logging
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pygame  # noqa: E402

logging.basicConfig(level=logging.WARNING)
logging.getLogger("airwar").setLevel(logging.WARNING)


def _find_overlaps(rects: dict[str, pygame.Rect]) -> list[tuple[str, str, pygame.Rect]]:
    """Return pairs of button names whose rects partially overlap (not containment)."""
    overlaps = []
    names = list(rects.keys())
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ra, rb = rects[a], rects[b]
            if not ra.colliderect(rb):
                continue
            if ra.contains(rb) or rb.contains(ra):
                continue
            inter = ra.clip(rb)
            if inter.width > 2 and inter.height > 2:
                overlaps.append((a, b, inter))
    return overlaps


def _get_button_rects(scene) -> dict[str, pygame.Rect]:
    """Find all clickable button rects on a scene."""
    rects: dict[str, pygame.Rect] = {}
    if hasattr(scene, "_button_rects") and isinstance(scene._button_rects, dict):
        for k, v in scene._button_rects.items():
            if isinstance(v, pygame.Rect):
                rects[k] = v
    gbr = getattr(scene, "get_button_rect", None)
    if gbr is not None:
        for name in (
            "login", "register", "delete", "guest", "easy", "medium", "hard", "insane",
            "benchmark", "leaderboard", "start", "continue", "resume", "settings",
            "quit", "yes", "no", "ok", "cancel", "back", "restart", "give_up",
            "new_run", "load_run", "fullscreen", "music", "sfx",
        ):
            try:
                r = gbr(name)
            except Exception:
                r = None
            if isinstance(r, pygame.Rect) and name not in rects:
                rects[name] = r
    return rects


def _drive(scene, sm, n: int) -> list[tuple[str, str]]:
    """Run update/render for n frames; return list of (where, repr(exception))."""
    out: list[tuple[str, str]] = []
    surface = pygame.display.get_surface()
    for f in range(n):
        try:
            sm.update()
        except Exception as e:
            out.append((f"update@frame{f}", repr(e)))
            break
        try:
            sm.render(surface)
        except Exception as e:
            out.append((f"render@frame{f}", repr(e)))
            break
    return out


def main() -> None:
    from airwar.game import Game
    print(f"pygame version: {pygame.version.ver}")
    print()
    game = Game()
    sm = game._director._scene_manager

    print("=" * 60)
    print("[A] Welcome scene probe")
    print("=" * 60)
    print(f"  registered scenes: {list(sm._scenes.keys())}")
    sm.switch("welcome")
    welcome = sm.get_scene("welcome")
    print(f"  current scene: {sm.get_current_scene_name()}")
    _required_attrs = (
        "animation_time", "_background", "username", "password", "focus",
        "selected_difficulty", "difficulty_index",
    )
    print(f"  welcome attrs set: {all(hasattr(welcome, a) for a in _required_attrs)}")

    welcome_excs = _drive(welcome, sm, 5)
    for where, exc in welcome_excs[:3]:
        print(f"  !! {where}: {exc}")
    if not welcome_excs:
        print("  update/render OK")

    rects = _get_button_rects(welcome)
    print(f"  found {len(rects)} named button rects: {sorted(rects.keys())}")
    overlaps = _find_overlaps(rects)
    if overlaps:
        print("  !! PARTIAL OVERLAPS:")
        for a, b, inter in overlaps:
            print(f"     {a!r} <-> {b!r}  intersect={inter}")
    else:
        print("  no partial button overlaps")
    for name in sorted(rects):
        r = rects[name]
        print(f"    {name:30s} x={r.x:5d} y={r.y:5d} w={r.w:4d} h={r.h:3d} center=({r.centerx:4d},{r.centery:4d})")

    # Probe key handling
    keypress_excs: list[tuple[str, str]] = []
    test_events = [
        ("K_d_with_unicode", pygame.event.Event(
            pygame.KEYDOWN, {"key": pygame.K_d, "mod": 0, "unicode": "d", "scancode": 0})),
        ("K_d_no_unicode", pygame.event.Event(
            pygame.KEYDOWN, {"key": pygame.K_d, "mod": 0, "scancode": 0})),
        ("K_TAB", pygame.event.Event(
            pygame.KEYDOWN, {"key": pygame.K_TAB, "mod": 0, "unicode": "\t", "scancode": 0})),
        ("K_RETURN", pygame.event.Event(
            pygame.KEYDOWN, {"key": pygame.K_RETURN, "mod": 0, "unicode": "\r", "scancode": 0})),
        ("K_UP", pygame.event.Event(
            pygame.KEYDOWN, {"key": pygame.K_UP, "mod": 0, "scancode": 0})),
        ("K_DOWN", pygame.event.Event(
            pygame.KEYDOWN, {"key": pygame.K_DOWN, "mod": 0, "scancode": 0})),
        ("K_LEFT", pygame.event.Event(
            pygame.KEYDOWN, {"key": pygame.K_LEFT, "mod": 0, "scancode": 0})),
        ("K_RIGHT", pygame.event.Event(
            pygame.KEYDOWN, {"key": pygame.K_RIGHT, "mod": 0, "scancode": 0})),
        ("K_F11", pygame.event.Event(
            pygame.KEYDOWN, {"key": pygame.K_F11, "mod": 0, "unicode": "", "scancode": 0})),
    ]
    for label, ev in test_events:
        try:
            welcome.handle_events(ev)
        except Exception as e:
            keypress_excs.append((label, repr(e)))
            print(f"  !! key {label} -> {e!r}")
    if not keypress_excs:
        print("  all key events handled cleanly")

    # Click each button
    click_excs: list[tuple[str, str]] = []
    for name, rect in rects.items():
        if rect.w <= 0 or rect.h <= 0:
            continue
        cx, cy = rect.center
        for ev_kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            ev = pygame.event.Event(ev_kind, {
                "button": 1, "pos": (cx, cy), "rel": (0, 0), "touch": False,
            })
            try:
                welcome.handle_events(ev)
            except Exception as e:
                click_excs.append((name, repr(e)))
                print(f"  !! click {name} -> {e!r}")
    if not click_excs:
        print("  all button clicks handled cleanly")

    print()
    print("=" * 60)
    print("[B] All-scenes render smoke (one window already up, scenes in same sm)")
    print("=" * 60)
    for name in list(sm._scenes.keys()):
        scene = sm.get_scene(name)
        if scene is None:
            print(f"  {name}: missing")
            continue
        try:
            if sm.get_current_scene_name() != name:
                sm.switch(name)
                scene = sm.get_current_scene()
            else:
                scene = sm.get_current_scene()
            excs = _drive(scene, sm, 5)
            if excs:
                print(f"  {name}: EXCEPTION  {excs[0][0]}: {excs[0][1]}")
            else:
                print(f"  {name}: OK")
        except Exception as e:
            print(f"  {name}: switch crashed {e!r}")


if __name__ == "__main__":
    main()
