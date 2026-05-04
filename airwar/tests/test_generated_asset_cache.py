import os

import pygame

from airwar.utils.generated_asset_cache import generated_asset_cache_dir, load_or_build_generated_surface


def test_generated_asset_cache_saves_and_reuses_png(monkeypatch, tmp_path):
    monkeypatch.setenv("AIRWAR_GENERATED_ASSET_DIR", str(tmp_path))
    build_count = 0

    def build_surface():
        nonlocal build_count
        build_count += 1
        surface = pygame.Surface((18, 14), pygame.SRCALPHA)
        surface.fill((12, 34, 56, 200))
        return surface

    first = load_or_build_generated_surface("unit", ("sprite", 1), build_surface)
    second = load_or_build_generated_surface("unit", ("sprite", 1), build_surface)

    assert build_count == 1
    assert first.get_size() == second.get_size() == (18, 14)
    assert len(list(tmp_path.glob("unit_*.png"))) == 1
    assert generated_asset_cache_dir() == str(tmp_path)


def test_generated_asset_cache_rebuilds_unreadable_png(monkeypatch, tmp_path):
    monkeypatch.setenv("AIRWAR_GENERATED_ASSET_DIR", str(tmp_path))

    def build_surface():
        surface = pygame.Surface((8, 8), pygame.SRCALPHA)
        surface.fill((255, 0, 0, 255))
        return surface

    load_or_build_generated_surface("bad", ("sprite", 1), build_surface)
    png_path = next(tmp_path.glob("bad_*.png"))
    png_path.write_text("not a png", encoding="utf-8")

    rebuilt = load_or_build_generated_surface("bad", ("sprite", 1), build_surface)

    assert rebuilt.get_size() == (8, 8)
    assert os.path.getsize(png_path) > len("not a png")
