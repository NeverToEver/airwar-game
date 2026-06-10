@echo off
REM =============================================================================
REM Air War - Windows Build (slim wrapper around AirWar.spec)
REM =============================================================================
REM Usage: build_windows.bat
REM Prerequisites: Rust (rustup), Python 3.11+, Visual Studio Build Tools
REM Output: dist\AirWar\AirWar.exe (standalone executable)
REM Optional env:
REM   AIRWAR_KEEP_BUILD_VENV=1     preserve .venv-build after the run
REM   AIRWAR_SIGNTOOL=...           sign dist\AirWar\AirWar.exe with signtool
REM   AIRWAR_SIGN_PFX=...           PFX file path passed to signtool /f
REM   AIRWAR_SIGN_PASSWORD=...      PFX password passed to signtool /p
REM =============================================================================
setlocal enabledelayedexpansion

echo === Air War Windows Build ===
set "KEEP_BUILD_VENV=%AIRWAR_KEEP_BUILD_VENV%"

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python 3.11 or newer is required.
    python --version
    exit /b 1
)
python --version

REM 1. Isolated build venv with PyInstaller + maturin + project deps
echo [1/3] Preparing build environment...
python -m venv .venv-build
call .venv-build\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt

REM 2. Optional Rust extension (game falls back to pure Python if unavailable)
echo [2/3] Building Rust extension...
where cargo >nul 2>nul
if %errorlevel% equ 0 (
    python -m maturin develop --release --manifest-path airwar_core\Cargo.toml
    if errorlevel 1 (
        echo    WARNING: Rust extension build failed.
    ) else (
        echo    Rust extension installed in .venv-build.
    )
) else (
    echo    WARNING: cargo not found.
)
echo    Game will fall back to pure Python if the extension is missing.

REM 3. Build standalone executable from AirWar.spec
echo [3/3] Building standalone executable...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

python -m PyInstaller AirWar.spec
if errorlevel 1 goto :cleanup_fail

REM 4. Optional Authenticode signing (mitigates SmartScreen warnings)
if defined AIRWAR_SIGNTOOL (
    set "EXE_PATH=dist\AirWar\AirWar.exe"
    if not defined AIRWAR_SIGN_PFX (
        echo ERROR: AIRWAR_SIGN_PFX must be set when AIRWAR_SIGNTOOL is set.
        goto :cleanup_fail
    )
    echo Signing with signtool: %EXE_PATH%
    "%AIRWAR_SIGNTOOL%" sign /f "%AIRWAR_SIGN_PFX%" /p "%AIRWAR_SIGN_PASSWORD%" /tr http://timestamp.digicert.com /td sha256 /fd sha256 "%EXE_PATH%"
    if errorlevel 1 goto :cleanup_fail
) else (
    echo Skipping signtool (set AIRWAR_SIGNTOOL to enable).
)

echo.
echo === Build complete ===
echo Executable: dist\AirWar\AirWar.exe
dir dist\AirWar\AirWar.exe

:cleanup
if /i not "%KEEP_BUILD_VENV%"=="1" (
    if exist .venv-build rmdir /s /q .venv-build
)
exit /b 0

:cleanup_fail
if /i not "%KEEP_BUILD_VENV%"=="1" (
    if exist .venv-build rmdir /s /q .venv-build
)
exit /b 1
