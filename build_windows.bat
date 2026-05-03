@echo off
REM =============================================================================
REM Air War - Windows Build Script
REM =============================================================================
REM Usage: build_windows.bat
REM Prerequisites: Rust (rustup), Python 3.12+, Visual Studio Build Tools
REM Output: dist\AirWar.exe (standalone executable)
REM =============================================================================
setlocal enabledelayedexpansion

echo === Air War Windows Build ===

REM 1. Create isolated build environment
echo [1/4] Preparing build environment...
python -m venv .venv-build
call .venv-build\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt

REM 2. Build and install Rust extension into the build environment
echo [2/4] Building Rust extension...
where cargo >nul 2>nul
if %errorlevel% equ 0 (
    python -m maturin develop --release --manifest-path airwar_core\Cargo.toml
    if errorlevel 1 (
        echo    WARNING: Rust extension build failed.
        echo    Game will fall back to pure Python.
    ) else (
        echo    Rust extension installed in .venv-build.
    )
) else (
    echo    WARNING: cargo not found.
    echo    Game will fall back to pure Python.
)

REM 3. Validate imports
echo [3/4] Validating Python environment...
python -c "import pygame, PIL, PyInstaller; from airwar.core_bindings import RUST_AVAILABLE; print('Rust acceleration:', RUST_AVAILABLE)"

REM 4. Build standalone executable
echo [4/4] Building standalone executable...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

set COLLECT_AIRWAR_CORE=
python -c "from airwar.core_bindings import RUST_AVAILABLE; raise SystemExit(0 if RUST_AVAILABLE else 1)"
if %errorlevel% equ 0 set COLLECT_AIRWAR_CORE=--collect-all airwar_core

python -m PyInstaller ^
    --name="AirWar" ^
    --add-data="airwar\data;airwar\data" ^
    %COLLECT_AIRWAR_CORE% ^
    --hidden-import=pygame ^
    --hidden-import=PIL ^
    --hidden-import=PIL.Image ^
    --noconsole ^
    --onefile ^
    main.py

echo.
echo === Build complete ===
echo Executable: dist\AirWar.exe
dir dist\AirWar.exe
