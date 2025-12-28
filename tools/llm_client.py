"""LLM client for interacting with language models (Anthropic Claude).

The real application talks to Anthropic's Claude models. For the purposes of
our open-source test environment we still need the orchestration pipeline to
run even when no API key is available. This module therefore provides a client
that operates in two modes:

* When an ``ANTHROPIC_API_KEY`` is available, requests are proxied to the
  official Anthropic SDK.
* Otherwise, the client falls back to a deterministic stub that heuristically
  extracts information from the supplied prompts. The stub never performs
  network operations but mirrors the shape of the responses expected by the
  rest of the system.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from anthropic import Anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from tools.stub_llm_client import StubLLMHandler

logger = logging.getLogger("themis.llm_client")


class LLMClient:
    """Wrapper for Anthropic Claude API with structured output support.

    Supports advanced features:
    - Extended thinking mode for deeper reasoning
    - 1-hour prompt caching for cost/latency optimization
    - Code execution tool for computational tasks
    - Files API for persistent document management
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-3-5-sonnet-20241022",
        use_extended_thinking: bool = True,  # Enabled by default for deeper reasoning
        use_prompt_caching: bool = True,     # Enabled by default for cost/latency optimization
        enable_code_execution: bool = False,
    ):
        """Initialise the client.

        Args:
            api_key: Anthropic API key. If ``None`` the environment variable
                ``ANTHROPIC_API_KEY`` is consulted.
            model: Claude model to use when the API key is present.
            use_extended_thinking: Enable extended thinking mode for deeper reasoning.
            use_prompt_caching: Enable 1-hour prompt caching for cost savings.
            enable_code_execution: Enable Python code execution tool.
        """

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self.use_extended_thinking = use_extended_thinking
        self.use_prompt_caching = use_prompt_caching
        self.enable_code_execution = enable_code_execution
        self._stub_mode = not self.api_key
        self.client = None if self._stub_mode else Anthropic(api_key=self.api_key)
        self._stub_handler = StubLLMHandler() if self._stub_mode else None

    @retry(
        retry=retry_if_exception_type((Exception,)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _call_anthropic_api(
        self,
        system_prompt: str,
        messages: list[dict[str, str]],
        max_tokens: int,
        file_ids: list[str] | None = None,
    ) -> str:
        """Call Anthropic API with retry logic and advanced features.

        Retries up to 3 times with exponential backoff (2s, 4s, 8s).
        This handles transient network errors and rate limiting gracefully.

        Supports:
        - Extended thinking mode for deeper reasoning
        - 1-hour prompt caching for cost optimization
        - Code execution tool for computational tasks
        - Files API for document references
        """
        logger.debug(
            f"Calling Anthropic API (model: {self.model}, max_tokens: {max_tokens}, "
            f"extended_thinking: {self.use_extended_thinking}, caching: {self.use_prompt_caching}, "
            f"code_execution: {self.enable_code_execution})"
        )

        # Build request parameters
        request_params: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
        }

        # Configure extended thinking
        if self.use_extended_thinking:
            request_params["extended_thinking"] = True

        # Configure prompt caching for system prompts
        if self.use_prompt_caching:
            request_params["system"] = [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
            request_params["extra_headers"] = {"anthropic-cache-control": "ephemeral+extended"}
        else:
            request_params["system"] = system_prompt

        # Add beta headers for extended thinking with interleaved mode
        if self.use_extended_thinking:
            if "extra_headers" not in request_params:
                request_params["extra_headers"] = {}
            request_params["extra_headers"]["anthropic-beta"] = "interleaved-thinking-2025-05-14"

        # Configure code execution tool
        if self.enable_code_execution:
            request_params["tools"] = [{"type": "code_execution_2025_04_01", "name": "python"}]

        # Add file references to messages if provided
        if file_ids and messages and messages[0]["role"] == "user":
            content = messages[0]["content"]
            if isinstance(content, str):
                messages[0]["content"] = [{"type": "text", "text": content}]
            # Insert file references at the beginning, preserving order
            file_blocks = [{"type": "file", "file": {"file_id": fid}} for fid in file_ids]
            messages[0]["content"] = file_blocks + messages[0]["content"]

        response = self.client.messages.create(**request_params)

        # Extract content from response, handling thinking blocks
        content_parts = []
        for block in response.content:
            if hasattr(block, "type"):
                if block.type == "text":
                    content_parts.append(block.text)
                elif block.type == "thinking":
                    # Log thinking content for observability
                    logger.debug(f"Extended thinking: {block.thinking[:200]}...")
                # Skip tool_use blocks - they're intermediate steps

        content = "\n".join(content_parts)
        logger.debug(f"Received response from Anthropic API ({len(content)} chars)")
        return content

    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: dict[str, Any] | None = None,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Generate a structured JSON response from the LLM.

        Automatically retries on failure with exponential backoff.
        """
        if self._stub_mode:
            return await self._stub_handler.generate_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format=response_format,
                max_tokens=max_tokens,
            )

        messages = [{"role": "user", "content": user_prompt}]

        if response_format:
            schema_instruction = (
                "\n\nYou MUST respond with valid JSON matching this schema:\n"
                f"{json.dumps(response_format, indent=2)}"
            )
            system_prompt = system_prompt + schema_instruction

        content = await self._call_anthropic_api(system_prompt, messages, max_tokens)

        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                json_str = content[start:end]
                return json.loads(json_str)
            return {"response": content}
        except json.JSONDecodeError:
            return {"response": content}

    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        file_ids: list[str] | None = None,
    ) -> str:
        """Generate a plain-text response from the LLM.

        Automatically retries on failure with exponential backoff.

        Args:
            system_prompt: System prompt for the model.
            user_prompt: User prompt for the model.
            max_tokens: Maximum tokens to generate.
            file_ids: Optional list of file IDs uploaded via Files API.
        """
        if self._stub_mode:
            return self._stub_handler.generate_text(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
            )

        messages = [{"role": "user", "content": user_prompt}]
        return await self._call_anthropic_api(system_prompt, messages, max_tokens, file_ids)

    async def generate_with_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict[str, Any]],
        tool_functions: dict[str, Any],
        max_tokens: int = 4096,
        max_tool_rounds: int = 10,
    ) -> dict[str, Any]:
        """Generate a response with autonomous tool use.

        Claude will decide which tools to call, in what order, and with what parameters.
        This method handles the tool use loop automatically.

        Args:
            system_prompt: System prompt describing the agent's role.
            user_prompt: User prompt with the task.
            tools: List of tool definitions in Anthropic format:
                [
                    {
                        "name": "tool_name",
                        "description": "What this tool does",
                        "input_schema": {
                            "type": "object",
                            "properties": {...},
                            "required": [...]
                        }
                    }
                ]
            tool_functions: Dict mapping tool names to callable functions:
                {"tool_name": async_function or sync_function}
            max_tokens: Maximum tokens for each generation.
            max_tool_rounds: Maximum number of tool use rounds to prevent infinite loops.

        Returns:
            dict with:
                - "result": Final response from Claude after all tool use
                - "tool_calls": List of tools called and their results
                - "reasoning": Claude's reasoning (if extended thinking enabled)
        """
        if self._stub_mode:
            return await self._stub_handler.generate_with_tools(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                tools=tools,
                tool_functions=tool_functions,
            )

        messages = [{"role": "user", "content": user_prompt}]
        tool_calls = []
        rounds = 0

        while rounds < max_tool_rounds:
            rounds += 1
            logger.info(f"Tool use round {rounds}/{max_tool_rounds}")

            # Call Claude with available tools
            request_params: dict[str, Any] = {
                "model": self.model,
                "max_tokens": max_tokens,
                "system": system_prompt,
                "messages": messages,
                "tools": tools,
            }

            response = self.client.messages.create(**request_params)

            # Check if Claude wants to use tools
            if response.stop_reason == "tool_use":
                # Extract tool use blocks
                tool_use_blocks = [block for block in response.content if hasattr(block, 'type') and block.type == "tool_use"]

                if not tool_use_blocks:
                    # No tool use despite stop_reason - shouldn't happen, but handle gracefully
                    break

                # Add Claude's response to conversation
                messages.append({"role": "assistant", "content": response.content})

                # Execute each tool
                tool_results = []
                for tool_use in tool_use_blocks:
                    tool_name = tool_use.name
                    tool_input = tool_use.input

                    logger.info(f"Claude calling tool: {tool_name} with input: {tool_input}")

                    if tool_name not in tool_functions:
                        error_msg = f"Tool {tool_name} not found in tool_functions"
                        logger.error(error_msg)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": json.dumps({"error": error_msg}),
                            "is_error": True
                        })
                        continue

                    try:
                        # Execute tool (handle both sync and async)
                        tool_fn = tool_functions[tool_name]
                        result = tool_fn(**tool_input) if callable(tool_fn) else tool_fn
                        if asyncio.iscoroutine(result):
                            result = await result

                        logger.info(f"Tool {tool_name} returned: {str(result)[:200]}")

                        tool_calls.append({
                            "tool": tool_name,
                            "input": tool_input,
                            "result": result
                        })

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": json.dumps(result) if not isinstance(result, str) else result
                        })
                    except Exception as e:
                        error_msg = f"Error executing {tool_name}: {str(e)}"
                        logger.error(error_msg, exc_info=True)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": json.dumps({"error": error_msg}),
                            "is_error": True
                        })

                # Add tool results to conversation
                messages.append({"role": "user", "content": tool_results})

            elif response.stop_reason == "end_turn":
                # Claude is done using tools, extract final response
                text_blocks = [block.text for block in response.content if hasattr(block, 'type') and block.type == "text"]
                final_response = "\n".join(text_blocks)

                return {
                    "result": final_response,
                    "tool_calls": tool_calls,
                    "rounds": rounds
                }
            else:
                # Unexpected stop reason
                logger.warning(f"Unexpected stop_reason: {response.stop_reason}")
                break

        # Max rounds reached or unexpected termination
        logger.warning(f"Tool use loop terminated after {rounds} rounds (max: {max_tool_rounds})")

        # Try to extract any text response
        if response.content:
            text_blocks = [block.text for block in response.content if hasattr(block, 'type') and block.type == "text"]
            final_response = "\n".join(text_blocks) if text_blocks else "Max tool rounds reached"
        else:
            final_response = "No response generated"

        return {
            "result": final_response,
            "tool_calls": tool_calls,
            "rounds": rounds
        }

    def upload_file(self, file_path: str) -> str:
        """Upload a file to Anthropic Files API for persistent reference.

        Args:
            file_path: Path to the file to upload.

        Returns:
            file_id: Unique identifier for the uploaded file.

        Raises:
            ValueError: If in stub mode (no API key available).
        """
        if self._stub_mode:
            logger.warning("File upload not available in stub mode")
            raise ValueError("File upload requires ANTHROPIC_API_KEY")

        logger.info(f"Uploading file: {file_path}")
        with open(file_path, "rb") as f:
            file_obj = self.client.files.create(file=f, purpose="user_data")

        logger.info(f"File uploaded successfully: {file_obj.id}")
        return file_obj.id

    def list_files(self) -> list[dict[str, Any]]:
        """List all uploaded files in the Files API.

        Returns:
            List of file metadata dictionaries.
        """
        if self._stub_mode:
            return []

        response = self.client.files.list()
        return [{"id": f.id, "filename": f.filename, "created_at": f.created_at} for f in response.data]

    def delete_file(self, file_id: str) -> None:
        """Delete a file from the Files API.

        Args:
            file_id: ID of the file to delete.
        """
        if self._stub_mode:
            return

        self.client.files.delete(file_id)
        logger.info(f"Deleted file: {file_id}")

    async def generate_with_mcp(
        self,
        system_prompt: str,
        user_prompt: str,
        mcp_servers: list[dict[str, str]],
        max_tokens: int = 4096,
    ) -> str:
        """Generate a response with MCP server integration.

        Args:
            system_prompt: System prompt for the model.
            user_prompt: User prompt for the model.
            mcp_servers: List of MCP server configurations.
                Each dict should have 'url' and optionally 'api_key'.
            max_tokens: Maximum tokens to generate.

        Returns:
            Generated text response.

        Example:
            mcp_servers = [{
                "url": "https://legal-research.example.com/mcp",
                "api_key": os.getenv("LEGAL_DB_KEY")
            }]
        """
        if self._stub_mode:
            logger.warning("MCP not available in stub mode, falling back to standard generation")
            return await self.generate_text(system_prompt, user_prompt, max_tokens)

        logger.info(f"Calling API with {len(mcp_servers)} MCP server(s)")

        request_params: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "mcp_servers": mcp_servers,
        }

        if self.use_extended_thinking:
            request_params["extended_thinking"] = True

        response = self.client.messages.create(**request_params)

        content_parts = []
        for block in response.content:
            if hasattr(block, "type") and block.type == "text":
                content_parts.append(block.text)

        return "\n".join(content_parts)


# Global singleton for easy access
_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Get or create the global LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


def set_llm_client(client: LLMClient) -> None:
    """Set the global LLM client instance (useful for testing)."""
    global _llm_client
    _llm_client = client
