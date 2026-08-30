"""Restricted, opt-in bridge to the local Pi CLI.

This is defense in depth, not a replacement for an OS/container sandbox.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import signal
import subprocess
import tempfile
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from app.core.config import get_settings

settings = get_settings()
_PI_SEMAPHORE = asyncio.Semaphore(max(1, settings.pi_agent_max_concurrency))
_SAFE_ENV_NAMES = {"PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC"}
_SAFE_ENV_PREFIXES = ("PI_", "OPENAI_", "ANTHROPIC_", "AZURE_OPENAI_", "DASHSCOPE_")
_SENSITIVE_MARKERS = ("DATABASE_URL", "JWT", "ADMIN_PASSWORD", "LLM_API_KEY", "SECRET", "TOKEN")


def _pi_command() -> str:
    command = shutil.which("pi")
    if not command:
        raise RuntimeError("未找到 Pi CLI，请先安装并完成模型配置")
    return command


def _pi_args(prompt: str) -> tuple[str, ...]:
    # Deliberately no --approve: unattended full-tool approval is unsafe.
    return (
        _pi_command(), "--mode", "json", "--print", "--no-session", "--no-approve",
        "--tools", "read,grep,find,ls", "--no-extensions", "--no-skills",
        "--no-prompt-templates", "--no-context-files", prompt,
    )


def _minimal_environment(sandbox_dir: Path | None = None) -> dict[str, str]:
    env: dict[str, str] = {}
    for name, value in os.environ.items():
        upper = name.upper()
        if upper in _SAFE_ENV_NAMES or upper.startswith(_SAFE_ENV_PREFIXES):
            if not any(marker in upper for marker in _SENSITIVE_MARKERS):
                env[name] = value
    if sandbox_dir is not None:
        # Keep all CLI state/cache/temp locations inside the disposable workdir;
        # never reveal the host user's profile paths to the child process.
        dirs = {
            "HOME": sandbox_dir / "home",
            "USERPROFILE": sandbox_dir / "profile",
            "APPDATA": sandbox_dir / "appdata",
            "LOCALAPPDATA": sandbox_dir / "localappdata",
            "TEMP": sandbox_dir / "temp",
            "TMP": sandbox_dir / "tmp",
        }
        for name, path in dirs.items():
            path.mkdir(parents=True, exist_ok=True)
            env[name] = str(path)
    env["NO_COLOR"] = "1"
    return env


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: "[REDACTED]" if any(marker in str(key).upper() for marker in _SENSITIVE_MARKERS) else _redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value[:100]]
    if isinstance(value, str):
        return value[:8000]
    return value


async def _start_pi(prompt: str, cwd: Path) -> subprocess.Popen[bytes]:
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    kwargs: dict[str, Any] = {"start_new_session": True} if os.name != "nt" else {}
    try:
        return await asyncio.to_thread(
            subprocess.Popen,
            _pi_args(prompt),
            cwd=cwd,
            env=_minimal_environment(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=creationflags,
            **kwargs,
        )
    except OSError as exc:
        raise RuntimeError(f"Pi 启动失败：{exc}") from exc


async def _kill_process_tree(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            await asyncio.to_thread(subprocess.run, ["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, timeout=10)
        else:
            os.killpg(process.pid, signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        process.kill()
    await asyncio.to_thread(process.wait)


def _event_content(result: Any) -> str:
    if not isinstance(result, dict):
        return ""
    content = result.get("content") or []
    return "\n".join(item.get("text", "") for item in content if isinstance(item, dict))[:8000]


def normalize_pi_event(event: dict[str, Any]) -> dict[str, Any] | None:
    event_type = event.get("type")
    if event_type == "session":
        return {"type": "session", "session_id": event.get("id")}
    if event_type == "agent_start":
        return {"type": "status", "status": "running", "message": "Pi 已开始处理任务"}
    if event_type == "message_update":
        update = event.get("assistantMessageEvent") or {}
        if update.get("type") in {"text_delta", "thinking_delta"}:
            return {"type": update["type"], "delta": str(update.get("delta", ""))[:8000]}
    if event_type == "tool_execution_start":
        return {"type": "tool_start", "id": event.get("toolCallId"), "tool": event.get("toolName"), "args": _redact(event.get("args") or {})}
    if event_type == "tool_execution_end":
        return {"type": "tool_end", "id": event.get("toolCallId"), "tool": event.get("toolName"), "is_error": bool(event.get("isError")), "output": _redact(_event_content(event.get("result")))}
    return None


async def stream_pi(prompt: str) -> AsyncIterator[dict[str, Any]]:
    started = time.perf_counter()
    async with _PI_SEMAPHORE:
        with tempfile.TemporaryDirectory(prefix="report-pi-agent-") as temp_dir:
            process = await _start_pi(prompt, Path(temp_dir))
            assert process.stdout is not None and process.stderr is not None
            stderr_task = asyncio.create_task(asyncio.to_thread(process.stderr.read))
            try:
                async with asyncio.timeout(settings.pi_agent_timeout_seconds):
                    while line := await asyncio.to_thread(process.stdout.readline):
                        try:
                            normalized = normalize_pi_event(json.loads(line))
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            continue
                        if normalized:
                            yield normalized
                    await asyncio.to_thread(process.wait)
                    stderr = _redact((await stderr_task).decode("utf-8", errors="replace").strip())
                    if process.returncode != 0:
                        yield {"type": "error", "message": (stderr or f"Pi 退出码 {process.returncode}")[:1000]}
                    else:
                        yield {"type": "done", "duration_ms": round((time.perf_counter() - started) * 1000)}
            except TimeoutError:
                yield {"type": "error", "message": "Pi 响应超时，请稍后重试"}
            except asyncio.CancelledError:
                await _kill_process_tree(process)
                raise
            finally:
                await _kill_process_tree(process)
                if not stderr_task.done():
                    stderr_task.cancel()
