@echo off
setlocal
cd /d %~dp0..\backend

rem Windows 下强制 watchfiles 使用轮询，避免文件变更事件丢失导致热更新失效。
set "WATCHFILES_FORCE_POLLING=true"
set "PYTHONUNBUFFERED=1"

python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload --reload-dir app --reload-include "*.py" --reload-delay 0.5
endlocal
