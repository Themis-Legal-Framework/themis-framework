"""
OpenRouter API Client

Handles communication with the OpenRouter API for multi-model LLM access.
"""
from __future__ import annotations

import httpx
from typing import AsyncIterator

from backend.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL


class OpenRouterClient:
    """Async client for OpenRouter API."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key or OPENROUTER_API_KEY
        self.base_url = base_url or OPENROUTER_BASE_URL
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://llm-counsel.local",
                    "X-Title": "LLM-COUNSEL Legal Deliberation"
                },
                timeout=120.0
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def chat_completion(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False
    ) -> dict | AsyncIterator[str]:
        """
        Send a chat completion request to OpenRouter.

        Args:
            model: The model identifier (e.g., "anthropic/claude-sonnet-4-20250514")
            messages: List of message dicts with "role" and "content"
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
            stream: Whether to stream the response

        Returns:
            Full response dict if stream=False, async iterator of content chunks if stream=True
        """
        client = await self._get_client()

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }

        if stream:
            return self._stream_response(client, payload)
        else:
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()
            return response.json()

    async def _stream_response(
        self,
        client: httpx.AsyncClient,
        payload: dict
    ) -> AsyncIterator[str]:
        """Stream response chunks from OpenRouter."""
        async with client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        import json
                        chunk = json.loads(data)
                        if chunk.get("choices") and chunk["choices"][0].get("delta", {}).get("content"):
                            yield chunk["choices"][0]["delta"]["content"]
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

    async def generate(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> str:
        """
        Simple generation interface with system and user prompts.

        Args:
            model: The model identifier
            system_prompt: System/context prompt
            user_prompt: User query
            temperature: Sampling temperature
            max_tokens: Maximum tokens

        Returns:
            Generated text content
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = await self.chat_completion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False
        )

        return response["choices"][0]["message"]["content"]

    async def generate_stream(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> AsyncIterator[str]:
        """
        Streaming generation interface.

        Args:
            model: The model identifier
            system_prompt: System/context prompt
            user_prompt: User query
            temperature: Sampling temperature
            max_tokens: Maximum tokens

        Yields:
            Text content chunks as they arrive
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        async for chunk in await self.chat_completion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True
        ):
            yield chunk


# Global client instance
_client: OpenRouterClient | None = None


def get_client() -> OpenRouterClient:
    """Get the global OpenRouter client instance."""
    global _client
    if _client is None:
        _client = OpenRouterClient()
    return _client


async def cleanup_client():
    """Cleanup the global client on shutdown."""
    global _client
    if _client:
        await _client.close()
        _client = None
