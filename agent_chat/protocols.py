"""protocols.py — the contracts a host project implements.

The generic package never imports a graph, a store, or a settings module.
Instead it depends on these small structural protocols. A host project
(e.g. journal_agent) provides concrete implementations.

Two contracts matter:

  TurnRequest / TurnRunner — how a single conversation turn is run. The host
      adapter inspects its own graph and yields ``Frame`` objects. This is the
      adapter-based translation seam: the graph stays as-is, the adapter
      maps its events/state onto the Action protocol.

  ModelSpec — the minimum a config object must expose for the LLM layer to
      build a client. Host config types (LLMModel, Settings) can satisfy this
      without importing anything from this package.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

from agent_chat.actions import RunnerFrame


class TurnRequest(BaseModel):
    """One turn of conversation, framework-agnostic.

    ``metadata`` carries anything the host adapter needs that isn't part of
    the generic contract (parsed command, command args, bootstrap flags, …).
    """

    session_id: str
    message: str
    metadata: dict[str, Any] = {}


@runtime_checkable
class TurnRunner(Protocol):
    """Runs one turn and yields frames as the agent works.

    The runner must NOT yield Done/Error — the transport appends those and
    guarantees exactly one terminal frame even if the runner raises.
    """

    def __call__(self, request: TurnRequest) -> AsyncIterator[RunnerFrame]: ...


@runtime_checkable
class ModelSpec(Protocol):
    """Minimal shape the LLM layer needs to build a client. Provider is a
    plain string ("openai" | "anthropic" | "ollama")."""

    provider: str
    model: str
    api_key: Any | None
    base_url: str | None
