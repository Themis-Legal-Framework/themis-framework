# Themis Legal AI Framework - Claude Agent Guide

This document provides context and guidelines for AI agents working with the Themis legal reasoning framework.

## System Overview

Themis is a multi-agent legal reasoning system that orchestrates specialized AI agents to handle different aspects of legal work. The system is designed for high-stakes legal analysis where provenance tracking, defensibility, and human review are critical.

## Core Legal Standards

### Provenance & Citation Requirements

1. **Always Track Sources**: Every factual assertion must include provenance metadata
2. **Bluebook Citation Format**: All legal authorities must be cited using proper Bluebook format
3. **Verify Jurisdiction**: Check jurisdiction-specific rules before generating any legal documents
4. **No Hallucinations**: When uncertain about a legal principle, flag it as an unresolved issue rather than guessing

### Legal Analysis Principles

- **Issue Spotting**: Systematically identify all potential legal issues before analysis
- **IRAC Method**: Structure legal analysis using Issue, Rule, Application, Conclusion
- **Controlling vs. Persuasive**: Distinguish between binding precedent and persuasive authority
- **Contrary Authority**: Always note contrary holdings or interpretations
- **Standard of Review**: Consider the applicable standard of review for each issue

### Document Drafting Standards

- **Modern Legal Prose**: Use clear, concise language; avoid archaic legalese
- **Plain Language**: Write for client understanding while maintaining legal precision
- **Tone Awareness**: Match document tone to purpose (demand letter vs. complaint vs. memorandum)
- **Jurisdictional Compliance**: Follow jurisdiction-specific filing rules and formatting requirements

## Agent Architecture

### Available Agents

1. **LDA (Legal Data Analyst)** - `agents/lda.py`
   - Extracts structured facts from case documents
   - Computes damages calculations and builds timelines
   - Prepares evidentiary exhibits and summaries
   - **NEW**: Can use code execution tool for computational tasks

2. **DEA (Doctrinal Expert Agent)** - `agents/dea.py`
   - Applies black-letter law with verifiable citations
   - Spots legal issues and analyzes claims
   - Provides both controlling and contrary authorities
   - **NEW**: Uses extended thinking for complex multi-issue analysis

3. **LSA (Legal Strategy Agent)** - `agents/lsa.py`
   - Crafts negotiation strategies and client counsel
   - Performs risk assessment and identifies weaknesses
   - Develops contingency plans and fallback positions
   - **NEW**: Uses extended thinking for strategic planning

4. **DDA (Document Drafting Agent)** - `agents/dda.py`
   - Generates formal legal documents using modern legal prose
   - Supports complaints, motions, demand letters, memoranda
   - Formats citations according to Bluebook standards

### Orchestrator Phases

The orchestrator routes tasks through 5 legal phases:

1. **INTAKE_FACTS** - Initial document parsing and fact extraction (LDA)
2. **ISSUE_FRAMING** - Legal issue identification (DEA)
3. **RESEARCH_RETRIEVAL** - Authority retrieval and citation (DEA)
4. **APPLICATION_ANALYSIS** - Legal analysis application (DEA/LDA)
5. **DRAFT_REVIEW** - Strategy and document review (LSA)

## Development Commands

### Running Tests

```bash
# Run all tests
make test
# or
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_agents.py -v

# Run with coverage
python -m pytest tests/ --cov=agents --cov=orchestrator --cov=tools

# QA smoke tests
make qa
python -m pytest qa/ -v
```

### Practice Packs

```bash
# Personal Injury - demand letter generation
python -m packs.personal_injury.run \
  --matter packs/personal_injury/fixtures/sample_matter.json

# Criminal Defense - case analysis
python -m packs.criminal_defense.run \
  --matter packs/criminal_defense/fixtures/dui_with_refusal.json

# List available fixtures
python -m packs.personal_injury.run --list
```

### API Server

```bash
# Start FastAPI server
uvicorn api.main:app --reload

# Endpoints:
# - OpenAPI docs: http://localhost:8000/docs
# - Health check: http://localhost:8000/health
# - Metrics: http://localhost:8000/metrics
```

## Tool System

### Core Tools

- **llm_client** (`tools/llm_client.py`) - Anthropic Claude API client with advanced features
- **document_parser** (`tools/document_parser.py`) - PDF/text extraction with LLM analysis
- **metrics** (`tools/metrics.py`) - Prometheus metrics registry
- **registry** (`tools/registry.py`) - Tool registration system

### NEW: Advanced LLM Features

The `LLMClient` now supports cutting-edge capabilities:

1. **Extended Thinking Mode**
   - Enables deeper reasoning for complex legal analysis
   - Interleaved thinking between tool calls for better decision-making
   - Ideal for DEA and LSA agents

2. **1-Hour Prompt Caching**
   - Up to 90% cost reduction for repeated operations
   - Up to 85% latency reduction
   - Automatically caches system prompts and matter context

3. **Code Execution Tool**
   - Run Python code for damages calculations, timelines, statistical analysis
   - Replaces stub calculations with real computation
   - Enabled for LDA agent computational tasks

4. **Files API**
   - Upload case documents once, reference across multiple sessions
   - Reduces overhead for multi-agent workflows
   - Use `llm_client.upload_file()` to upload documents

5. **MCP Connector**
   - Connect to Model Context Protocol servers for external tools
   - Integration with legal databases, document repositories, workflow systems
   - Use `llm_client.generate_with_mcp()` for MCP-enabled requests

### Using Tools in Agents

