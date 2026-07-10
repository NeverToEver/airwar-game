@echo off
setlocal EnableExtensions EnableDelayedExpansion
title AirWar

set "ROOT=%~dp0"
cd /d "%ROOT%"

set "INSTALL_DEPS=%AIRWAR_INSTALL_DEPS%"
if "%INSTALL_DEPS%"=="" set "INSTALL_DEPS=0"
set "PREPARE_ONLY=0"
set "SKIP_RUST=0"
set "REBUILD_RUST=0"
set "APP_ARGS="

:parse_args
if "%~1"=="" goto :args_done
if /i "%~1"=="--install-deps" (
    set "INSTALL_DEPS=1"
    shift
    goto :parse_args
)
if /i "%~1"=="--rebuild-rust" (
    set "REBUILD_RUST=1"
    shift
    goto :parse_args
)
if /i "%~1"=="--skip-rust" (
    set "SKIP_RUST=1"
    shift
    goto :parse_args
)
if /i "%~1"=="--prepare-only" (
    set "PREPARE_ONLY=1"
    shift
    goto :parse_args
)
if /i "%~1"=="--help" goto :help
if "%~1"=="-h" goto :help
if "%~1"=="--" (
    shift
    goto :collect_game_args
)
set "APP_ARGS=!APP_ARGS! "%~1""
shift
goto :parse_args

:collect_game_args
if "%~1"=="" goto :args_done
set "APP_ARGS=!APP_ARGS! "%~1""
shift
goto :collect_game_args

:args_done
echo.
echo   ==============================
echo     AirWar Launcher
echo   ==============================
echo.

set "PYTHON="
for %%C in (py python3 python) do (
    where %%C >nul 2>&1
    if !errorlevel! equ 0 (
        %%C -c "import sys; raise SystemExit(0 if sys.version_info ^>= (3, 11) else 1)" >nul 2>&1
        if !errorlevel! equ 0 (
            set "PYTHON=%%C"
            goto :python_ready
        )
    )
)
echo   [ERROR] Python 3.11 or newer was not found.
echo           Install it from https://www.python.org/downloads/
goto :fail

:python_ready
for /f "tokens=*" %%V in ('%PYTHON% --version 2^>^&1') do set "PYTHON_VERSION=%%V"
echo   [OK] %PYTHON_VERSION%

set "VENV=%ROOT%.venv"
set "VENV_PYTHON=%VENV%\Scripts\python.exe"
if not exist "%VENV_PYTHON%" (
    echo   [..] Creating virtual environment...
    %PYTHON% -m venv "%VENV%"
    if errorlevel 1 (
        echo   [ERROR] Failed to create the virtual environment.
        goto :fail
    )
) else (
    "%VENV_PYTHON%" -c "import sys; raise SystemExit(0 if sys.version_info ^>= (3, 11) else 1)" >nul 2>&1
    if errorlevel 1 (
        echo   [ERROR] Existing .venv does not use Python 3.11 or newer.
        echo           Remove .venv and run this launcher again.
        goto :fail
    )
)
echo   [OK] Virtual environment ready

set "DEPENDENCY_MARKER=%VENV%\.airwar-runtime-deps"
set "NEED_DEPS=0"
if not exist "%DEPENDENCY_MARKER%" set "NEED_DEPS=1"
if "%ROOT%requirements.txt" newer "%DEPENDENCY_MARKER%" set "NEED_DEPS=1"
if "%ROOT%pyproject.toml" newer "%DEPENDENCY_MARKER%" set "NEED_DEPS=1"
if "!NEED_DEPS!"=="0" (
    "%VENV_PYTHON%" -c "import numpy, PIL, pygame" >nul 2>&1
    if errorlevel 1 set "NEED_DEPS=1"
)
if "!NEED_DEPS!"=="1" (
    echo   [..] Installing runtime dependencies...
    "%VENV_PYTHON%" -m pip install --quiet --disable-pip-version-check -r requirements.txt
    if errorlevel 1 (
        echo   [ERROR] Failed to install runtime dependencies.
        goto :fail
    )
    type nul > "%DEPENDENCY_MARKER%"
)
echo   [OK] Runtime dependencies ready

if /i "%SKIP_RUST%"=="1" goto :rust_skipped
if exist "%USERPROFILE%\.cargo\bin\cargo.exe" set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
where cargo >nul 2>&1
if !errorlevel! neq 0 goto :cargo_missing
goto :cargo_ready

