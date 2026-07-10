# -*- mode: python ; coding: utf-8 -*-
# =============================================================================
# Air War - PyInstaller Spec (Single Source of Truth)
# =============================================================================
# Used by: build_linux.sh / build_macos.sh / build_windows.bat
# Entry:   main.py -> airwar.__main__:main -> airwar.game:Game.run
# =============================================================================

import os
import sys

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Project root (where this spec file lives)
PROJECT_ROOT = os.path.abspath(SPECPATH)

# Generated asset directory. AIRWAR_GENERATED_ASSET_DIR can override it at
# runtime. The directory itself is created on
# first run; we don't ship a populated one, so no need to include it.
ASSET_DIR = os.path.join(PROJECT_ROOT, "airwar", "data", "generated_assets")
if not os.path.isdir(ASSET_DIR):
    os.makedirs(ASSET_DIR, exist_ok=True)

# Detect optional Rust extension at build time; if installed, collect it.
try:
    from airwar.core_bindings import RUST_AVAILABLE  # type: ignore[import-not-found]
except Exception:
    RUST_AVAILABLE = False

# airwar submodules are referenced dynamically (manager registries, plugin
# loaders, reward pool, etc.) so we explicitly enumerate them.
HIDDENIMPORTS = []
HIDDENIMPORTS += collect_submodules("airwar")
HIDDENIMPORTS += [
    "pygame",
    "PIL",
    "PIL.Image",
    "pygame.gfxdraw",
    "pygame.font",
    "pygame.mixer",
    "pygame.image",
]

# Platform-specific bundle options injected by the build script.
# build_macos.sh sets AIRWAR_OSX_BUNDLE_ID; everything else leaves it empty.
OSX_BUNDLE_ID = os.environ.get("AIRWAR_OSX_BUNDLE_ID", "")
OSX_BUNDLE_OPTIONS = []
if sys.platform == "darwin" and OSX_BUNDLE_ID:
    OSX_BUNDLE_OPTIONS = [
        ("BUNDLE_IDENTIFIER", OSX_BUNDLE_ID),
    ]

EXCLUDES = [
    # Heavy debugging / dev tools that should never ship in a release build.
    "maturin",
    "matplotlib",
    "tkinter",
    "pydoc",
]

a = Analysis(
    ["main.py"],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[
        # Ship a writable asset directory so first-run generation works.
        (ASSET_DIR, "airwar/data/generated_assets"),
    ],
    hiddenimports=HIDDENIMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Add the Rust extension to the COLLECT step when available so its .so/.pyd
# ends up next to the executable.
binaries_extra = []
if RUST_AVAILABLE:
    try:
        import airwar_core  # type: ignore[import-not-found]

        core_dir = os.path.dirname(airwar_core.__file__)
        binaries_extra += [
            (os.path.join(core_dir, f), "airwar_core")
            for f in os.listdir(core_dir)
            if f.endswith((".so", ".pyd", ".dylib"))
        ]
    except Exception:
        pass

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries + binaries_extra,
    a.zipfiles,
    a.datas,
    [],
    name="AirWar",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
    bundle_options=OSX_BUNDLE_OPTIONS,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="AirWar",
)
