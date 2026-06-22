"""console.py — render a Frame stream to a terminal.

A CLI counterpart to the SSE transport: same runner, same frames, different
sink. Useful for driving an agent from a shell and for eyeballing a runner
without the web layer. Tokens stream inline; actions print as labeled lines.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from agent_chat.actions import (
    AskHuman,
    FrameKind,
    InvokeSubgraph,
    StateUpdate,
    Terminate,
    Token,
    ToolCall,
)

_CYAN = "\033[36m"
_YELLOW = "\033[33m"
_DIM = "\033[2m"
_RESET = "\033[0m"


def get_console_input(prompt: str = "You (blank line to send):") -> str:
    """Read a multi-line message from stdin; blank line submits."""
    while True:
        print(prompt)
        lines: list[str] = []
        while True:
            line = input()
            if line == "":
                break
            lines.append(line)
        text = "\n".join(lines).strip()
        if text:
            return text


async def render_frames_to_terminal(frames: AsyncIterator) -> None:
    """Consume a runner's Frame stream and print it.

    Tokens are concatenated under an ``AI:`` prefix; each action prints on its
    own dim line so it's distinguishable from model text.
    """
    in_tokens = False
    try:
        async for frame in frames:
            if isinstance(frame, Token):
                if not in_tokens:
                    print(f"{_CYAN}AI: ", end="", flush=True)
                    in_tokens = True
                print(frame.text, end="", flush=True)
                continue

            if in_tokens:
                print(_RESET)
                in_tokens = False

            if isinstance(frame, StateUpdate):
                print(f"{_YELLOW}System: {frame.message}{_RESET}")
            elif isinstance(frame, AskHuman):
                print(f"{_YELLOW}? {frame.prompt}{_RESET}")
            elif isinstance(frame, ToolCall):
                print(f"{_DIM}[tool] {frame.name}({frame.args}){_RESET}")
            elif isinstance(frame, InvokeSubgraph):
                print(f"{_DIM}[subgraph] {frame.name} {frame.status}{_RESET}")
            elif isinstance(frame, Terminate):
                print(f"{_YELLOW}— session over{(': ' + frame.reason) if frame.reason else ''}{_RESET}")
            elif getattr(frame, "kind", None) == FrameKind.ERROR:
                print(f"{_YELLOW}[error] {getattr(frame, 'message', '')}{_RESET}")
    finally:
        if in_tokens:
            print(_RESET)
