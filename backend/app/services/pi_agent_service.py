"""以完整工具权限调用本机 Pi CLI，并转换为前端可消费的流事件。"""
import asyncio
import json
import os
import shutil
import subprocess
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PI_TIMEOUT_SECONDS = 300


def _pi_command() -> str:
    command = shutil.which("pi")
    if not command:
        raise RuntimeError("未找到 Pi CLI，请先安装并完成模型配置")
    return command


def _pi_args(prompt: str) -> tuple[str, ...]:
    return (_pi_command(), "--mode", "json", "--no-session", "--approve", prompt)


async def _start_pi(prompt: str) -> subprocess.Popen[bytes]:
    env = os.environ.copy()
    env.setdefault("NO_COLOR", "1")
    try:
        return await asyncio.to_thread(
            subprocess.Popen, _pi_args(prompt), cwd=PROJECT_ROOT, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
    except OSError as exc:
        raise RuntimeError(f"Pi 启动失败：{exc}") from exc


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
            return {"type": update["type"], "delta": update.get("delta", "")}
    if event_type == "tool_execution_start":
        return {"type": "tool_start", "id": event.get("toolCallId"), "tool": event.get("toolName"), "args": event.get("args") or {}}
    if event_type == "tool_execution_end":
        return {
            "type": "tool_end", "id": event.get("toolCallId"), "tool": event.get("toolName"),
            "is_error": bool(event.get("isError")), "output": _event_content(event.get("result")),
        }
    return None


async def stream_pi(prompt: str) -> AsyncIterator[dict[str, Any]]:
    started = time.perf_counter()
    process = await _start_pi(prompt)
    assert process.stdout is not None and process.stderr is not None
    stderr_task = asyncio.create_task(asyncio.to_thread(process.stderr.read))
    try:
        async with asyncio.timeout(PI_TIMEOUT_SECONDS):
            while line := await asyncio.to_thread(process.stdout.readline):
                try:
                    normalized = normalize_pi_event(json.loads(line))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                if normalized:
                    yield normalized
            await asyncio.to_thread(process.wait)
            stderr = (await stderr_task).decode("utf-8", errors="replace").strip()
            if process.returncode != 0:
                yield {"type": "error", "message": (stderr or f"Pi 退出码 {process.returncode}")[:1000]}
            else:
                yield {"type": "done", "duration_ms": round((time.perf_counter() - started) * 1000)}
    except TimeoutError:
        yield {"type": "error", "message": "Pi 响应超时，请稍后重试"}
    except asyncio.CancelledError:
        if process.poll() is None:
            process.kill()
            await asyncio.to_thread(process.wait)
        raise
    finally:
        if process.poll() is None:
            process.kill()
            await asyncio.to_thread(process.wait)
        if not stderr_task.done():
            stderr_task.cancel()
