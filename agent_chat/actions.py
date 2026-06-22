"""actions.py — the Action protocol that flows over the chat transport.

This is the heart of the generic package. A turn produces a stream of
``Frame`` objects; the transport encodes each as an SSE event. Frames are
either *text* (streamed model tokens) or *actions* the agent took.

The five actions mirror what an agent does inside a turn:

    call_tool      — the agent invoked a tool
    invoke_subgraph— the agent delegated to a subgraph
    ask_human      — the agent needs input; the turn ends here and the
                     client answers in the next request (no interrupt())
    update_state   — a notification that durable state changed
    terminate      — the session is over

Nothing here knows about LangGraph, FastAPI, or any domain. A host project
produces these frames from a ``turn_runner`` (see ``protocols.TurnRunner``).
"""
from __future__ import annotations

import json
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class FrameKind(StrEnum):
    """The ``event:`` name carried on the SSE wire."""

    TOKEN = "token"                 # one chunk of streamed model text
    TOOL_CALL = "tool_call"         # agent called a tool
    INVOKE_SUBGRAPH = "subgraph"    # agent delegated to a subgraph
    ASK_HUMAN = "ask_human"         # agent needs input; turn ends
    STATE_UPDATE = "state_update"   # durable state changed (notification)
    TERMINATE = "terminate"         # session is over
    DONE = "done"                   # turn complete (terminal, always last)
    ERROR = "error"                 # something failed (terminal)


class Frame(BaseModel):
    """Base class for everything that crosses the wire.

    The ``kind`` field is the discriminator and becomes the SSE ``event:``
    name. Subclasses add their own payload fields, which are serialized into
    the SSE ``data:`` JSON.
    """

    kind: FrameKind

    def sse(self) -> str:
        """Encode this frame as a single SSE event string."""
        data = self.model_dump(mode="json", exclude={"kind"})
        return f"event: {self.kind.value}\ndata: {json.dumps(data)}\n\n"


# ── Text ────────────────────────────────────────────────────────────────────

class Token(Frame):
    """One chunk of streamed model output."""

    kind: Literal[FrameKind.TOKEN] = FrameKind.TOKEN
    text: str


# ── Actions ───────────────────────────────────────────────────────────────

class ToolCall(Frame):
    """The agent invoked a tool. ``result`` is optional — emit one frame on
    call and (optionally) another once the result is known, or a single frame
    carrying both."""

    kind: Literal[FrameKind.TOOL_CALL] = FrameKind.TOOL_CALL
    name: str
    args: dict[str, Any] = Field(default_factory=dict)
    result: Any | None = None


class InvokeSubgraph(Frame):
    """The agent delegated this turn (or part of it) to a named subgraph."""

    kind: Literal[FrameKind.INVOKE_SUBGRAPH] = FrameKind.INVOKE_SUBGRAPH
    name: str
    status: Literal["started", "finished"] = "started"
    detail: str | None = None


class AskHuman(Frame):
    """The agent needs input. This ends the turn — under per-request
    invocation there is no interrupt()/resume; the client answers by sending
    a normal message in the next request. ``field`` optionally names what is
    being asked for so a client can render a structured prompt."""

    kind: Literal[FrameKind.ASK_HUMAN] = FrameKind.ASK_HUMAN
    prompt: str
    field: str | None = None


class StateUpdate(Frame):
    """Notification that durable state changed during the turn. Observational,
    not a command — the state has already been written by the time the client
    sees this (e.g. a /save confirmation)."""

    kind: Literal[FrameKind.STATE_UPDATE] = FrameKind.STATE_UPDATE
    message: str
    patch: dict[str, Any] | None = None


class Terminate(Frame):
    """The session is over. The client should stop sending turns and may
    trigger any end-of-session cleanup on its side."""

    kind: Literal[FrameKind.TERMINATE] = FrameKind.TERMINATE
    reason: str | None = None


# ── Terminal frames (emitted by the transport, not the runner) ──────────────

class Done(Frame):
    kind: Literal[FrameKind.DONE] = FrameKind.DONE


class Error(Frame):
    kind: Literal[FrameKind.ERROR] = FrameKind.ERROR
    message: str


# Convenience: the union a turn_runner is allowed to yield. Done/Error are
# appended by the transport, so a runner should not produce them itself.
Action = ToolCall | InvokeSubgraph | AskHuman | StateUpdate | Terminate
RunnerFrame = Token | Action
