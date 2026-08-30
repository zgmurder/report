import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.schemas.pi_agent import PiAgentRequest
from app.services.pi_agent_service import stream_pi

router = APIRouter()


@router.post("/stream", summary="流式调用本机 Pi Agent")
async def stream(payload: PiAgentRequest) -> StreamingResponse:
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
