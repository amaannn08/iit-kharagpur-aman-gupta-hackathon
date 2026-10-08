"""Server-Sent Events streaming route conforming to PRD Section 11.3 & 12."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from sentinel.api.events import broadcaster

router = APIRouter(prefix="/events", tags=["Event Stream"])


@router.get("/stream")
async def stream_live_events() -> StreamingResponse:
    """Stream live risk signals, replay progress, and stress events via Server-Sent Events (SSE)."""
    return StreamingResponse(
        broadcaster.stream_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
