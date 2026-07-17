"""Render current ship sprites to PNGs for visual review.

Generates player/enemy/elite/boss sprites at their exact runtime sizes,
composited on a dark space-like background, upscaled 2x for inspection.

Usage: python3 scripts_dev/render_sprites.py [outdir]
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ["AIRWAR_GENERATED_ASSET_DIR"] = "/tmp/airwar_sprite_review/asset_cache"

import pygame  # noqa: E402

from airwar.utils.sprites import (  # noqa: E402
    get_boss_sprite,
    get_elite_enemy_sprite,
    get_enemy_sprite,
    get_player_sprite,
)

OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else "/tmp/airwar_sprite_review"
SCALE = 2
BG = (10, 12, 22)  # dark space background, close to in-game starfield base


def _composite(sprite: pygame.Surface, label: str) -> pygame.Surface:
    sw, sh = sprite.get_size()
    cell = pygame.Surface((sw + 20, sh + 20), pygame.SRCALPHA)
    cell.fill((*BG, 255))
    cell.blit(sprite, (10, 10))
    return pygame.transform.scale(cell, (cell.get_width() * SCALE, cell.get_height() * SCALE))


def main() -> None:
    pygame.init()
    os.makedirs(OUT_DIR, exist_ok=True)

    jobs = [
        ("player_68x82", get_player_sprite(68, 82)),
        ("enemy_50x50_hp100", get_enemy_sprite(50, 50, 1.0)),
        ("enemy_50x50_hp50", get_enemy_sprite(50, 50, 0.5)),
        ("elite_85x85_hp100", get_elite_enemy_sprite(65 * 1.3, 65 * 1.3, 1.0)),
        ("boss_120x100_hp100", get_boss_sprite(120, 100, 1.0)),
        ("boss_120x100_hp25", get_boss_sprite(120, 100, 0.25)),
    ]

    cells = []
    for name, sprite in jobs:
        cell = _composite(sprite, name)
        cells.append((name, cell))
        pygame.image.save(cell, os.path.join(OUT_DIR, f"{name}.png"))

    # Contact sheet: all cells in a row, aligned by bottom edge.
    gap = 24
    sheet_w = sum(c.get_width() for _, c in cells) + gap * (len(cells) + 1)
    sheet_h = max(c.get_height() for _, c in cells) + 2 * gap
    sheet = pygame.Surface((sheet_w, sheet_h), pygame.SRCALPHA)
    sheet.fill((*BG, 255))
    x = gap
    for name, cell in cells:
        sheet.blit(cell, (x, sheet_h - gap - cell.get_height()))
        x += cell.get_width() + gap
    pygame.image.save(sheet, os.path.join(OUT_DIR, "contact_sheet.png"))
    print(f"saved {len(cells)} sprites + contact sheet to {OUT_DIR}")
    for name, sprite in jobs:
        print(f"  {name}: surface {sprite.get_size()}")


if __name__ == "__main__":
    main()
