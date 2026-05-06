@echo off
setlocal enabledelayedexpansion
title AirWar Uninstaller

set ROOT=%~dp0
cd /d "%ROOT%"

echo.
echo   ==============================
echo     AirWar - Uninstaller
echo   ==============================
echo.
echo   This will remove all generated files:
echo     - Virtual environment (.venv)
echo     - Rust build artifacts (airwar_core/target)
echo     - Python bytecode cache (__pycache__)
echo     - Installed wheel (pip uninstall airwar_core)
echo.
echo   Your source code, saves, and config files
echo   will NOT be affected.
echo.
choice /c YN /n /m "  Proceed with uninstall? [Y/N] "
if !errorlevel! equ 2 (
    echo   Cancelled.
    pause
    exit /b 0
)

echo.
echo   [..] Removing virtual environment...
if exist "%ROOT%.venv" (
    rmdir /s /q "%ROOT%.venv" 2>nul
    echo   [OK] .venv removed
) else (
    echo   [--] .venv not found
)

echo   [..] Removing Rust build cache...
if exist "%ROOT%airwar_core\target" (
    rmdir /s /q "%ROOT%airwar_core\target" 2>nul
    echo   [OK] target/ removed
) else (
    echo   [--] target/ not found
)

echo   [..] Removing Python cache files...
for /d /r "%ROOT%" %%d in (__pycache__) do (
    if exist "%%d" rmdir /s /q "%%d" 2>nul
)
echo   [OK] __pycache__ cleaned

echo   [..] Uninstalling airwar_core package...
for %%c in (py python3 python) do (
    where %%c >nul 2>&1
    if !errorlevel! equ 0 (
        %%c -m pip uninstall -y airwar_core >nul 2>&1
        goto :pip_done
    )
)
:pip_done
echo   [OK] Package unregistered

echo.
echo   ==============================
echo     Uninstall complete.
echo   ==============================
echo.
echo   To play again, just run: run.bat
echo.
pause
endlocal
