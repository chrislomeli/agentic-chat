"""hello_world.py — the smallest possible agent_chat backend.

This is the copy-paste starting point for a new project. It shows the *entire*
reuse contract: write one async generator (a ``TurnRunner``) that yields Frames,
hand it to ``create_chat_app``, and you have a streaming chat API.

There is no graph, no LLM, no database here — just a fake runner that emits one
of each Frame kind so you can see the whole Action protocol end to end. To make
it real, replace ``hello_runner`` with a generator that drives your agent and
translates its events into Frames (see journal_agent/api/adapter.py for a real one).

Run it three ways
-----------------
1. As an HTTP server (what a front end talks to)::

       uv run uvicorn examples.hello_world:app --reload
       # then, in another shell:
       curl -N -X POST localhost:8000/chat/demo \
            -H 'content-type: application/json' \
            -d '{"message": "hi"}'

   ``-N`` disables curl buffering so you see the SSE events stream in live.

2. As a terminal chat (same runner, no web layer)::

       uv run python -m examples.hello_world console

3. As a self-check (drives the runner and prints each frame's SSE wire form)::

       uv run python -m examples.hello_world dump
"""
from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncIterator

from agent_chat import (
    AskHuman,
    StateUpdate,
    Terminate,
    Token,
    ToolCall,
    TurnRequest,
    create_chat_app,
)


# ─────────────────────────────────────────────────────────────────────────────
# The one thing you write per project: a TurnRunner.
#
# It's an async generator: TurnRequest -> AsyncIterator[Frame]. It runs ONE turn
# and yields frames as work happens. The transport streams each yield to the
# client immediately and appends the terminal Done/Error frame for you — so this
# function never yields Done/Error and never has to clean up the stream.
# ─────────────────────────────────────────────────────────────────────────────
async def hello_runner(request: TurnRequest) -> AsyncIterator:
    """A fake agent that exercises every Frame kind for one turn.

    Replace the body with your real agent: iterate your graph's event stream
    (e.g. ``graph.astream_events(...)``) and translate each event into a Frame.
    Everything below is just a scripted demonstration.
    """
    # /quit ends the session. The client watches for `terminate` to know the
    # conversation is over (and to trigger any end-of-session cleanup).
    if request.message.strip().lower() == "/quit":
        yield Terminate(reason="Session ended. Goodbye.")
        return

    # STEP 2 (your decision/routing) would happen here. We just pretend the
    # agent decided to call a tool, then answer.
    yield ToolCall(name="echo", args={"input": request.message}, result=request.message)

    # STEP 3/4: stream the answer back token by token, exactly like real model
    # output. The front end appends each chunk to the assistant bubble.
    for word in f"You said: {request.message}".split():
        yield Token(text=word + " ")
        await asyncio.sleep(0.05)  # simulate model latency so streaming is visible

    # If the agent needs more input, it says so and the turn ENDS here. There is
    # no interrupt()/resume — the user answers in the next /chat request.
    if "?" not in request.message:
        yield AskHuman(prompt="Anything else? (end your message with ? to stop)")
        return

    # A notification that durable state changed (e.g. "saved"). Observational —
    # the write already happened; this just tells the UI about it.
    yield StateUpdate(message="Saved this exchange.")


# ─────────────────────────────────────────────────────────────────────────────
# Wire the runner into a full FastAPI app. This single call gives you:
#   POST /sessions, POST /chat/{id}, DELETE /sessions/{id}, GET /health.
# ─────────────────────────────────────────────────────────────────────────────
app = create_chat_app(runner=hello_runner, title="Hello Agent")


# ─────────────────────────────────────────────────────────────────────────────
# Optional local drivers — the same runner, without the web layer.
# ─────────────────────────────────────────────────────────────────────────────
async def _console() -> None:
    """Chat in the terminal: same runner, rendered to stdout instead of SSE."""
    from agent_chat import get_console_input, render_frames_to_terminal

    print("Hello agent (type /quit to end)\n")
    while True:
        message = get_console_input()
        request = TurnRequest(session_id="console", message=message)
        await render_frames_to_terminal(hello_runner(request))
        if message.strip().lower() == "/quit":
            break


async def _dump() -> None:
    """Drive the runner once and print each frame's exact SSE wire form."""
    request = TurnRequest(session_id="dump", message="hello world?")
    async for frame in hello_runner(request):
        print(repr(frame.sse()))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "dump"
    if mode == "console":
        asyncio.run(_console())
    elif mode == "dump":
        asyncio.run(_dump())
    else:
        print("usage: python -m examples.hello_world [console|dump]")
        print("   or: uvicorn examples.hello_world:app --reload   (HTTP server)")
