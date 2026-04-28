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

REM 1. Build Rust extension
echo [1/4] Building Rust extension...
cd airwar_core
cargo build --release
cd ..

REM 2. Install Rust extension
echo [2/4] Installing Rust extension...
set RUST_DLL=airwar_core\target\release\airwar_core.dll
if exist "%RUST_DLL%" (
    for /f "tokens=*" %%i in ('python -c "import site; print(site.getusersitepackages())"') do set SITE_PKGS=%%i
    if not exist "%SITE_PKGS%\airwar_core" mkdir "%SITE_PKGS%\airwar_core"
    copy /Y "%RUST_DLL%" "%SITE_PKGS%\airwar_core\airwar_core.cp312-win_amd64.pyd"
    echo    Rust extension installed.
) else (
    echo    WARNING: Rust .dll not found at %RUST_DLL%
    echo    Game will fall back to pure Python.
)

REM 3. Install PyInstaller
echo [3/4] Checking PyInstaller...
python -c "import PyInstaller" 2>nul || pip install pyinstaller

REM 4. Build standalone executable
echo [4/4] Building standalone executable...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

pyinstaller ^
    --name="AirWar" ^
    --add-data="airwar\data;airwar\data" ^
    --collect-all airwar_core ^
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
