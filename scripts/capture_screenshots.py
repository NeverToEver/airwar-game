"""Capture README screenshots in a headless pygame environment.

Usage:
    SDL_VIDEODRIVER=dummy python scripts/capture_screenshots.py

Outputs PNGs to .github/screenshots/ at 1280x720.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Allow importing the airwar package from the repo root regardless of CWD.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # noqa: E402

import pygame  # noqa: E402

from airwar.config import set_display_size  # noqa: E402
from airwar.game.frame_context import FixedStepAccumulator  # noqa: E402
from airwar.game.scaled_viewport import ScaledViewport  # noqa: E402
from airwar.game.systems.game_save_service import GameSaveService  # noqa: E402
from airwar.i18n import set_locale  # noqa: E402
from airwar.scenes import (  # noqa: E402
    DeathScene,
    GameScene,
    PauseScene,
    SettingsScene,
    WelcomeScene,
)
from airwar.scenes.scene import SceneManager  # noqa: E402
from airwar.utils.database import UserDB  # noqa: E402
from airwar.utils.sprites import prewarm_glow_caches, prewarm_ship_sprite_caches  # noqa: E402

# Chinese is the historical default UI language.
set_locale("zh_CN")

OUTPUT_DIR = ROOT / ".github" / "screenshots"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Design resolution for capture.
CAPTURE_W, CAPTURE_H = 1920, 1080
# Exported screenshot resolution.
EXPORT_W, EXPORT_H = 1280, 720


def _init_pygame() -> pygame.Surface:
    pygame.init()
    pygame.font.init()
    set_display_size(CAPTURE_W, CAPTURE_H)
    return pygame.display.set_mode((CAPTURE_W, CAPTURE_H))


def _resize_surface(surface: pygame.Surface) -> pygame.Surface:
    """Scale a capture down to README-friendly dimensions."""
    return pygame.transform.smoothscale(surface, (EXPORT_W, EXPORT_H))


def _save(name: str, surface: pygame.Surface) -> Path:
    path = OUTPUT_DIR / f"{name}.png"
    scaled = _resize_surface(surface)
    pygame.image.save(scaled, str(path))
    return path


def _render_once(scene, surface: pygame.Surface) -> None:
    """Render a single frame; some scenes register buttons during render."""
    scene.render(surface)


def capture_welcome(scene_manager: SceneManager, viewport: ScaledViewport, surface: pygame.Surface) -> Path:
    scene_manager.switch("welcome", viewport=viewport)
    scene = scene_manager.get_current_scene()
    # First render registers buttons; second render is cleaner.
    _render_once(scene, surface)
    _render_once(scene, surface)
    return _save("welcome", surface)


def capture_settings(scene_manager: SceneManager, db: UserDB, surface: pygame.Surface) -> Path:
    settings = SettingsScene()
    scene_manager.register("settings_capture", settings)
    scene_manager.switch(
        "settings_capture",
        db=db,
        username="Player",
        settings_ref={"ctrl_mode": "hold", "shift_boost_mode": "hold"},
    )
    _render_once(settings, surface)
    return _save("settings", surface)


def capture_pause(scene_manager: SceneManager, surface: pygame.Surface) -> Path:
    pause = PauseScene()
    scene_manager.register("pause_capture", pause)
    scene_manager.switch("pause_capture")
    _render_once(pause, surface)
    return _save("pause", surface)


def capture_death(scene_manager: SceneManager, surface: pygame.Surface) -> Path:
    death = DeathScene()
    scene_manager.register("death_capture", death)
    scene_manager.switch(
        "death_capture",
        score=12_345,
        kills=67,
        boss_kills=1,
        username="Player",
    )
    _render_once(death, surface)
    return _save("death", surface)


def capture_gameplay(
    scene_manager: SceneManager,
    viewport: ScaledViewport,
    surface: pygame.Surface,
) -> Path | None:
    """Capture the game scene after a few simulation steps.

    This is the most fragile capture because GameScene builds a full
    game session. Failures are reported but do not abort the script.
    """
    save_service = GameSaveService()
    pygame.mouse.set_pos(CAPTURE_W // 2, CAPTURE_H // 2)
    scene_manager.switch(
        "game",
        difficulty="medium",
        username="Player",
        settings_ref={"ctrl_mode": "hold", "shift_boost_mode": "hold"},
        save_service=save_service,
        viewport=viewport,
    )
    game = scene_manager.get_current_scene()
    clock = FixedStepAccumulator()
    # Advance a handful of frames so entities are visible.
    for _ in range(60):
        frame = clock.advance(1 / 60, simulate=True)
        game.update(frame)
        game.render(surface)
    return _save("gameplay", surface)


def main() -> int:
    surface = _init_pygame()
    viewport = ScaledViewport(CAPTURE_W, CAPTURE_H)
    viewport.update(CAPTURE_W, CAPTURE_H)
    set_display_size(CAPTURE_W, CAPTURE_H)

    prewarm_glow_caches()
    prewarm_ship_sprite_caches()

    scene_manager = SceneManager()
    db = UserDB()
    scene_manager.register("welcome", WelcomeScene())
    scene_manager.register("game", GameScene())

    captures: list[tuple[str, Path | None]] = []

    try:
        captures.append(("welcome", capture_welcome(scene_manager, viewport, surface)))
    except Exception as exc:  # noqa: BLE001
        print(f"[skip] welcome: {exc}")
        captures.append(("welcome", None))

    try:
        captures.append(("settings", capture_settings(scene_manager, db, surface)))
    except Exception as exc:  # noqa: BLE001
        print(f"[skip] settings: {exc}")
        captures.append(("settings", None))

    try:
        captures.append(("pause", capture_pause(scene_manager, surface)))
    except Exception as exc:  # noqa: BLE001
        print(f"[skip] pause: {exc}")
        captures.append(("pause", None))

    try:
        captures.append(("death", capture_death(scene_manager, surface)))
    except Exception as exc:  # noqa: BLE001
        print(f"[skip] death: {exc}")
        captures.append(("death", None))

    try:
        captures.append(("gameplay", capture_gameplay(scene_manager, viewport, surface)))
    except Exception as exc:  # noqa: BLE001
        print(f"[skip] gameplay: {exc}")
        captures.append(("gameplay", None))

    pygame.quit()

    print("\nCaptured screenshots:")
    for name, path in captures:
        status = str(path) if path else "FAILED"
        print(f"  {name}: {status}")

    return 0 if any(p is not None for _, p in captures) else 1


if __name__ == "__main__":
    raise SystemExit(main())
