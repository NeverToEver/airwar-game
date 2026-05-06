@echo off
setlocal enabledelayedexpansion
title AirWar

set ROOT=%~dp0
cd /d "%ROOT%"

echo.
echo   ==============================
echo     AirWar - One-Click Launcher
echo   ==============================
echo.

REM ----------------------------------------------------------------
REM  STEP 1: Find Python (try "py" launcher first, then "python3", then "python")
REM ----------------------------------------------------------------
set PYTHON=
for %%c in (py python3 python) do (
    where %%c >nul 2>&1
    if !errorlevel! equ 0 (
        set PYTHON=%%c
        goto :step1_done
    )
)
echo   [ERROR] Python not found.
echo.
echo   Please install Python 3.12+ from:
echo     https://www.python.org/downloads/
echo   Make sure to check "Add Python to PATH" during install.
echo.
pause
exit /b 1

:step1_done
%PYTHON% --version 2>&1 | findstr /i "Python" >nul
echo   [OK] Python found

REM ----------------------------------------------------------------
REM  STEP 2: Create virtual environment (if missing)
REM ----------------------------------------------------------------
set VENV=%ROOT%.venv
if not exist "%VENV%\Scripts\python.exe" (
    echo   [..] Creating virtual environment...
    %PYTHON% -m venv "%VENV%" >nul 2>&1
    if !errorlevel! neq 0 (
        echo   [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)
call "%VENV%\Scripts\activate.bat" >nul 2>&1
echo   [OK] Virtual environment ready

REM ----------------------------------------------------------------
REM  STEP 3: Install Python dependencies into venv
REM ----------------------------------------------------------------
echo   [..] Checking Python packages...
python -c "import pygame; import PIL" >nul 2>&1
if !errorlevel! neq 0 (
    echo   [..] Downloading pygame, pillow, etc...
    python -m pip install --quiet -r requirements.txt
    if !errorlevel! neq 0 (
        echo   [ERROR] Failed to install Python packages.
        echo   Check your internet connection and try again.
        pause
        exit /b 1
    )
)
echo   [OK] Python packages ready

REM ----------------------------------------------------------------
REM  STEP 4: Check for Rust / Cargo
REM ----------------------------------------------------------------
REM Try PATH first, then default install location
where cargo >nul 2>&1
if !errorlevel! equ 0 goto :cargo_ok
if exist "%USERPROFILE%\.cargo\bin\cargo.exe" (
    set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
    goto :cargo_ok
)
REM Cargo not found anywhere - offer to install
    echo.
    echo   [WARNING] Rust toolchain not found.
    echo.
    echo   This game requires Rust to compile its native extension.
    echo   It's a one-time setup -- takes about 5 minutes.
    echo.
    echo   Would you like to install Rust automatically now? (Y/N)
    echo.
    choice /c YN /n /m "  Install Rust? [Y/N] "
    if !errorlevel! equ 2 (
        echo   Skipped. Please install Rust manually from https://rustup.rs/
        pause
        exit /b 1
    )
    echo.
    echo   [..] Downloading Rust installer...
    curl -L --progress-bar -o "%TEMP%\rustup-init.exe" https://win.rustup.rs/x86_64
    if !errorlevel! neq 0 (
        echo   [ERROR] Failed to download Rust installer.
        echo   Please install manually from https://rustup.rs/
        pause
        exit /b 1
    )
    echo   [..] Running Rust installer (follow the prompts)...
    "%TEMP%\rustup-init.exe" -y --default-toolchain stable
    if !errorlevel! neq 0 (
        echo   [ERROR] Rust installation failed.
        echo   Please install manually from https://rustup.rs/
        pause
        exit /b 1
    )
    del "%TEMP%\rustup-init.exe"
    echo   [OK] Rust installed
    echo.
    echo   Restart this launcher to continue.
    echo   (You may need to restart your terminal or File Explorer first)
    pause
    exit /b 0
:cargo_ok
echo   [OK] Cargo found

REM ----------------------------------------------------------------
REM  STEP 5: Build Rust native extension (airwar_core)
REM ----------------------------------------------------------------
echo   [..] Installing maturin build tool...
python -m pip install --quiet maturin >nul 2>&1

echo   [..] Compiling native extension (one-time build)...
cd /d "%ROOT%airwar_core"
python -m maturin develop --release 2>&1
if !errorlevel! neq 0 (
    cd /d "%ROOT%"
    echo.
    echo   [ERROR] Rust compilation failed.
    echo.
    echo   This usually means one of:
    echo     - Visual C++ Build Tools are not installed
    echo       Download: https://aka.ms/vs/17/release/vs_BuildTools.exe
    echo       Select "Desktop development with C++" during install
    echo     - Or your Rust installation is incomplete
    echo       Try running: rustup default stable
    echo.
    pause
    exit /b 1
)
cd /d "%ROOT%"
echo   [OK] Native extension compiled

REM ----------------------------------------------------------------
REM  STEP 6: Launch the game
REM ----------------------------------------------------------------
echo.
echo   ==============================
echo     Launching AirWar...
echo   ==============================
echo.
python main.py

echo.
echo   AirWar closed.
pause
endlocal
