import json

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.schemas.pi_agent import PiAgentRequest
from app.services.pi_agent_service import stream_pi

router = APIRouter()


@router.post("/stream", summary="流式调用本机 Pi Agent")
async def stream(payload: PiAgentRequest) -> StreamingResponse:
    if not get_settings().pi_agent_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pi Agent 默认禁用；仅在完成外部沙箱隔离后设置 PI_AGENT_ENABLED=true",
        )

    async def event_stream():
        try:
            async for event in stream_pi(payload.prompt):
                yield json.dumps(event, ensure_ascii=False) + "\n"
        except RuntimeError as exc:
            yield json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False) + "\n"

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
