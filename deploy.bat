@echo off
rem Deploy rosens to the server and verify it is serving again.
rem
rem   deploy.bat <host> [port]
rem
rem <host> is what ssh connects to
rem the same host is used for the health check. [port] defaults to 8000.

setlocal EnableDelayedExpansion

rem --- settings (server side) ---
set "REMOTE_DIR=dev/rosens"
set "SERVICE=rosens"
set "PORT=8000"
set "RETRIES=10"
set "RETRY_WAIT=2"

if "%~1"=="" (
    echo usage: %~nx0 ^<host^|user@host^> [port]
    exit /b 1
)
set "TARGET=%~1"
if not "%~2"=="" set "PORT=%~2"

rem the health check URL needs the bare host, so drop any "user@" prefix
set "HOST=%TARGET%"
for /f "tokens=2 delims=@" %%h in ("%TARGET%") do set "HOST=%%h"

echo === deploy to %TARGET% (%REMOTE_DIR%) ===
rem A command run over ssh gets a non-interactive shell, and Ubuntu's ~/.bashrc returns early for
rem those, before the PATH line the uv installer appends. So add uv's install dir explicitly.
ssh -t %TARGET% "export PATH=$HOME/.local/bin:$PATH && cd %REMOTE_DIR% && git pull && uv sync --no-dev && sudo systemctl restart %SERVICE%"
if errorlevel 1 (
    echo [FAILED] remote deploy failed - the service was left as it was
    exit /b 1
)

echo.
echo === health check http://%HOST%:%PORT%/ ===
rem ping is used instead of timeout because timeout fails when stdin is redirected
set /a "PING_N=RETRY_WAIT+1"
set "CODE="
for /l %%i in (1,1,%RETRIES%) do (
    for /f %%c in ('curl -s -o nul -w "%%{http_code}" --max-time 5 http://%HOST%:%PORT%/') do set "CODE=%%c"
    if "!CODE!"=="200" goto :healthy
    echo   %%i/%RETRIES%: HTTP !CODE! - retrying in %RETRY_WAIT%s
    ping -n !PING_N! 127.0.0.1 >nul
)
echo [FAILED] no 200 from the server (last response: !CODE!)
echo          check the server with: ssh %TARGET% "journalctl -u %SERVICE% -n 50"
exit /b 1

:healthy
echo [OK] 200
curl -s http://%HOST%:%PORT%/
echo.
exit /b 0
