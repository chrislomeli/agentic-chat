"""app.py — the drop-in chat backend, as a FastAPI app factory.

``create_chat_app`` returns a fully wired FastAPI app whose only connection to
your agent is a ``TurnRunner`` (one async generator that yields Frames). Drop
it into any project: bring a runner, optionally a lifespan and session hooks,
and you have a streaming chat API the journal_chat_app front end can talk to.

    POST   /sessions              — allocate a session_id (runs on_session_start)
    POST   /chat/{session_id}     — one turn, streamed as SSE Action frames
    DELETE /sessions/{session_id} — end a session (runs on_session_end)
    GET    /health                — liveness

The backend imports no graph, store, or LLM call site. Everything domain- or
graph-specific is supplied by the caller:

    app = create_chat_app(
        runner=my_runner,                 # required: TurnRequest -> AsyncIterator[Frame]
        lifespan=my_lifespan,             # optional: build deps once at startup
        on_session_start=mark_bootstrap,  # optional: async (session_id) -> None
        on_session_end=run_eos_pipeline,  # optional: async (session_id) -> dict | None
    )

This makes the backend testable in isolation: pass a fake runner that yields
canned frames and exercise the whole HTTP/SSE surface with no agent at all.
"""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from agent_chat.models import HealthResponse, SessionEndResponse, SessionResponse
from agent_chat.protocols import TurnRunner
from agent_chat.transport import chat_router

logger = logging.getLogger(__name__)

# Hook signatures. Both are optional and async.
SessionStartHook = Callable[[str], Awaitable[None]]
SessionEndHook = Callable[[str], Awaitable[dict | None]]
Lifespan = Callable[[FastAPI], AbstractAsyncContextManager[None]]


def create_chat_app(
    *,
    runner: TurnRunner,
    title: str = "Chat Backend",
    version: str = "0.1.0",
    lifespan: Lifespan | None = None,
    on_session_start: SessionStartHook | None = None,
    on_session_end: SessionEndHook | None = None,
) -> FastAPI:
    """Build a drop-in streaming chat backend around ``runner``."""
    app = FastAPI(title=title, version=version, lifespan=lifespan)

    # /chat/{session_id} comes from the generic transport.
    app.include_router(chat_router(runner, with_sessions=False))

    @app.post("/sessions", response_model=SessionResponse, status_code=201)
    async def create_session() -> SessionResponse:
        session_id = str(uuid4())
        if on_session_start is not None:
            await on_session_start(session_id)
        logger.info("session created", extra={"session_id": session_id})
        return SessionResponse(session_id=session_id)

    @app.delete(
        "/sessions/{session_id}",
        response_model=SessionEndResponse,
        status_code=202,
    )
    async def end_session(session_id: str) -> SessionEndResponse:
        logger.info("session end", extra={"session_id": session_id})
        if on_session_end is not None:
            try:
                await on_session_end(session_id)
            except Exception as exc:  # noqa: BLE001 — surface as 500
                logger.exception("session end hook failed", extra={"session_id": session_id})
                raise HTTPException(status_code=500, detail=str(exc)) from exc
        return SessionEndResponse(status="ended", session_id=session_id)

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse()

    return app
