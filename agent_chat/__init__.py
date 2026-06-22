"""agent_chat — a domain-agnostic, drop-in streaming chat backend.

Everything a front end (e.g. journal_chat_app) talks to: HTTP, sessions, SSE,
command parsing — with exactly one seam to your agent, a ``TurnRunner`` that
yields Frames. The package imports no graph, store, or LLM call site; node-
level routing stays inside your graph (the orchestrator pattern). The backend
only relays the *boundary-crossing* actions (token, ask_human, tool_call,
state_update, terminate) to the client.

Drop-in quick start::

    from agent_chat import create_chat_app, TurnRequest, Token, AskHuman

    async def my_runner(req: TurnRequest):
        async for frame in drive_my_graph(req):   # yields Token/Action frames
            yield frame

    app = create_chat_app(runner=my_runner)       # a FastAPI app, ready to serve

Test in isolation with no agent::

    async def fake(req):
        yield Token(text="hi")
        yield AskHuman(prompt="what next?")
    app = create_chat_app(runner=fake)            # hit /chat and assert the SSE
"""
from agent_chat.actions import (
    Action,
    AskHuman,
    Done,
    Error,
    Frame,
    FrameKind,
    InvokeSubgraph,
    RunnerFrame,
    StateUpdate,
    Terminate,
    Token,
    ToolCall,
)
from agent_chat.app import create_chat_app
from agent_chat.commands import Command, CommandParser, ParsedInput
from agent_chat.console import get_console_input, render_frames_to_terminal
from agent_chat.llm import (
    LLMClient,
    LLMRegistry,
    Provider,
    build_llm_registry,
    create_llm_client,
)
from agent_chat.models import HealthResponse, SessionEndResponse, SessionResponse
from agent_chat.protocols import ModelSpec, TurnRequest, TurnRunner
from agent_chat.transport import SSE_HEADERS, ChatBody, chat_router, stream_turn

__all__ = [
    # protocol
    "Frame", "FrameKind", "Token", "Action", "RunnerFrame",
    "ToolCall", "InvokeSubgraph", "AskHuman", "StateUpdate", "Terminate",
    "Done", "Error",
    # contracts
    "TurnRequest", "TurnRunner", "ModelSpec",
    # app (drop-in)
    "create_chat_app",
    # transport
    "stream_turn", "chat_router", "ChatBody", "SSE_HEADERS",
    # http models
    "SessionResponse", "SessionEndResponse", "HealthResponse",
    # commands
    "CommandParser", "Command", "ParsedInput",
    # console
    "render_frames_to_terminal", "get_console_input",
    # llm
    "LLMClient", "LLMRegistry", "Provider",
    "create_llm_client", "build_llm_registry",
]
