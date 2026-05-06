@echo off
setlocal enabledelayedexpansion
title AirWar Launcher

set "ROOT=%~dp0"
cd /d "%ROOT%"

echo ========================================
echo   AirWar Launcher
echo ========================================
echo.

:: ── Find Python ────────────────────────────────────────────
set "PYTHON="
for %%c in (py python3 python) do (
    where %%c >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON=%%c"
        goto :found_python
    )
)
:found_python

if "%PYTHON%"=="" (
    echo [ERROR] Python not found in PATH.
    echo.
    echo Install Python 3.12+ from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)
%PYTHON% --version
echo Python found: %PYTHON%
echo.

:: ── Check Python version ───────────────────────────────────
for /f "tokens=2 delims= " %%v in ('%PYTHON% --version 2^>^&1') do set "VER=%%v"
for /f "tokens=1 delims=." %%a in ("!VER!") do set "MAJOR=%%a"
for /f "tokens=2 delims=." %%a in ("!VER!") do set "MINOR=%%a"
if !MAJOR! lss 3 (
    echo [ERROR] Python 3.11+ required, found !VER!
    pause
    exit /b 1
)
if !MAJOR! equ 3 if !MINOR! lss 11 (
    echo [ERROR] Python 3.11+ required, found !VER!
    pause
    exit /b 1
)
echo Python !VER! OK
echo.

:: ── Find Cargo ────────────────────────────────────────────
where cargo >nul 2>&1
if !errorlevel! neq 0 (
    echo [ERROR] Rust / Cargo not found.
    echo Install from: https://rustup.rs/
    echo After installing, re-run run.bat
    pause
    exit /b 1
)
echo Cargo OK
echo.

:: ── Python deps ───────────────────────────────────────────
%PYTHON% -c "import pygame; print('pygame', pygame.version.ver)" >nul 2>&1
if !errorlevel! neq 0 (
    echo Installing Python dependencies...
    %PYTHON% -m pip install --user -r requirements.txt
    if !errorlevel! neq 0 (
        echo [ERROR] pip install failed. Check your internet connection.
        pause
        exit /b 1
    )
)
echo Python dependencies OK
echo.

:: ── Rust extension ────────────────────────────────────────
echo Building Rust extension ^(this may take a few minutes^)...
cd /d "%ROOT%airwar_core"

%PYTHON% -c "import maturin" >nul 2>&1
if !errorlevel! neq 0 (
    %PYTHON% -m pip install --user maturin
)

%PYTHON% -m maturin develop --release
if !errorlevel! neq 0 (
    cd /d "%ROOT%"
    echo.
    echo ========================================
    echo [ERROR] Rust build FAILED.
    echo.
    echo On Windows this usually means you need:
    echo   Visual Studio Build Tools with C++ workload
    echo   Download: https://aka.ms/vs/17/release/vs_BuildTools.exe
    echo   Select "Desktop development with C++" during install
    echo.
    echo OR install with: winget install Microsoft.VisualStudio.2022.BuildTools
    echo ========================================
    pause
    exit /b 1
)
cd /d "%ROOT%"
echo Rust extension OK
echo.

:: ── Launch ────────────────────────────────────────────────
echo Starting AirWar...
echo ========================================
echo.
%PYTHON% main.py

echo.
echo AirWar has exited ^(code: !errorlevel!^).
pause
endlocal
