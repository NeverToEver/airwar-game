@echo off
setlocal enabledelayedexpansion
title AirWar with Leaderboard Server

set "ROOT=%~dp0"
cd /d "%ROOT%"

REM Prefer the project virtualenv, then fall back to any Python 3.11+.
set "PYTHON=.venv\Scripts\python.exe"
if exist "%PYTHON%" goto :launch

for %%c in (py python3 python) do (
    where %%c >nul 2>&1
    if !errorlevel! equ 0 (
        %%c -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
        if !errorlevel! equ 0 (
            set "PYTHON=%%c"
            goto :launch
        )
    )
)

echo [airwar-server] ERROR: Python 3.11 or newer not found.
pause
exit /b 1

:launch
cd /d "%ROOT%"
"%PYTHON%" run_with_server.py %*
endlocal
exit /b %errorlevel%
