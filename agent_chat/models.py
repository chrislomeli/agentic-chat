"""models.py — HTTP request/response models for the chat backend.

These cross the wire and are intentionally tiny. The streaming side uses the
Action protocol (see actions.py); these cover the non-streaming endpoints.
"""
from __future__ import annotations

from pydantic import BaseModel


class SessionResponse(BaseModel):
    session_id: str


class SessionEndResponse(BaseModel):
    status: str
    session_id: str


class HealthResponse(BaseModel):
    status: str = "ok"
