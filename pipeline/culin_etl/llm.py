"""Thin OpenAI Chat Completions proxy. Key stays server-side (OPENAI_API_KEY)."""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx
from fastapi import HTTPException

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4o-mini"


def openai_configured() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


def default_model() -> str:
    return os.environ.get("OPENAI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


async def chat_completions(
    *,
    messages: list[dict[str, Any]],
    tools: Optional[list[dict[str, Any]]] = None,
    tool_choice: Optional[Any] = None,
    model: Optional[str] = None,
    temperature: float = 0.3,
    response_format: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is not set on the API server",
        )

    body: dict[str, Any] = {
        "model": (model or default_model()).strip() or default_model(),
        "messages": messages,
        "temperature": temperature,
    }
    if tools:
        body["tools"] = tools
    if tool_choice is not None:
        body["tool_choice"] = tool_choice
    if response_format is not None:
        body["response_format"] = response_format

    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.post(
            OPENAI_URL,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json=body,
        )

    if res.status_code >= 400:
        detail = res.text
        try:
            detail = res.json()
        except Exception:
            pass
        raise HTTPException(status_code=502, detail={"openai_status": res.status_code, "body": detail})

    return res.json()
