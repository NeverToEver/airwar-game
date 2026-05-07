@echo off
setlocal enabledelayedexpansion
title AirWar

set "ROOT=%~dp0"
cd /d "%ROOT%"

set "INSTALL_DEPS=%AIRWAR_INSTALL_DEPS%"
if "%INSTALL_DEPS%"=="" set "INSTALL_DEPS=0"
if "%~1"=="" goto :args_done
if "%~1"=="--install-deps" set "INSTALL_DEPS=1" & goto :args_done
if "%~1"=="--help" goto :help
if "%~1"=="-h" goto :help
echo   [ERROR] Unknown option: %~1
goto :help_error
:args_done
if not "%~2"=="" (
    echo   [ERROR] Too many arguments.
    goto :help_error
)

echo.
echo   ==============================
echo     AirWar - One-Click Launcher
echo   ==============================
echo.

REM Step 1: Find Python 3.11+
set PYTHON=
for %%c in (py python3 python) do (
    where %%c >nul 2>&1
    if !errorlevel! equ 0 (
        %%c -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
        if !errorlevel! equ 0 (
            set PYTHON=%%c
            goto :python_done
        )
    )
)
echo   [ERROR] Python 3.11 or newer not found.
echo.
echo   Please install Python from:
echo     https://www.python.org/downloads/
echo   Make sure to check "Add Python to PATH" during install.
echo.
pause
exit /b 1

:python_done
for /f "tokens=*" %%v in ('%PYTHON% --version 2^>^&1') do set "PYTHON_VERSION=%%v"
echo   [OK] %PYTHON_VERSION%

REM Step 2: Create virtual environment.
set "VENV=%ROOT%.venv"
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

REM Step 3: Install Python dependencies into venv.
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

REM Step 4: Optional Rust native extension.
where cargo >nul 2>&1
if !errorlevel! equ 0 goto :cargo_ok
if exist "%USERPROFILE%\.cargo\bin\cargo.exe" (
    set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
    goto :cargo_ok
)

if /i "%INSTALL_DEPS%"=="true" set "INSTALL_DEPS=1"
if /i "%INSTALL_DEPS%"=="yes" set "INSTALL_DEPS=1"
if /i "%INSTALL_DEPS%"=="1" (
    echo.
    echo   [..] Downloading Rust installer...
    curl -L --progress-bar -o "%TEMP%\rustup-init.exe" https://win.rustup.rs/x86_64
    if !errorlevel! neq 0 (
        echo   [ERROR] Failed to download Rust installer.
        echo   Please install manually from https://rustup.rs/
        pause
        exit /b 1
    )
    echo   [..] Running Rust installer...
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
    pause
    exit /b 0
) else (
    echo   [WARN] Cargo not found. AirWar will use the pure-Python fallback.
    echo          For Rust acceleration, install Rust from https://rustup.rs/
    echo          To let this script install it, rerun: run.bat --install-deps
    goto :launch
)

:cargo_ok
echo   [OK] Cargo found
echo   [..] Installing maturin build tool...
python -m pip install --quiet "maturin>=1,<2" >nul 2>&1

echo   [..] Compiling native extension...
cd /d "%ROOT%airwar_core"
python -m maturin develop --release 2>&1
if !errorlevel! neq 0 (
    cd /d "%ROOT%"
    echo   [WARN] Rust compilation failed. AirWar will use the pure-Python fallback.
    echo          Visual C++ Build Tools are required for Rust acceleration.
    echo          Download: https://aka.ms/vs/17/release/vs_BuildTools.exe
    goto :launch
)
cd /d "%ROOT%"
echo   [OK] Native extension compiled

:launch
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
exit /b 0

:help
echo Usage: run.bat [--install-deps]
echo.
echo By default this script only creates the project virtualenv and installs
echo Python packages into it. Rust is installed only when --install-deps is
echo passed or AIRWAR_INSTALL_DEPS=1 is set.
exit /b 0

:help_error
echo Usage: run.bat [--install-deps]
exit /b 2
