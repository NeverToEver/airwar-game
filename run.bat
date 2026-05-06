@echo off
setlocal enabledelayedexpansion
title AirWar Launcher

set ROOT=%~dp0
cd /d "%ROOT%"

echo -----------------------------------------
echo   AirWar Launcher
echo -----------------------------------------
echo.

REM ---- Find Python ----
set PYTHON=
for %%c in (py python3 python) do (
    where %%c >nul 2>&1
    if !errorlevel! equ 0 (
        set PYTHON=%%c
        goto :found_python
    )
)
:found_python

if "%PYTHON%"=="" (
    echo [ERROR] Python not found in PATH.
    echo.
    echo Install Python 3.12+ from: https://www.python.org/downloads/
    echo Check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)
echo [OK] Python: %PYTHON%
%PYTHON% --version
echo.

REM ---- Python deps ----
echo [..] Checking Python dependencies...
%PYTHON% -c "import pygame" >nul 2>&1
if !errorlevel! neq 0 (
    echo [..] Installing pygame, pillow etc...
    %PYTHON% -m pip install --user -r requirements.txt
    if !errorlevel! neq 0 (
        echo [FAIL] pip install failed. Check internet connection.
        pause
        exit /b 1
    )
)
echo [OK] Python dependencies
echo.

REM ---- Rust / Cargo ----
where cargo >nul 2>&1
if !errorlevel! neq 0 (
    echo [WARN] Rust/Cargo not found.
    echo        Download: https://rustup.rs/
    echo        After install, re-run run.bat
    pause
    exit /b 1
)
echo [OK] Cargo found
echo.

REM ---- Build Rust extension ----
echo [..] Building Rust extension (may take a few minutes)...
cd /d "%ROOT%airwar_core"

%PYTHON% -c "import maturin" >nul 2>&1
if !errorlevel! neq 0 (
    %PYTHON% -m pip install --user maturin
)

%PYTHON% -m maturin develop --release
if !errorlevel! neq 0 (
    cd /d "%ROOT%"
    echo.
    echo [FAIL] Rust build failed.
    echo.
    echo On Windows this usually needs:
    echo   Microsoft Visual C++ Build Tools
    echo   https://aka.ms/vs/17/release/vs_BuildTools.exe
    echo   Select "Desktop development with C++" during install
    echo.
    pause
    exit /b 1
)
cd /d "%ROOT%"
echo [OK] Rust extension built
echo.

REM ---- Launch ----
echo -----------------------------------------
echo   Starting AirWar...
echo -----------------------------------------
%PYTHON% main.py

echo.
echo AirWar exited.
pause
endlocal