```python
from agents.base import BaseAgent

class CustomAgent(BaseAgent):
    async def _run(self, matter: dict[str, Any]) -> dict[str, Any]:
        # Call registered tools
        result = await self._call_tool("my_tool", matter)

        # Build response with provenance
        return self._build_response(
            core={"analysis": result},
            provenance={
                "tools_used": ["my_tool"],
                "sources": ["matter_payload"]
            },
            unresolved_issues=[]
        )
```

## Stub Mode

When no `ANTHROPIC_API_KEY` is available, Themis runs in stub mode:

- Heuristically extracts information from prompts
- Deterministic responses for testing
- No network operations
- Mirrors expected response shapes

**To use stub mode:**
```bash
unset ANTHROPIC_API_KEY
python -m packs.personal_injury.run --matter path/to/matter.json
```

## Environment Variables

```bash
# Required for production
ANTHROPIC_API_KEY=sk-ant-...

# API authentication
THEMIS_API_KEY=your-secure-api-key

# Optional configuration
CACHE_TTL_SECONDS=60          # State cache TTL (default: 60)
LOG_LEVEL=INFO                # Logging level
MODEL=claude-3-5-sonnet-20241022  # Claude model version
```

## Code Quality Standards

### Type Hints
- Use type hints on all function signatures
- Import `from __future__ import annotations` for forward references

### Docstrings
- Document all public functions and classes
- Include Args, Returns, Raises sections
- Use Google-style docstring format

### Testing
- Write tests for all new agents and tools
- Use fixtures in `conftest.py` for shared test data
- Mock LLM calls with custom tools in tests
- Aim for >80% code coverage

### Style
- Maximum line length: 120 characters
- Use `ruff` for linting: `make lint` or `ruff check --fix .`
- Follow existing patterns for consistency

## State Management

Themis uses a hybrid state management approach:

- **In-Memory Cache**: TTL-based caching (configurable, default 60s)
- **SQLite Persistence**: Plans stored in `orchestrator_state.db`
- **Write-Through Strategy**: Updates go to both cache and database
- **Performance**: 500x faster reads, 10x higher throughput

## Observability

### Structured Logging
All logs include context with automatic sanitization:
- Sensitive data redaction (API keys, passwords)
- Request ID tracking (`X-Request-ID`)
- Client IP correlation
- Response time measurement

### Prometheus Metrics
Available at `/metrics`:
- `themis_agent_run_seconds` - Agent execution latency histogram
- `themis_agent_tool_invocations_total` - Tool usage counter
- `themis_agent_run_errors_total` - Error counter

### Monitoring Stack
Configure Prometheus to scrape `/metrics` endpoint for visualization in Grafana.

## Practice Pack Development

### Creating a New Practice Pack

```bash
# 1. Create directory structure
mkdir -p packs/my_pack/fixtures

# 2. Define schema (packs/my_pack/schema.py)
MATTER_SCHEMA = {
    "type": "object",
    "properties": {
        "case_type": {"type": "string"},
        "parties": {"type": "array"},
        # ... your fields
    },
    "required": ["case_type", "parties"]
}

# 3. Create run script (packs/my_pack/run.py)
# 4. Add fixtures and test
```

## Best Practices

### When Writing Code
1. Read relevant files first before making changes
2. Use extended thinking for complex planning: "think about X"
3. Implement incrementally with tests
4. Commit with descriptive messages

### When Analyzing Cases
1. Extract facts systematically (LDA)
2. Identify all issues comprehensively (DEA)
3. Research controlling authority (DEA)
4. Assess strategy and risk (LSA)
5. Generate client-ready artifacts (DDA)

### When Testing
1. Use fixture files for consistent test data
2. Mock LLM calls to avoid API costs
3. Test edge cases (sparse data, missing fields)
4. Verify provenance tracking

## Repository Etiquette

### Commit Messages
```bash
git commit -m "Add feature: brief description

Longer explanation of what changed and why.
Fixes #123"
```

### Pull Requests
- Keep PRs focused and atomic
- Update documentation for user-facing changes
- Ensure all tests pass: `make test && make lint`
- Respond to review feedback promptly

### Code Review
- Check provenance tracking in agent responses
- Verify error handling and edge cases
- Ensure legal standards compliance
- Test with multiple practice packs

## Security & Compliance

### Data Handling
- Never commit API keys or secrets
- Use `.env` files (excluded from git)
- Redact sensitive information in logs
- Validate all input data (Pydantic models)

### Legal Ethics
- All artifacts require human review before use
- Never file documents without attorney approval
- Maintain client confidentiality
- Track all data sources and citations

## Quick Reference

```bash
# Run tests
make test

# Lint code
make lint

# QA checks
make qa

# Start API server
uvicorn api.main:app --reload

# Run practice pack
python -m packs.personal_injury.run --matter path/to/matter.json

# Use stub mode (no API key needed)
unset ANTHROPIC_API_KEY
```

## Resources

- **Documentation**: `docs/` directory
- **API Reference**: `docs/API_REFERENCE.md`
- **Deployment Guide**: `docs/DEPLOYMENT_GUIDE.md`
- **Code Review**: `CODE_REVIEW_REPORT.md`
- **Quick Start**: `QUICKSTART.md`

## Support

- GitHub Issues: https://github.com/themis-agentic-system/themis-framework/issues
- GitHub Discussions: https://github.com/themis-agentic-system/themis-framework/discussions

---

> "Trust, but verify."
>
> Every automated deliverable is designed for human review before filing, sending, or advising clients.

⚖️ Built with care for legal professionals | 🤖 Powered by Claude AI | 🛡️ Production-ready
