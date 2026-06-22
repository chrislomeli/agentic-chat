# agent_chat

A domain-agnostic, **drop-in streaming chat backend** for graph agents.

It owns everything a chat front end talks to — HTTP, sessions, SSE, command
parsing — and connects to *your* agent through exactly one seam: a
**`TurnRunner`** that yields **Frames**. It imports no graph, store, or LLM
call site.

## The boundary

Node-level routing stays **inside your graph** (the orchestrator/router-node
pattern). The backend only relays the *boundary-crossing* actions to the
client:

| Frame | Meaning |
|---|---|
| `Token` | one chunk of streamed model text |
| `ToolCall` | the agent called a tool (notification) |
| `InvokeSubgraph` | the agent delegated to a subgraph (notification) |
| `AskHuman` | needs input — turn ends; the client answers in the next request (no `interrupt()`) |
| `StateUpdate` | durable state changed (notification) |
| `Terminate` | session is over |
| `Done` / `Error` | terminal frames, emitted by the transport |

On the wire each is an SSE event: `event: <kind>\ndata: <json>\n\n`.

## Drop it in

```python
from agent_chat import create_chat_app, TurnRequest, Token, AskHuman

async def my_runner(req: TurnRequest):
    # drive your graph; translate its events into frames
    async for frame in drive_my_graph(req):
        yield frame

app = create_chat_app(
    runner=my_runner,
    lifespan=my_lifespan,             # optional: build deps once at startup
    on_session_start=mark_bootstrap,  # optional: async (session_id) -> None
    on_session_end=run_eos_pipeline,  # optional: async (session_id) -> dict | None
)
# uvicorn my_module:app
```

Endpoints: `POST /sessions`, `POST /chat/{session_id}` (SSE), `DELETE
/sessions/{session_id}`, `GET /health`.

## Quick start

`examples/hello_world.py` is a complete, copy-paste starting point: a fake
runner that emits one of every Frame kind, wired into a real app. Run it three
ways without writing any agent:

```bash
# 1. as an HTTP server (what a front end talks to)
uv run uvicorn examples.hello_world:app --reload
curl -N -X POST localhost:8000/chat/demo \
     -H 'content-type: application/json' -d '{"message": "hi"}'

# 2. as a terminal chat (same runner, no web layer)
uv run python -m examples.hello_world console

# 3. as a self-check (prints each frame's SSE wire form)
uv run python -m examples.hello_world dump
```

To make it real, replace the example's `hello_runner` body with a generator
that drives your agent and translates its events into Frames.

## Test in isolation (no agent)

The runner is the only thing your project supplies, so you can test the whole
backend with a fake one:

```python
async def fake(req):
    yield Token(text="hi")
    yield AskHuman(prompt="what next?")

app = create_chat_app(runner=fake)   # hit /chat and assert the SSE stream
```

See `tests/test_isolation.py` for the full lifecycle exercised without
LangGraph, Postgres, or any domain code.

## What's in the box

- `actions.py` — the Frame/Action protocol + SSE encoding
- `transport.py` — `stream_turn`, `chat_router`, terminal-frame guarantees
- `app.py` — `create_chat_app` factory (the drop-in entry point)
- `protocols.py` — `TurnRequest`, `TurnRunner`, `ModelSpec` contracts
- `commands.py` — configurable slash-command parsing (`CommandParser`)
- `console.py` — render a Frame stream to a terminal (CLI runner)
- `llm.py` — provider-agnostic `LLMClient` + `LLMRegistry`

## Reference adapter

`journal_agent/api/adapter.py` is a working `TurnRunner` over a real LangGraph
graph — copy it as the template for a new project's runner.
