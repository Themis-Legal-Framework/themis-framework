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

import ast
import asyncio
import json
import logging
import os
import re
from collections.abc import Iterable
from typing import Any

from anthropic import Anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

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
        if file_ids:
            if messages and messages[0]["role"] == "user":
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
            return self._generate_structured_stub(
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
            return self._generate_text_stub(
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
            return await self._generate_with_tools_stub(
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

    # ------------------------------------------------------------------
    # Stub implementation helpers
    # ------------------------------------------------------------------

    def _generate_structured_stub(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_format: dict[str, Any] | None,
        max_tokens: int,
    ) -> dict[str, Any]:
        if not response_format:
            return {
                "response": self._generate_text_stub(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=max_tokens,
                )
            }

        keys = set(response_format.keys())

        if {"summary", "key_facts", "dates", "parties_mentioned"}.issubset(keys):
            return self._stub_document_parse(user_prompt)
        if "issues" in keys:
            return {"issues": self._stub_issue_spotter(user_prompt)}
        if {
            "objectives",
            "actions",
            "positions",
            "leverage_points",
            "proposed_concessions",
            "contingencies",
            "assumptions",
        }.issubset(keys):
            return self._stub_strategy_template(user_prompt)
        if {"confidence", "weaknesses", "evidentiary_gaps", "unknowns", "potential_problems"}.issubset(keys):
            return self._stub_risk_assessment(user_prompt)
        if "full_document" in keys:
            return self._stub_document_generator(user_prompt, system_prompt)

        result: dict[str, Any] = {}
        for key, template in response_format.items():
            if isinstance(template, dict):
                result[key] = {}
            elif isinstance(template, list):
                result[key] = []
            else:
                result[key] = ""
        return result

    def _generate_text_stub(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
    ) -> str:
        context = self._extract_line(user_prompt, "Matter Context:") or "the presented matter"
        parties = self._extract_line(user_prompt, "Parties:")
        party_sentence = f"The parties involved are {parties}." if parties else ""

        issue_lines = self._extract_bullets(user_prompt, "Legal Issues Identified:")
        if issue_lines:
            issues_sentence = f"Key legal issues include {self._natural_join(issue_lines)}."
        else:
            issues_sentence = "Key legal issues will require further investigation."

        authorities = self._extract_bullets(user_prompt, "Authorities:")
        if authorities:
            authorities_sentence = (
                f"Supporting authorities such as {self._natural_join(authorities)} guide the analysis."
            )
        else:
            authorities_sentence = "No authorities were supplied, so additional research is required."

        follow_up_sentence = (
            "Further factual development should focus on resolving open questions and strengthening the evidentiary record."
        )

        paragraphs = [
            f"The matter concerns {context}. {party_sentence}".strip(),
            issues_sentence,
            authorities_sentence,
            follow_up_sentence,
        ]

        return "\n\n".join(paragraph for paragraph in paragraphs if paragraph)

    async def _generate_with_tools_stub(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict[str, Any]],
        tool_functions: dict[str, Any],
    ) -> dict[str, Any]:
        """Stub implementation that heuristically uses tools based on prompt content."""
        logger.info("Running in stub mode - simulating autonomous tool use")

        tool_calls = []
        result_text = f"Stub mode analysis based on {len(tools)} available tools.\n\n"

        # Extract matter from user_prompt if it's JSON
        matter = {}
        try:
            match = re.search(r'\{[^{}]*"summary"[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', user_prompt, re.DOTALL)
            if not match:
                # Try to find any JSON object
                match = re.search(r'\{.*\}', user_prompt, re.DOTALL)
            if match:
                matter = json.loads(match.group(0))
        except Exception:
            logger.debug("Could not extract matter JSON from prompt")

        # Simulate calling relevant tools based on prompt content
        prompt_lower = user_prompt.lower()

        # If document-related keywords, call document_parser if available
        if any(kw in prompt_lower for kw in ["document", "parse", "extract", "text"]):
            if "document_parser" in tool_functions:
                logger.info("Stub: Calling document_parser")
                try:
                    parsed = tool_functions["document_parser"](matter)
                    if asyncio.iscoroutine(parsed):
                        parsed = await parsed
                except Exception as e:
                    logger.debug(f"Custom tool failed, using stub: {e}")
                    parsed = self._stub_document_parse(user_prompt)
                tool_calls.append({"tool": "document_parser", "input": {}, "result": parsed})
                # Handle both list and dict results
                if isinstance(parsed, list):
                    key_facts_count = sum(len(doc.get('key_facts', [])) for doc in parsed if isinstance(doc, dict))
                else:
                    key_facts_count = len(parsed.get('key_facts', []))
                result_text += f"Parsed documents and extracted {key_facts_count} key facts.\n\n"

        # If timeline keywords, call timeline_builder if available
        if any(kw in prompt_lower for kw in ["timeline", "chronolog", "sequence", "events"]):
            if "timeline_builder" in tool_functions:
                logger.info("Stub: Calling timeline_builder")
                try:
                    timeline = tool_functions["timeline_builder"](matter, None)
                    if asyncio.iscoroutine(timeline):
                        timeline = await timeline
                except Exception as e:
                    logger.debug(f"Custom tool failed, using stub: {e}")
                    timeline = [{"date": "2024-01-15", "description": "Event from stub timeline"}]
                tool_calls.append({"tool": "timeline_builder", "input": {}, "result": timeline})
                result_text += f"Built timeline with {len(timeline)} events.\n\n"

        # If damages/calculation keywords, call damages_calculator if available
        if any(kw in prompt_lower for kw in ["damage", "calculat", "expense", "loss", "wage"]):
            if "damages_calculator" in tool_functions:
                logger.info("Stub: Calling damages_calculator")
                try:
                    damages = tool_functions["damages_calculator"]({"economic_losses": {}, "non_economic_factors": {}})
                    if asyncio.iscoroutine(damages):
                        damages = await damages
                except Exception as e:
                    logger.debug(f"Custom tool failed, using stub: {e}")
                    damages = {"total": 110000, "medical": 85000, "lost_wages": 25000}
                tool_calls.append({"tool": "damages_calculator", "input": {}, "result": damages})
                result_text += f"Calculated total damages: ${damages.get('total', 0)}\n\n"

        # If legal/issue keywords, call issue_spotter if available
        if any(kw in prompt_lower for kw in ["issue", "legal", "cause", "claim", "negligence"]):
            issues = []
            if "issue_spotter" in tool_functions:
                logger.info("Stub: Calling issue_spotter")
                try:
                    issues = tool_functions["issue_spotter"](matter)
                    if asyncio.iscoroutine(issues):
                        issues = await issues
                except Exception as e:
                    logger.debug(f"Custom tool failed, using stub: {e}")
                    issues = self._stub_issue_spotter(user_prompt)
                tool_calls.append({"tool": "issue_spotter", "input": {}, "result": issues})
                result_text += f"Identified {len(issues)} legal issues.\n\n"

            # If citation_retriever available, call it after issue_spotter
            if "citation_retriever" in tool_functions and issues:
                logger.info("Stub: Calling citation_retriever")
                try:
                    citations = tool_functions["citation_retriever"](matter, issues)
                    # citation_retriever is typically not async, but check anyway
                    if asyncio.iscoroutine(citations):
                        citations = await citations
                except Exception as e:
                    logger.error(f"citation_retriever failed: {e}", exc_info=True)
                    citations = []
                tool_calls.append({"tool": "citation_retriever", "input": {}, "result": citations})
                result_text += f"Retrieved {len(citations)} citations.\n\n"

        # If strategy keywords, call risk_assessor or strategy_template if available
        if any(kw in prompt_lower for kw in ["strategy", "risk", "negotiate", "settlement"]):
            if "strategy_template" in tool_functions:
                logger.info("Stub: Calling strategy_template")
                try:
                    strategy = tool_functions["strategy_template"](matter)
                    if asyncio.iscoroutine(strategy):
                        strategy = await strategy
                    tool_calls.append({"tool": "strategy_template", "input": {}, "result": strategy})
                    result_text += "Developed legal strategy.\n\n"
                    # Also call risk_assessor if available
                    if "risk_assessor" in tool_functions:
                        logger.info("Stub: Calling risk_assessor")
                        risk = tool_functions["risk_assessor"](matter, strategy)
                        if asyncio.iscoroutine(risk):
                            risk = await risk
                        tool_calls.append({"tool": "risk_assessor", "input": {}, "result": risk})
                        result_text += "Assessed case risks and strategic considerations.\n\n"
                except Exception as e:
                    logger.debug(f"Custom tool failed: {e}")
            elif "risk_assessor" in tool_functions:
                logger.info("Stub: Calling risk_assessor")
                try:
                    risk = tool_functions["risk_assessor"](matter, {})
                    if asyncio.iscoroutine(risk):
                        risk = await risk
                except Exception as e:
                    logger.debug(f"Custom tool failed, using stub: {e}")
                    risk = {"confidence": 85, "weaknesses": ["Stub weakness 1"], "unknowns": ["Stub unknown 1"]}
                tool_calls.append({"tool": "risk_assessor", "input": {}, "result": risk})
                result_text += "Assessed case risks and strategic considerations.\n\n"

        # If document drafting keywords, call DDA tools if available
        if any(kw in prompt_lower for kw in ["document", "draft", "generate", "compose", "memorandum", "complaint", "motion"]):
            # Call section_generator if available
            if "section_generator" in tool_functions:
                logger.info("Stub: Calling section_generator")
                try:
                    # Extract facts from matter - could be at top level or nested under agent outputs
                    facts = matter.get("facts", {})
                    if not facts or not facts.get("fact_pattern_summary"):
                        # Try to find facts from LDA output
                        if "lda" in matter and isinstance(matter["lda"], dict):
                            facts = matter["lda"].get("facts", {})

                    # Extract legal analysis - could be from DEA
                    legal_analysis = matter.get("legal_analysis", {})
                    if not legal_analysis:
                        if "dea" in matter and isinstance(matter["dea"], dict):
                            legal_analysis = matter["dea"].get("legal_analysis", {})

                    # Extract strategy - could be from LSA
                    strategy = matter.get("strategy", {})
                    if not strategy:
                        if "lsa" in matter and isinstance(matter["lsa"], dict):
                            strategy = matter["lsa"].get("strategy", {})

                    logger.info(f"Stub section_generator: facts={len(facts.get('fact_pattern_summary', []))} items, "
                              f"issues={len(legal_analysis.get('issues', []))}, "
                              f"strategy={'yes' if strategy else 'no'}")

                    sections = tool_functions["section_generator"](
                        document_type=matter.get("document_type", "memorandum"),
                        facts=facts,
                        legal_analysis=legal_analysis,
                        strategy=strategy,
                        jurisdiction=matter.get("jurisdiction", "federal")
                    )
                    if asyncio.iscoroutine(sections):
                        sections = await sections
                    tool_calls.append({"tool": "section_generator", "input": {}, "result": sections})
                    result_text += "Generated document sections.\n\n"
                except Exception as e:
                    logger.debug(f"section_generator failed: {e}")
                    sections = {}

            # Call document_composer if available
            if "document_composer" in tool_functions:
                logger.info("Stub: Calling document_composer")
                try:
                    composed = tool_functions["document_composer"](
                        document_type=matter.get("document_type", "memorandum"),
                        sections=sections if "section_generator" in tool_functions else {},
                        citations=matter.get("authorities", {}),
                        jurisdiction=matter.get("jurisdiction", "federal"),
                        matter=matter
                    )
                    if asyncio.iscoroutine(composed):
                        composed = await composed
                    tool_calls.append({"tool": "document_composer", "input": {}, "result": composed})
                    result_text += "Composed final document.\n\n"
                except Exception as e:
                    logger.debug(f"document_composer failed: {e}")

        # Default: generate text summary
        if not tool_calls:
            result_text += self._generate_text_stub(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=4096
            )

        return {
            "result": result_text.strip(),
            "tool_calls": tool_calls,
            "rounds": len(tool_calls)
        }

    def _stub_document_parse(self, user_prompt: str) -> dict[str, Any]:
        content = self._extract_section(
            user_prompt,
            "Document Content:",
            stop_markers=("Please provide",),
        )
        sentences = self._split_sentences(content)
        summary = " ".join(sentences[:2]).strip()
        if not summary and content:
            summary = content[:200].strip()

        key_facts = self._dedupe([sentence.strip() for sentence in sentences[:3] if sentence.strip()])
        if not key_facts and content:
            key_facts = [segment.strip() for segment in content.splitlines() if segment.strip()][:3]

        dates = self._dedupe(re.findall(r"\d{4}-\d{2}-\d{2}", content))
        parties_line = self._extract_line(user_prompt, "Parties:")
        parties = []
        if parties_line:
            parties = self._dedupe(
                [segment.strip() for segment in re.split(r",| and ", parties_line) if segment.strip()]
            )

        return {
            "summary": summary or "Summary unavailable from document stub.",
            "key_facts": key_facts,
            "dates": dates,
            "parties_mentioned": parties,
        }

    def _stub_issue_spotter(self, user_prompt: str) -> list[dict[str, Any]]:
        text = user_prompt.lower()
        sentences = self._split_sentences(user_prompt)

        def issue_for(
            keyword: str,
            *,
            label: str,
            area: str,
            fact_keywords: Iterable[str],
            strength: str = "moderate",
        ) -> dict[str, Any] | None:
            if keyword not in text:
                return None
            facts = [
                sentence.strip()
                for sentence in sentences
                if any(token in sentence.lower() for token in fact_keywords)
            ]
            if not facts:
                facts = ["Referenced facts in provided materials."]
            return {
                "issue": label,
                "area_of_law": area,
                "facts": self._dedupe(facts)[:3],
                "strength": strength,
            }

        mappings = [
            ("breach", "Breach of contract", "Contract", ["breach", "contract", "deliver"], "strong"),
            ("neglig", "Negligence", "Tort", ["neglig", "injur", "collision", "fail"], "strong"),
            ("damage", "Damages assessment", "Damages", ["damage", "loss", "therapy", "income"], "moderate"),
            ("settlement", "Settlement posture", "Negotiation", ["settlement", "offer", "demand"], "moderate"),
        ]

        issues: list[dict[str, Any]] = []
        for keyword, label, area, fact_keywords, strength in mappings:
            issue = issue_for(
                keyword,
                label=label,
                area=area,
                fact_keywords=fact_keywords,
                strength=strength,
            )
            if issue:
                issues.append(issue)

        if not issues:
            first_sentence = sentences[0].strip() if sentences else "Additional facts are required to identify issues."
            issues.append(
                {
                    "issue": "Further issue spotting required",
                    "area_of_law": "General",
                    "facts": [first_sentence],
                    "strength": "unknown",
                }
            )

        return issues[:5]

    def _stub_strategy_template(self, user_prompt: str) -> dict[str, Any]:
        goals_raw = self._extract_line(user_prompt, "Client Goals:")
        goals: dict[str, Any] = {}
        if goals_raw:
            try:
                goals = ast.literal_eval(goals_raw)
            except (SyntaxError, ValueError):
                pass

        key_facts = self._extract_bullets(user_prompt, "Key Facts:")
        legal_issues = self._extract_bullets(user_prompt, "Legal Issues:")

        opening_position = goals.get("settlement") or goals.get("opening")
        fallback_position = goals.get("fallback") or goals.get("minimum")

        objectives = (
            goals.get("settlement")
            or (legal_issues[0] if legal_issues else None)
            or "Advance the client's negotiating posture"
        )

        actions = [
            "Prepare negotiation brief highlighting the strongest liability facts.",
            "Engage opposing counsel with a settlement framework anchored to the client's objectives.",
        ]
        if key_facts:
            actions.append(f"Emphasise: {key_facts[0]}")
        actions.append("Outline follow-up evidence needed to solidify damages claims.")

        positions = {
            "opening": opening_position or objectives,
            "ideal": goals.get("ideal") or opening_position or objectives,
            "minimum": goals.get("minimum") or fallback_position or "Secure meaningful monetary recovery",
            "fallback": fallback_position or "Escalate to litigation if negotiations stall",
        }

        leverage_points = key_facts[:2] if key_facts else legal_issues[:2]
        if not leverage_points:
            leverage_points = ["Well-documented liability narrative"]

        concessions = []
        if goals.get("fallback"):
            concessions.append(f"Consider fallback outcome of {goals['fallback']}")
        concessions.append("Remain flexible on payment structure if headline value is protected.")

        contingencies = [
            "Coordinate with trial team should negotiations fail to progress.",
            "Revisit settlement authority upon receipt of new information.",
        ]

        assumptions = [
            "Opposing counsel is open to early dialogue.",
            "Client can rapidly supply supplemental documentation when requested.",
        ]

        return {
            "objectives": objectives,
            "actions": self._dedupe(actions),
            "positions": positions,
            "leverage_points": self._dedupe(leverage_points),
            "proposed_concessions": self._dedupe(concessions),
            "contingencies": contingencies,
            "assumptions": assumptions,
        }

    def _stub_risk_assessment(self, user_prompt: str) -> dict[str, Any]:
        issues = self._extract_bullets(user_prompt, "Legal Issues:")
        key_facts = self._extract_bullets(user_prompt, "Key Facts:")

        weaknesses = [
            "Need to substantiate damages with updated records.",
            "Monitor for comparative fault allegations from the defence.",
        ]
        evidentiary_gaps = ["Outstanding discovery on economic losses."]
        if key_facts:
            evidentiary_gaps.append(f"Corroborate: {key_facts[-1]}")

        unknowns = ["Awaiting opposing counsel's position on liability."]
        if issues:
            unknowns.append("Assess strength of secondary issues through further investigation.")

        potential_problems = [
            "Delays in treatment or document production could undermine leverage.",
        ]

        return {
            "confidence": 68,
            "weaknesses": self._dedupe(weaknesses),
            "evidentiary_gaps": self._dedupe(evidentiary_gaps),
            "unknowns": self._dedupe(unknowns),
            "potential_problems": potential_problems,
        }

    def _stub_document_generator(self, user_prompt: str, system_prompt: str) -> dict[str, Any]:
        """Generate a stub legal document based on prompt analysis."""
        # Extract document type from prompt - look for explicit "Generate a ... {doc_type}" statements
        # This is more reliable than just keyword matching which can be fooled by examples
        doc_type = "complaint"  # Default

        # Look for "Generate a complete, professional {doc_type}" pattern (most reliable)
        generate_match = re.search(r'generate\s+a\s+(?:complete|professional|court-ready|formal)?,?\s*(?:complete|professional|court-ready|formal)?\s+(\w+)', user_prompt.lower())
        if generate_match:
            detected = generate_match.group(1)
            if detected in ("complaint", "motion", "memorandum", "demand_letter"):
                doc_type = detected
                logger.debug(f"Stub generator: Detected doc_type from 'Generate...' pattern: {doc_type}")
            elif detected == "demand":
                doc_type = "demand_letter"
                logger.debug("Stub generator: Detected 'demand' -> demand_letter from 'Generate...' pattern")
        else:
            # Fallback: Look for keywords, but be more careful
            # Only match if the keyword appears early in the prompt (not in examples/instructions)
            prompt_start = user_prompt.lower()[:500]  # Only check first 500 chars
            if "demand letter" in prompt_start or "demand_letter" in prompt_start:
                doc_type = "demand_letter"
                logger.debug("Stub generator: Detected 'demand letter' keyword in prompt start")
            elif "motion" in prompt_start:
                doc_type = "motion"
                logger.debug("Stub generator: Detected 'motion' keyword in prompt start")
            elif "memorandum" in prompt_start:
                doc_type = "memorandum"
                logger.debug("Stub generator: Detected 'memorandum' keyword in prompt start")

        logger.debug(f"Stub generator: Final doc_type={doc_type}")

        # Extract key information from the prompt
        jurisdiction = self._extract_line(user_prompt, "Jurisdiction:") or "California"

        # Try to extract parties information from various sections
        plaintiff = "PLAINTIFF NAME"
        defendant = "DEFENDANT NAME"

        # Look for parties in different formats
        parties_line = self._extract_line(user_prompt, "Parties:")
        if parties_line:
            # Handle formats like "Alex Benedict (Plaintiff), Hien Ngo (Defendant)"
            # Remove role labels in parentheses for parsing
            clean_line = re.sub(r'\([^)]*\)', '', parties_line)
            parts = [p.strip() for p in clean_line.split(",")]
            if len(parts) >= 1 and parts[0]:
                plaintiff = parts[0]
            if len(parts) >= 2 and parts[1]:
                defendant = parts[1]

        # Also try extracting from JSON-like structures in the prompt
        # Look for parties array format: [{"name": "...", "role": "Plaintiff"}, ...]
        if plaintiff == "PLAINTIFF NAME" or defendant == "DEFENDANT NAME":
            parties_array_match = re.search(r'"parties":\s*\[(.*?)\]', user_prompt, re.DOTALL)
            if parties_array_match:
                parties_json = parties_array_match.group(1)
                # Extract plaintiff
                plaintiff_obj = re.search(r'{[^}]*"name":\s*"([^"]+)"[^}]*"role":\s*"[Pp]laintiff', parties_json)
                if plaintiff_obj:
                    plaintiff = plaintiff_obj.group(1)
                # Extract defendant
                defendant_obj = re.search(r'{[^}]*"name":\s*"([^"]+)"[^}]*"role":\s*"[Dd]efendant', parties_json)
                if defendant_obj:
                    defendant = defendant_obj.group(1)

        # Extract facts
        facts_section = self._extract_section(user_prompt, "Facts:", stop_markers=("LEGAL ANALYSIS", "Legal Analysis", "Legal Issues"))
        if not facts_section:
            facts_section = self._extract_section(user_prompt, "MATTER INFORMATION:", stop_markers=("INSTRUCTIONS", "Legal"))
        if not facts_section:
            # Try to get fact pattern summary
            facts_bullets = self._extract_bullets(user_prompt, "fact_pattern_summary")
            if facts_bullets:
                facts_section = "\n".join(facts_bullets)

        # Extract legal issues
        issues = self._extract_bullets(user_prompt, "Legal Issues:")
        if not issues:
            issues = self._extract_bullets(user_prompt, "issues")

        # Build the document based on type
        if doc_type == "complaint":
            return self._generate_stub_complaint(jurisdiction, plaintiff, defendant, facts_section, issues)
        elif doc_type == "demand_letter":
            return self._generate_stub_demand_letter(plaintiff, defendant, facts_section, issues)
        else:
            return self._generate_stub_generic_document(doc_type, jurisdiction, facts_section, issues)

    def _generate_stub_complaint(self, jurisdiction: str, plaintiff: str, defendant: str, facts: str, issues: list[str]) -> dict[str, Any]:
        """Generate a stub complaint document."""
        # Extract specific facts if available
        fact_lines = facts.split("\n") if facts else []
        fact_paragraphs = []
        for line in fact_lines[:10]:  # Limit to first 10 lines
            line = line.strip().lstrip("•-*").strip()
            if line and len(line) > 10:
                fact_paragraphs.append(line)

        facts_text = "\n\n".join(fact_paragraphs) if fact_paragraphs else "On or about [DATE], the events giving rise to this action occurred. [Additional factual allegations to be provided]"

        # Generate causes of action from issues
        causes_of_action = []
        for i, issue in enumerate(issues[:3], 1):  # Limit to 3 causes of action
            issue_clean = issue.strip().lstrip("•-*").strip()
            if issue_clean:
                causes_of_action.append(f"FIRST CAUSE OF ACTION\n({issue_clean})\n\nPlaintiff re-alleges and incorporates by reference all previous paragraphs. [Additional elements and allegations for {issue_clean} to be provided based on {jurisdiction} law.]")

        if not causes_of_action:
            causes_of_action = ["FIRST CAUSE OF ACTION\n(Negligence)\n\nPlaintiff re-alleges and incorporates by reference all previous paragraphs. Defendant owed Plaintiff a duty of care, breached that duty, and caused damages as a direct and proximate result."]

        causes_text = "\n\n".join(causes_of_action)

        document = f"""SUPERIOR COURT OF {jurisdiction.upper()}

{plaintiff},
    Plaintiff,

v.                                  Case No. [TO BE ASSIGNED]

{defendant},
    Defendant.

COMPLAINT FOR DAMAGES

Plaintiff {plaintiff} alleges as follows:

PARTIES

1. Plaintiff {plaintiff} is an individual residing in {jurisdiction}.

2. Defendant {defendant} is an individual residing in {jurisdiction}.

JURISDICTION AND VENUE

3. This Court has jurisdiction over this action pursuant to applicable state law.

4. Venue is proper in this Court.

FACTUAL ALLEGATIONS

5. {facts_text}

CAUSES OF ACTION

{causes_text}

PRAYER FOR RELIEF

WHEREFORE, Plaintiff prays for judgment as follows:

1. For general damages according to proof;
2. For special damages according to proof;
3. For costs of suit incurred herein;
4. For such other and further relief as the Court deems just and proper.

Dated: [DATE]

Respectfully submitted,

_________________________
[Attorney Name]
[Law Firm]
[Bar Number]
Attorney for Plaintiff

VERIFICATION

I, {plaintiff}, declare under penalty of perjury that I have read the foregoing Complaint and know the contents thereof. The same is true of my own knowledge, except as to those matters stated on information and belief, and as to those matters, I believe them to be true.

Executed on [DATE] at [CITY], {jurisdiction}.

_________________________
{plaintiff}
"""
        return {"full_document": document}

    def _generate_stub_demand_letter(self, plaintiff: str, defendant: str, facts: str, issues: list[str]) -> dict[str, Any]:
        """Generate a stub demand letter."""
        fact_lines = facts.split("\n") if facts else []
        facts_text = " ".join([line.strip().lstrip("•-*").strip() for line in fact_lines if line.strip()])[:500]

        document = f"""[DATE]

{defendant}
[Address]

Re: Demand for Settlement - {plaintiff} v. {defendant}

Dear {defendant}:

This office represents {plaintiff} in connection with the incident that occurred on [DATE]. This letter serves as a formal demand for settlement.

FACTS

{facts_text or "The incident giving rise to this claim occurred on [DATE]. [Additional facts to be provided]"}

LIABILITY

Based on the facts outlined above, {defendant} is liable for the damages sustained by {plaintiff}. The evidence clearly establishes your responsibility for this matter.

DAMAGES

{plaintiff} has sustained substantial damages as a result of your actions, including but not limited to medical expenses, lost wages, pain and suffering, and emotional distress. Detailed damages documentation is available upon request.

DEMAND

We demand payment of $[AMOUNT] to settle all claims arising from this incident. This demand is valid for 30 days from the date of this letter.

Please contact our office immediately to discuss resolution. If we do not hear from you within 30 days, we will proceed with filing a lawsuit without further notice.

Sincerely,

[Attorney Name]
[Law Firm]
Attorney for {plaintiff}
"""
        return {"full_document": document}

    def _generate_stub_generic_document(self, doc_type: str, jurisdiction: str, facts: str, issues: list[str]) -> dict[str, Any]:
        """Generate a generic stub document."""
        facts_text = facts[:1000] if facts else "[Facts to be provided]"
        issues_text = "\n".join([f"• {issue}" for issue in issues[:5]]) if issues else "[Legal issues to be analyzed]"

        document = f"""{doc_type.upper().replace('_', ' ')}

Re: Legal Matter in {jurisdiction}

INTRODUCTION

This {doc_type.replace('_', ' ')} addresses the legal issues arising from the following circumstances.

FACTS

{facts_text}

LEGAL ISSUES

{issues_text}

ANALYSIS

[Detailed legal analysis to be provided based on applicable {jurisdiction} law]

CONCLUSION

[Conclusion and recommendations to be provided]

[Attorney Name]
[Law Firm]
[Date]
"""
        return {"full_document": document}

    # ------------------------------------------------------------------
    # Utility helpers for stub mode
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_line(text: str, header: str) -> str:
        prefix = header.strip()
        for raw_line in text.splitlines():
            stripped = raw_line.strip()
            if stripped.startswith(prefix):
                remainder = stripped[len(prefix) :].lstrip()
                if remainder.startswith(":"):
                    remainder = remainder[1:].strip()
                return remainder
        return ""

    @staticmethod
    def _extract_section(
        text: str,
        header: str,
        *,
        stop_markers: tuple[str, ...] = (),
    ) -> str:
        lines = text.splitlines()
        capture = False
        collected: list[str] = []
        for raw_line in lines:
            stripped = raw_line.strip()
            if not capture:
                if stripped.startswith(header):
                    capture = True
                continue
            if stop_markers and any(marker in stripped for marker in stop_markers):
                break
            collected.append(raw_line.rstrip())
        return "\n".join(collected).strip()

    @staticmethod
    def _extract_bullets(text: str, header: str) -> list[str]:
        lines = text.splitlines()
        capture = False
        bullets: list[str] = []
        for raw_line in lines:
            stripped = raw_line.strip()
            if not capture:
                if stripped.startswith(header):
                    capture = True
                continue
            if not stripped:
                break
            if stripped.startswith("-") or stripped.startswith("•"):
                bullet = stripped.lstrip("-• ").strip()
                if bullet:
                    bullets.append(bullet)
            elif bullets:
                bullets[-1] = f"{bullets[-1]} {stripped}".strip()
        return LLMClient._dedupe(bullets)

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        fragments = re.split(r"(?<=[.!?])\s+", text.strip()) if text else []
        return [fragment.strip() for fragment in fragments if fragment.strip()]

    @staticmethod
    def _dedupe(items: Iterable[Any]) -> list[Any]:
        seen: set[Any] = set()
        result: list[Any] = []
        for item in items:
            marker = json.dumps(item, sort_keys=True) if isinstance(item, (dict, list)) else item
            if marker in seen:
                continue
            seen.add(marker)
            result.append(item)
        return result

    @staticmethod
    def _natural_join(items: Iterable[str]) -> str:
        values = [item.strip().rstrip(".") for item in items if item.strip()]
        if not values:
            return ""
        if len(values) == 1:
            return values[0]
        if len(values) == 2:
            return " and ".join(values)
        return ", ".join(values[:-1]) + ", and " + values[-1]


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
