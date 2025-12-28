"""Tests for LLM client including streaming functionality."""

from __future__ import annotations

import pytest

from tools.llm_client import LLMClient


@pytest.fixture
def stub_llm_client() -> LLMClient:
    """Create an LLM client in stub mode (no API key)."""
    return LLMClient(api_key=None)


class TestLLMClientStreaming:
    """Tests for streaming functionality."""

    @pytest.mark.asyncio
    async def test_generate_text_stream_yields_chunks(
        self, stub_llm_client: LLMClient
    ) -> None:
        """Test that streaming yields text chunks in stub mode."""
        chunks = []
        async for chunk in stub_llm_client.generate_text_stream(
            system_prompt="You are a legal assistant.",
            user_prompt="Analyze this case.",
            max_tokens=100,
        ):
            chunks.append(chunk)

        # Should yield multiple chunks
        assert len(chunks) > 0
        # Joined chunks should form coherent text
        full_text = "".join(chunks)
        assert len(full_text) > 0

    @pytest.mark.asyncio
    async def test_generate_text_stream_simulates_words(
        self, stub_llm_client: LLMClient
    ) -> None:
        """Test that stub streaming yields word-by-word output."""
        chunks = []
        async for chunk in stub_llm_client.generate_text_stream(
            system_prompt="Summarize the document.",
            user_prompt="Document content here.",
            max_tokens=50,
        ):
            chunks.append(chunk)

        # Each chunk should be a word (possibly with trailing space)
        for chunk in chunks:
            # Chunks should be reasonable size (not empty, not too long)
            assert 0 < len(chunk) <= 100


class TestLLMClientStubMode:
    """Tests for stub mode behavior."""

    def test_stub_mode_enabled_without_api_key(self) -> None:
        """Test that stub mode is enabled when no API key is provided."""
        client = LLMClient(api_key=None)
        assert client._stub_mode is True

    def test_stub_mode_disabled_with_api_key(self) -> None:
        """Test that stub mode is disabled when API key is provided."""
        client = LLMClient(api_key="test-key-123")
        assert client._stub_mode is False

    @pytest.mark.asyncio
    async def test_generate_text_in_stub_mode(
        self, stub_llm_client: LLMClient
    ) -> None:
        """Test that generate_text works in stub mode."""
        result = stub_llm_client._stub_handler.generate_text(
            system_prompt="You are a legal assistant.",
            user_prompt="Analyze this contract.",
            max_tokens=100,
        )
        assert isinstance(result, str)
        assert len(result) > 0


class TestLLMClientConfiguration:
    """Tests for client configuration options."""

    def test_default_model_is_claude_opus(self) -> None:
        """Test that default model is Claude Opus 4.5."""
        client = LLMClient(api_key=None)
        assert "opus" in client.model.lower()

    def test_custom_model_configuration(self) -> None:
        """Test that custom model can be configured."""
        client = LLMClient(api_key=None, model="claude-3-5-sonnet-20241022")
        assert client.model == "claude-3-5-sonnet-20241022"

    def test_extended_thinking_enabled_by_default(self) -> None:
        """Test that extended thinking is enabled by default."""
        client = LLMClient(api_key=None)
        assert client.use_extended_thinking is True

    def test_prompt_caching_enabled_by_default(self) -> None:
        """Test that prompt caching is enabled by default."""
        client = LLMClient(api_key=None)
        assert client.use_prompt_caching is True

    def test_code_execution_disabled_by_default(self) -> None:
        """Test that code execution is disabled by default."""
        client = LLMClient(api_key=None)
        assert client.enable_code_execution is False
