@echo off
setlocal enabledelayedexpansion
title AirWar Uninstaller

set "GAME_DIR=%~dp0"
cd /d "%GAME_DIR%"

echo.
echo   ======================================
echo     AirWar - Complete Uninstaller
echo   ======================================
echo.
echo   This will permanently delete:
echo     - The entire game folder and all its contents
echo     - Saves, config, downloaded dependencies
echo     - Compiled Rust extension
echo.
echo   Location: %GAME_DIR%
echo.
choice /c YN /n /m "  Are you sure? This CANNOT be undone. [Y/N] "
if !errorlevel! equ 2 (
    echo   Cancelled.
    pause
    exit /b 0
)

echo.
echo   Removing AirWar...

REM A running script cannot delete its own folder.
REM Write a one-shot cleanup script to %TEMP% that deletes
REM the game folder, then deletes itself.
set "CLEANUP=%TEMP%\airwar_uninstall.bat"
(
    echo @echo off
    echo rmdir /s /q "%GAME_DIR%"
    echo echo AirWar has been completely removed.
    echo timeout /t 3 ^>nul
    echo del "%%~f0" ^& exit
) > "%CLEANUP%"

start "" cmd /c "%CLEANUP%"
exit
