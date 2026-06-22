"""transport.py — turn a stream of Frames into an SSE response.

This is the generic replacement for the journal project's ``api/streaming.py``
and the SSE endpoint in ``api/main.py``. It knows nothing about LangGraph or
any domain: it drives a ``TurnRunner`` and guarantees a clean terminal frame.

Two layers:

  stream_turn(runner, request) -> AsyncIterator[str]
      Pure async generator of SSE wire strings. Use this anywhere.

  chat_router(runner, ...) -> APIRouter
      Optional FastAPI sugar: a ready-made POST /chat/{session_id} endpoint
      (and a /sessions allocator) wired to ``runner``. Import-guarded so the
      package doesn't hard-depend on FastAPI.
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from pydantic import BaseModel

from agent_chat.actions import Done, Error
from agent_chat.protocols import TurnRequest, TurnRunner

logger = logging.getLogger(__name__)

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",  # stop nginx buffering the SSE stream
}


class ChatBody(BaseModel):
    """Request body for POST /chat/{session_id}. Module-level so FastAPI can
    resolve its type hints (a function-local model is treated as a query param)."""

    message: str
    metadata: dict = {}


async def stream_turn(
    runner: TurnRunner,
    request: TurnRequest,
) -> AsyncIterator[str]:
    """Drive ``runner`` for one turn, yielding SSE strings.

    Every frame the runner yields is encoded and forwarded. The stream always
    ends with exactly one terminal frame: ``done`` on success, ``error`` if
    the runner raised. Terminal frames are owned by the transport so runners
    never have to remember to emit them.
    """
    try:
        async for frame in runner(request):
            yield frame.sse()
        yield Done().sse()
    except Exception as exc:  # noqa: BLE001 — body is open; surface, don't raise
        logger.exception("turn failed", extra={"session_id": request.session_id})
        yield Error(message=str(exc)).sse()


def chat_router(runner: TurnRunner, *, with_sessions: bool = True):
    """Build a FastAPI router exposing the chat transport over ``runner``.

    Returns an ``APIRouter`` with:
        POST /sessions            (if with_sessions) — allocate a session_id
        POST /chat/{session_id}   — one streamed turn

    FastAPI is imported lazily so the core package has no web dependency.
    """
    from uuid import uuid4

    from fastapi import APIRouter
    from fastapi.responses import StreamingResponse

    router = APIRouter()

    if with_sessions:

        @router.post("/sessions", status_code=201)
        async def create_session() -> dict:
            return {"session_id": str(uuid4())}

    @router.post("/chat/{session_id}")
    async def chat(session_id: str, body: ChatBody) -> StreamingResponse:
        request = TurnRequest(
            session_id=session_id,
            message=body.message,
            metadata=body.metadata,
        )
        return StreamingResponse(
            stream_turn(runner, request),
            media_type="text/event-stream",
            headers=SSE_HEADERS,
        )

    return router
