@echo off
setlocal enabledelayedexpansion
title AirWar Uninstaller

set "GAME_DIR=%~dp0"
if "!GAME_DIR:~-1!"=="\" set "GAME_DIR=!GAME_DIR:~0,-1!"
cd /d "%GAME_DIR%"

echo.
echo   ======================================
echo     AirWar - Complete Uninstaller
echo   ======================================
echo.
echo   This will permanently delete:
echo     %GAME_DIR%
echo.
echo   Including all game files, saves, config, and dependencies.
echo.
choice /c YN /n /m "  Are you sure? [Y/N] "
if !errorlevel! equ 2 (
    echo   Cancelled.
    pause
    exit /b 0
)

echo.
echo   Removing AirWar...

set "TMP=%TEMP%\airwar_uninst.bat"
(
    echo @echo off
    echo rmdir /s /q "%GAME_DIR%" 2^>nul
    echo if not exist "%GAME_DIR%" echo AirWar has been completely removed.^& echo.^& pause^& del "%%~f0"^& exit
    echo echo WARNING: Could not remove all files.
    echo echo The game folder may be in use by another program.
    echo echo Close it and delete the folder manually:
    echo echo   %GAME_DIR%
    echo echo.
    echo pause
    echo del "%%~f0"
) > "%TMP%"

start "" cmd /c "%TMP%"
exit
