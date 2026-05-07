@echo off
setlocal enabledelayedexpansion
title AirWar Local Uninstaller

set "GAME_DIR=%~dp0"
if "!GAME_DIR:~-1!"=="\" set "GAME_DIR=!GAME_DIR:~0,-1!"
cd /d "%GAME_DIR%"

echo.
echo   ==============================
echo     AirWar - Local Uninstaller
echo   ==============================
echo.
echo   This will remove local environments, build artifacts, and disposable caches:
echo     .venv, .venv-build, build\, dist\, target\, airwar_core\target\
echo     AirWar.spec, airwar.spec, __pycache__, .pytest_cache, .ruff_cache
echo     airwar\data\generated_assets\
echo     platform generated-asset cache
echo.
echo   Source code, saves, account data, and config will NOT be affected.
echo.
choice /c YN /n /m "  Proceed? [Y/N] "
if !errorlevel! equ 2 (
    echo   Cancelled.
    pause
    exit /b 0
)

echo.
if exist ".venv\Scripts\python.exe" (
    echo   [..] Uninstalling airwar_core from .venv...
    ".venv\Scripts\python.exe" -m pip uninstall -y airwar_core >nul 2>nul
    echo   [OK] airwar_core package
)

call :remove_path ".venv"
call :remove_path ".venv-build"
call :remove_path "build"
call :remove_path "dist"
call :remove_path "target"
call :remove_path "airwar_core\target"
call :remove_path "AirWar.spec"
call :remove_path "airwar.spec"
call :remove_path ".pytest_cache"
call :remove_path ".ruff_cache"
call :remove_path "airwar\data\generated_assets"
for /f "usebackq delims=" %%p in (`python -c "from airwar.utils.platform_paths import generated_asset_cache_dir; print(generated_asset_cache_dir())" 2^>nul`) do (
    echo %%p | findstr /i /r "\\airwar\\generated_assets$ \\airwar\\Cache\\generated_assets$" >nul
    if !errorlevel! equ 0 call :remove_path "%%p"
)

echo   [..] Removing __pycache__ directories...
for /d /r %%d in (__pycache__) do (
    if exist "%%d" rmdir /s /q "%%d" 2>nul
)
echo   [OK] __pycache__

echo.
echo   Done. Run run.bat to play again.
pause
exit /b 0

:remove_path
set "TARGET=%~1"
if exist "%TARGET%\" (
    rmdir /s /q "%TARGET%"
    echo   [OK] %TARGET%
) else if exist "%TARGET%" (
    del /f /q "%TARGET%"
    echo   [OK] %TARGET%
) else (
    echo   [--] %TARGET%
)
exit /b 0
