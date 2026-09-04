@echo off
setlocal
cd /d %~dp0..

rem Stop project processes started by start scripts or AGENTS.md commands.
rem Uvicorn --reload and Vite may create child processes on Windows, so kill the full tree.

call :kill_pid_file backend-uvicorn.pid
call :kill_pid_file frontend-vite.pid

rem Fallback: if pid files are stale/missing, release known dev ports.
call :kill_port 8001
call :kill_port 5173

del /f /q backend-uvicorn.pid frontend-vite.pid 2>nul

echo Project stopped.
endlocal
exit /b 0

:kill_pid_file
if exist "%~1" (
  set /p PID=<"%~1"
  if not "%PID%"=="" (
    echo Stopping process tree from %~1: %PID%
    taskkill /PID %PID% /T /F >nul 2>nul
  )
)
exit /b 0

:kill_port
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:":%~1 .*LISTENING"') do (
  echo Releasing port %~1, PID %%p
  taskkill /PID %%p /T /F >nul 2>nul
)
exit /b 0