:cargo_missing
if /i "%INSTALL_DEPS%"=="true" set "INSTALL_DEPS=1"
if /i "%INSTALL_DEPS%"=="yes" set "INSTALL_DEPS=1"
if /i not "%INSTALL_DEPS%"=="1" (
    echo   [WARN] Cargo not found; using the Python fallback.
    echo          Install Rust from https://rustup.rs/ or run: run.bat --install-deps
    goto :prepared
)
where curl >nul 2>&1
if !errorlevel! neq 0 (
    echo   [ERROR] curl is required to install Rust automatically.
    goto :fail
)
echo   [..] Installing Rust toolchain...
curl -L --fail --progress-bar -o "%TEMP%\rustup-init.exe" https://win.rustup.rs/x86_64
if errorlevel 1 goto :rust_install_failed
"%TEMP%\rustup-init.exe" -y --default-toolchain stable
if errorlevel 1 goto :rust_install_failed
del /q "%TEMP%\rustup-init.exe" >nul 2>&1
set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
where cargo >nul 2>&1
if !errorlevel! neq 0 goto :rust_install_failed

:cargo_ready
set "RUST_MARKER=%VENV%\.airwar-rust-extension"
set "NEED_RUST=0"
if /i "%REBUILD_RUST%"=="1" (
    if exist "%RUST_MARKER%" del /q "%RUST_MARKER%" >nul 2>&1
    set "NEED_RUST=1"
)
if not exist "%RUST_MARKER%" set "NEED_RUST=1"
if "%ROOT%airwar_core\Cargo.toml" newer "%RUST_MARKER%" set "NEED_RUST=1"
if "%ROOT%airwar_core\Cargo.lock" newer "%RUST_MARKER%" set "NEED_RUST=1"
if "%ROOT%airwar_core\pyproject.toml" newer "%RUST_MARKER%" set "NEED_RUST=1"
for /r "%ROOT%airwar_core\src" %%F in (*.rs) do if "%%F" newer "%RUST_MARKER%" set "NEED_RUST=1"
if "!NEED_RUST!"=="0" (
    "%VENV_PYTHON%" -c "from airwar.core_bindings import RUST_AVAILABLE; raise SystemExit(0 if RUST_AVAILABLE else 1)" >nul 2>&1
    if errorlevel 1 set "NEED_RUST=1"
)
if "!NEED_RUST!"=="0" (
    echo   [OK] Rust extension ready
    goto :prepared
)

echo   [..] Building optional Rust extension...
"%VENV_PYTHON%" -m pip install --quiet --disable-pip-version-check "maturin>=1,<2"
if errorlevel 1 (
    echo   [WARN] Could not install maturin; using the Python fallback.
    goto :prepared
)
"%VENV_PYTHON%" -m maturin develop --release --manifest-path "%ROOT%airwar_core\Cargo.toml"
if errorlevel 1 (
    echo   [WARN] Rust extension build failed; using the Python fallback.
    goto :prepared
)
type nul > "%RUST_MARKER%"
echo   [OK] Rust extension built
goto :prepared

:rust_install_failed
echo   [WARN] Rust installation failed; using the Python fallback.
echo          Install manually from https://rustup.rs/
goto :prepared

:rust_skipped
echo   [WARN] Rust extension skipped

:prepared
if "%PREPARE_ONLY%"=="1" (
    echo   [OK] Runtime environment prepared
    endlocal
    exit /b 0
)

echo.
echo   Launching AirWar...
"%VENV_PYTHON%" main.py %APP_ARGS%
set "GAME_EXIT=%ERRORLEVEL%"
echo.
echo   AirWar closed.
pause
endlocal
exit /b %GAME_EXIT%

:help
echo Usage: run.bat [launcher options] [-- game options]
echo.
echo Launcher options:
echo   --install-deps   Install Rust when Cargo is unavailable.
echo   --rebuild-rust   Rebuild the optional Rust extension.
echo   --skip-rust      Do not build the optional Rust extension.
echo   --prepare-only   Prepare the virtual environment, then exit.
echo   -h, --help       Show this help.
echo.
echo Game options are forwarded to AirWar. Example: run.bat -- --debug
endlocal
exit /b 0

:fail
if "%PREPARE_ONLY%"=="1" (
    endlocal
    exit /b 1
)
pause
endlocal
exit /b 1
