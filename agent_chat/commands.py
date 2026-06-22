"""commands.py — generic slash-command parsing for chat input.

Domain-free. A host project configures which commands exist and what prompt
each expands to; this module just recognizes ``/word [args]`` and produces a
``ParsedInput``. The journal's ``/reflect``, ``/recall``, ``/save`` live in
the host as ``Command`` entries — none of that vocabulary is baked in here.

Typical use::

    parser = CommandParser(commands=[
        Command("reflect", "Share the patterns you've noticed."),
        Command("recall", lambda a: f"Recall what I wrote about: {a}" if a
                                    else "Recall my recent entries."),
    ])
    parsed = parser.parse(user_text)
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ParsedInput:
    """Structured result of parsing one line of user input.

    Attributes:
        is_quit: the user asked to end the session.
        command: the recognized command name (without the leading slash), or
            None for a plain message.
        args: raw text after the command word.
        message: the text to hand to the agent as the turn's content. For a
            command this is the expanded prompt; for plain text it's the text.
            Empty string means "no message this turn".
    """

    is_quit: bool = False
    command: str | None = None
    args: str = ""
    message: str = ""


# A command's prompt is either a fixed string or a function of its args.
PromptSpec = str | Callable[[str], str]


@dataclass(frozen=True)
class Command:
    """One recognized slash command.

    name:   the word after the slash (e.g. "reflect" for "/reflect").
    prompt: what the command expands into as the turn message. A ``str`` is
            used verbatim; a callable receives the args string.
    emit_message: if False, the command carries no turn message (e.g. a
            "/save" that captures inline without prompting the agent).
    """

    name: str
    prompt: PromptSpec = ""
    emit_message: bool = True

    def expand(self, args: str) -> str:
        if not self.emit_message:
            return ""
        return self.prompt(args) if callable(self.prompt) else self.prompt


class CommandParser:
    """Parses raw input into a ParsedInput using a configured command set."""

    def __init__(
        self,
        commands: list[Command] | None = None,
        *,
        quit_aliases: tuple[str, ...] = ("/quit", "/exit"),
    ):
        self._commands = {c.name: c for c in (commands or [])}
        self._quit_aliases = quit_aliases

    def parse(self, text: str) -> ParsedInput:
        stripped = text.strip()

        if stripped in self._quit_aliases:
            return ParsedInput(is_quit=True)

        if stripped.startswith("/"):
            parts = stripped[1:].split(maxsplit=1)
            name = parts[0] if parts else ""
            args = parts[1].strip() if len(parts) > 1 else ""
            cmd = self._commands.get(name)
            if cmd is not None:
                return ParsedInput(command=name, args=args, message=cmd.expand(args))
            # Unknown slash command — treat the whole thing as a plain message.

        return ParsedInput(message=stripped)
