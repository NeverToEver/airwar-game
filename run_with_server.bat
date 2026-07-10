@echo off
setlocal EnableExtensions EnableDelayedExpansion
title AirWar with Leaderboard Server

set "ROOT=%~dp0"
cd /d "%ROOT%"
set "BOOTSTRAP_ARGS="
set "SERVER_ARGS="

:parse_args
if "%~1"=="" goto :prepare
if /i "%~1"=="--help" goto :help
if "%~1"=="-h" goto :help
if /i "%~1"=="--install-deps" (
    set "BOOTSTRAP_ARGS=!BOOTSTRAP_ARGS! --install-deps"
    shift
    goto :parse_args
)
if /i "%~1"=="--rebuild-rust" (
    set "BOOTSTRAP_ARGS=!BOOTSTRAP_ARGS! --rebuild-rust"
    shift
    goto :parse_args
)
if /i "%~1"=="--skip-rust" (
    set "BOOTSTRAP_ARGS=!BOOTSTRAP_ARGS! --skip-rust"
    shift
    goto :parse_args
)
if "%~1"=="--" (
    shift
    goto :collect_server_args
)
set "SERVER_ARGS=!SERVER_ARGS! "%~1""
shift
goto :parse_args

:collect_server_args
if "%~1"=="" goto :prepare
set "SERVER_ARGS=!SERVER_ARGS! "%~1""
shift
goto :collect_server_args

:prepare
call "%ROOT%run.bat" --prepare-only %BOOTSTRAP_ARGS%
if errorlevel 1 (
    echo [airwar-server] Environment preparation failed.
    pause
    endlocal
    exit /b 1
)

"%ROOT%.venv\Scripts\python.exe" "%ROOT%run_with_server.py" %SERVER_ARGS%
set "EXIT_CODE=%ERRORLEVEL%"
pause
endlocal
exit /b %EXIT_CODE%

:help
echo Usage: run_with_server.bat [launcher options] [server options]
echo.
echo Launcher options: --install-deps, --rebuild-rust, --skip-rust
echo Server options:   --host HOST, --port PORT, --debug, --game-arg=ARG
endlocal
exit /b 0
