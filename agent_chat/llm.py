"""llm.py — provider-agnostic LLM client + named registry.

Lifted from journal_agent.comms.{llm_client,llm_registry} with the journal
config types removed. The client wraps a LangChain chat model; the registry
is a role-name → client catalog built once at startup.

Construction is driven by a ``ModelSpec`` (see protocols.ModelSpec) so host
config types plug in without importing this package.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from langchain_core.messages import AIMessage
from pydantic import SecretStr

from agent_chat.protocols import ModelSpec

logger = logging.getLogger(__name__)


class Provider(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


# ── Client ──────────────────────────────────────────────────────────────────

class LLMClient:
    """Thin wrapper over a LangChain chat model. Forwards sync/async/stream
    calls and structured-output helpers to the underlying model."""

    def __init__(self, model: str, client: Any):
        self._model = model
        self._client = client

    @property
    def model(self) -> str:
        return self._model

    def chat(self, messages) -> AIMessage:
        return self._client.invoke(messages)

    async def achat(self, messages) -> AIMessage:
        return await self._client.ainvoke(messages)

    def astream(self, messages):
        """Async-iterate response chunks; drives ``on_chat_model_stream``
        events when called inside a LangGraph node."""
        return self._client.astream(messages)

    def get_client(self):
        return self._client

    def structured(self, schema: type):
        return self._client.with_structured_output(schema, method="json_schema")

    def astructured(self, schema: type):
        return self._client.with_structured_output(schema, method="json_schema")


def create_llm_client(
    provider: str | Provider,
    api_key: SecretStr | str | None,
    model: str,
    base_url: str | None = None,
) -> LLMClient:
    """Build an LLMClient for the given provider. For ollama, ``api_key`` is
    ignored and ``base_url`` is used."""
    provider = Provider(provider)

    if provider == Provider.OPENAI:
        from langchain_openai import ChatOpenAI

        chat = ChatOpenAI(model=model, temperature=0, api_key=api_key)
    elif provider == Provider.ANTHROPIC:
        from langchain_anthropic import ChatAnthropic

        key = api_key.get_secret_value() if isinstance(api_key, SecretStr) else api_key
        chat = ChatAnthropic(model_name=model, api_key=key, temperature=0)
    elif provider == Provider.OLLAMA:
        from langchain_ollama import ChatOllama

        chat = ChatOllama(
            model=model,
            temperature=0,
            base_url=base_url or "http://localhost:11434",
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")

    return LLMClient(model=model, client=chat)


# ── Registry ──────────────────────────────────────────────────────────────

@dataclass
class LLMRegistry:
    """Immutable role-name → LLMClient catalog with a 'conversation' fallback."""

    _clients: dict[str, LLMClient] = field(default_factory=dict)

    def get(self, role: str) -> LLMClient:
        client = self._clients.get(role)
        if client is not None:
            return client
        fallback = self._clients.get("conversation")
        if fallback is not None:
            logger.warning("No LLM for role %r — falling back to 'conversation'", role)
            return fallback
        raise KeyError(f"No LLM for role {role!r} and no 'conversation' fallback.")

    @property
    def roles(self) -> list[str]:
        return sorted(self._clients)


def build_llm_registry(specs: dict[str, ModelSpec]) -> LLMRegistry:
    """Build a registry from a role-name → ModelSpec mapping. The host is
    responsible for resolving labels/keys into ModelSpecs before calling
    this (keeps config resolution out of the generic package)."""
    clients: dict[str, LLMClient] = {}
    for role, spec in specs.items():
        if spec is None:
            logger.warning("Skipping role %r — no model spec", role)
            continue
        clients[role] = create_llm_client(
            provider=spec.provider,
            api_key=spec.api_key,
            model=spec.model,
            base_url=spec.base_url,
        )
        logger.info("Registered LLM for role %r → %s (%s)", role, spec.model, spec.provider)
    return LLMRegistry(_clients=clients)
