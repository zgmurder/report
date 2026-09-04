@echo off
setlocal
cd /d %~dp0..

rem Start backend and frontend as process trees and record root PIDs.
rem stop-project.bat can later terminate these trees with taskkill /T /F.

if exist backend-uvicorn.pid del /f /q backend-uvicorn.pid
if exist frontend-vite.pid del /f /q frontend-vite.pid
if not exist logs mkdir logs

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$root=(Resolve-Path '.').Path;" ^
  "$logs=Join-Path $root 'logs';" ^
  "New-Item -ItemType Directory -Force -Path $logs | Out-Null;" ^
  "$env:WATCHFILES_FORCE_POLLING='true';" ^
  "$env:PYTHONUNBUFFERED='1';" ^
  "$backend=Start-Process -FilePath 'python' -ArgumentList @('-m','uvicorn','app.main:app','--host','0.0.0.0','--port','8001','--reload','--reload-dir','app','--reload-include','*.py','--reload-delay','0.5') -WorkingDirectory (Join-Path $root 'backend') -RedirectStandardOutput (Join-Path $logs 'backend-uvicorn.log') -RedirectStandardError (Join-Path $logs 'backend-uvicorn-error.log') -WindowStyle Hidden -PassThru;" ^
  "Set-Content -Path (Join-Path $root 'backend-uvicorn.pid') -Value $backend.Id;" ^
  "$frontend=Start-Process -FilePath 'npm.cmd' -ArgumentList @('run','dev','--','--host','0.0.0.0') -WorkingDirectory (Join-Path $root 'frontend') -RedirectStandardOutput (Join-Path $logs 'frontend-vite.log') -RedirectStandardError (Join-Path $logs 'frontend-vite-error.log') -WindowStyle Hidden -PassThru;" ^
  "Set-Content -Path (Join-Path $root 'frontend-vite.pid') -Value $frontend.Id;" ^
  "Write-Host ('Backend PID: '+$backend.Id); Write-Host ('Frontend PID: '+$frontend.Id);"

echo.
echo Project starting...
echo Frontend: http://localhost:5173/
echo Backend:  http://127.0.0.1:8001
echo Health:   http://127.0.0.1:8001/health
endlocal
