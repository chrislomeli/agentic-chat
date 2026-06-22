"""Backend-in-isolation tests.

The whole point of the package: exercise the full HTTP/SSE/session surface
with a *fake* runner — no LangGraph, no Postgres, no domain code. If these
pass, the backend is droppable into any project; only the runner changes.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from agent_chat import (
    AskHuman,
    Command,
    CommandParser,
    StateUpdate,
    Terminate,
    Token,
    TurnRequest,
    create_chat_app,
)


def _parse_sse(text: str) -> list[dict]:
    """Parse an SSE body into a list of {event, data-line} dicts."""
    import json

    events = []
    current = None
    for line in text.splitlines():
        if line.startswith("event: "):
            current = {"event": line[7:].strip(), "data": None}
        elif line.startswith("data: ") and current is not None:
            current["data"] = json.loads(line[6:].strip())
        elif line == "" and current is not None:
            events.append(current)
            current = None
    return events


async def _fake_runner(request: TurnRequest):
    """A graph-free runner that branches on the message to emit each frame."""
    msg = request.message
    if msg == "/quit":
        yield Terminate(reason="bye")
        return
    if msg == "ask":
        yield Token(text="thinking… ")
        yield AskHuman(prompt="What date?", field="date")
        return
    if msg == "save":
        yield Token(text="done ")
        yield StateUpdate(message="Saved 3 items.")
        return
    yield Token(text="Hello ")
    yield Token(text="world")


def _client(**kwargs) -> AsyncClient:
    app = create_chat_app(runner=_fake_runner, **kwargs)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ── transport / lifecycle ───────────────────────────────────────────────────

async def test_health():
    async with _client() as c:
        r = await c.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


async def test_create_session_returns_uuid():
    async with _client() as c:
        r = await c.post("/sessions")
        assert r.status_code == 201
        assert len(r.json()["session_id"]) == 36


async def test_chat_streams_tokens_then_done():
    async with _client() as c:
        r = await c.post("/chat/s1", json={"message": "hi"})
        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]
        events = _parse_sse(r.text)
        assert [e["event"] for e in events] == ["token", "token", "done"]
        assert "".join(e["data"]["text"] for e in events if e["event"] == "token") == "Hello world"


async def test_ask_human_frame():
    async with _client() as c:
        r = await c.post("/chat/s1", json={"message": "ask"})
        events = _parse_sse(r.text)
        assert [e["event"] for e in events] == ["token", "ask_human", "done"]
        ask = next(e for e in events if e["event"] == "ask_human")
        assert ask["data"] == {"prompt": "What date?", "field": "date"}


async def test_state_update_frame():
    async with _client() as c:
        r = await c.post("/chat/s1", json={"message": "save"})
        kinds = [e["event"] for e in _parse_sse(r.text)]
        assert kinds == ["token", "state_update", "done"]


async def test_quit_terminates():
    async with _client() as c:
        r = await c.post("/chat/s1", json={"message": "/quit"})
        events = _parse_sse(r.text)
        assert [e["event"] for e in events] == ["terminate", "done"]


async def test_runner_exception_becomes_error_frame():
    async def boom(request: TurnRequest):
        yield Token(text="x")
        raise RuntimeError("kaboom")

    app = create_chat_app(runner=boom)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        events = _parse_sse((await c.post("/chat/s1", json={"message": "hi"})).text)
        assert [e["event"] for e in events] == ["token", "error"]
        assert "kaboom" in events[-1]["data"]["message"]


# ── session hooks ────────────────────────────────────────────────────────────

async def test_session_hooks_fire():
    started, ended = [], []

    async def on_start(sid):
        started.append(sid)

    async def on_end(sid):
        ended.append(sid)
        return {"saved": True}

    async with _client(on_session_start=on_start, on_session_end=on_end) as c:
        sid = (await c.post("/sessions")).json()["session_id"]
        assert started == [sid]
        r = await c.delete(f"/sessions/{sid}")
        assert r.status_code == 202
        assert ended == [sid]


# ── command parser (no HTTP) ─────────────────────────────────────────────────

def test_command_parser():
    parser = CommandParser(commands=[
        Command("reflect", "Show me patterns."),
        Command("recall", lambda a: f"recall: {a}" if a else "recall recent"),
    ])
    assert parser.parse("/quit").is_quit
    assert parser.parse("/reflect").message == "Show me patterns."
    assert parser.parse("/recall trips").message == "recall: trips"
    assert parser.parse("/recall").message == "recall recent"
    # unknown command falls through to a plain message
    assert parser.parse("/bogus x").command is None
    assert parser.parse("just talking").message == "just talking"
