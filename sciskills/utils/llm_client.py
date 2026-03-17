"""
Thin LLM client wrapper supporting OpenAI-compatible APIs.

Reads configuration from environment variables:
    LLM_API_KEY   - API key
    LLM_BASE_URL  - Base URL (default: https://api.openai.com/v1)
    LLM_MODEL     - Model name (default: gpt-4o)

Can also be configured programmatically via LLMClient().
"""
from __future__ import annotations

import json
import os
from typing import Any

import httpx


_DEFAULT_BASE_URL = "https://api.openai.com/v1"
_DEFAULT_MODEL = "gpt-4o"


class LLMClient:
    """
    Minimal OpenAI-compatible chat completions client.
    Supports both sync and async usage.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
    ):
        self.api_key = api_key or os.environ.get("LLM_API_KEY", "")
        self.base_url = (
            base_url or os.environ.get("LLM_BASE_URL", _DEFAULT_BASE_URL)
        ).rstrip("/")
        self.model = model or os.environ.get("LLM_MODEL", _DEFAULT_MODEL)
        self.timeout = timeout

        if not self.api_key:
            raise ValueError(
                "LLM API key is required. Set LLM_API_KEY env var or pass api_key="
            )

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------ #
    # Sync                                                                 #
    # ------------------------------------------------------------------ #

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.0,
        max_tokens: int = 4096,
        response_format: dict | None = None,
        **kwargs: Any,
    ) -> str:
        """Send a chat completion request and return the assistant message content."""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format
        payload.update(kwargs)

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        return data["choices"][0]["message"]["content"]

    def chat_json(
        self,
        messages: list[dict],
        temperature: float = 0.0,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> dict:
        """
        Call chat() and attempt to parse the response as JSON.
        Falls back to returning {"raw": content} if parsing fails.
        """
        content = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        # Strip markdown code fences if present
        cleaned = content.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Remove first and last fence lines
            cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {"raw": content}

    # ------------------------------------------------------------------ #
    # Async                                                                #
    # ------------------------------------------------------------------ #

    async def achat(
        self,
        messages: list[dict],
        temperature: float = 0.0,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> str:
        """Async version of chat()."""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        payload.update(kwargs)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        return data["choices"][0]["message"]["content"]


# Module-level default instance (lazy init on first use)
_default_client: LLMClient | None = None


def get_default_client() -> LLMClient:
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client
