# Agentic Enhancements for Themis Framework

**Document Version:** 1.0
**Last Updated:** 2025-10-26
**Status:** Production Ready

This document describes the advanced agentic capabilities integrated into Themis Framework, leveraging cutting-edge features from Anthropic's Claude API (2025).

## Table of Contents

- [Overview](#overview)
- [Extended Thinking Mode](#extended-thinking-mode)
- [1-Hour Prompt Caching](#1-hour-prompt-caching)
- [Code Execution Tool](#code-execution-tool)
- [Files API](#files-api)
- [MCP Connector](#mcp-connector)
- [CLAUDE.md Documentation](#claudemd-documentation)
- [Custom Slash Commands](#custom-slash-commands)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Cost Optimization](#cost-optimization)
- [Troubleshooting](#troubleshooting)

## Overview

Themis has been enhanced with seven major agentic capabilities:

1. **Extended Thinking Mode** - Deeper reasoning for complex legal analysis
2. **1-Hour Prompt Caching** - Up to 90% cost reduction and 85% latency improvement
3. **Code Execution Tool** - Computational analysis for damages and statistics
4. **Files API** - Persistent document management across sessions
5. **MCP Connector** - Integration with external tools and databases
6. **CLAUDE.md** - Automatic context loading for legal domain knowledge
7. **Slash Commands** - Parameterized workflow templates

These enhancements are production-ready and backward-compatible with existing Themis workflows.

## Extended Thinking Mode

### What It Does

Extended thinking enables Claude to generate internal reasoning in "thinking" content blocks before producing responses. This is particularly valuable for:

- Complex multi-issue legal analysis (DEA agent)
- Strategic planning with multiple contingencies (LSA agent)
- Multi-step reasoning between tool calls (interleaved thinking)

### How It Works

When enabled, Claude produces two types of content:
1. **Thinking blocks** - Internal reasoning (logged for observability)
2. **Text blocks** - Final response to the user

With **interleaved thinking**, Claude can reason about tool call results before deciding what to do next.

### Configuration

In `.env`:
```bash
USE_EXTENDED_THINKING=true
```

In code:
```python
from tools.llm_client import LLMClient

client = LLMClient(use_extended_thinking=True)
```

### Use Cases for Themis

| Agent | Use Case | Benefit |
|-------|----------|---------|
| **DEA** | Multi-jurisdiction analysis | Compare conflicting authorities across states |
| **DEA** | Issue spotting | Systematically identify primary, secondary, and tertiary issues |
| **LSA** | Strategy planning | Evaluate multiple negotiation paths with contingencies |
| **LSA** | Risk assessment | Weigh competing factors in settlement decisions |
| **DDA** | Document drafting | Structure complex arguments with proper legal reasoning |

### Cost

Extended thinking uses additional tokens for the internal reasoning blocks. Typical overhead: 20-40% more tokens for complex reasoning tasks.

**Mitigation:** Use extended thinking selectively for complex tasks; disable for simple document parsing.

## 1-Hour Prompt Caching

### What It Does

Caches system prompts and other content for **1 hour** (up from 5 minutes), enabling:

- **90% cost reduction** for repeated agent executions
- **85% latency reduction** for multi-agent workflows
- **Higher throughput** for parallel processing

### How It Works

The LLM client automatically marks system prompts with cache control headers:

```python
request_params["system"] = [{
    "type": "text",
    "text": system_prompt,
    "cache_control": {"type": "ephemeral"}
}]
request_params["extra_headers"] = {
    "anthropic-cache-control": "ephemeral+extended"  # 1-hour TTL
}
```

Subsequent requests with identical system prompts hit the cache instead of re-processing.

### Configuration

In `.env`:
```bash
USE_PROMPT_CACHING=true  # Enabled by default
```

### Use Cases for Themis

1. **Multi-Agent Workflows** - LDA → DEA → LSA → DDA share cached matter context
2. **Batch Processing** - Process multiple similar cases (e.g., 50 PI demand letters)
3. **Practice Pack Runs** - Repeated executions during development/testing
4. **API Endpoints** - Orchestrator endpoints with consistent system prompts

### Cost Savings Example

**Scenario:** Generate 20 demand letters in 1 hour

- **Without caching:** 20 × 10,000 tokens = 200,000 tokens @ $3/MTok = **$0.60**
- **With caching:** (1 × 10,000) + (19 × 100) = 11,900 tokens @ $3/MTok = **$0.04**
- **Savings:** 94% reduction

### Best Practices

1. **Group similar work** - Process batches within 1-hour windows
2. **Consistent prompts** - Avoid unnecessary variations in system prompts
3. **Monitor cache hits** - Check logs for "cache_hit" indicators
4. **Pre-warm cache** - Run initial request before batch processing

## Code Execution Tool

### What It Does

Enables Claude to execute Python code in a sandboxed environment for:

- **Damages calculations** - Sum economic losses, project future earnings
- **Statistical analysis** - Analyze timelines, identify patterns
- **Financial modeling** - Settlement ranges, present value calculations
- **Data processing** - Parse complex documents, extract structured data

### How It Works

The LLM client enables the code execution tool in API requests:

```python
request_params["tools"] = [{
    "type": "code_execution_2025_04_01",
    "name": "python"
}]
```

Claude can now write and execute Python code to solve computational problems.

### Configuration

In `.env`:
```bash
ENABLE_CODE_EXECUTION=false  # Enable when needed for LDA
```

In LDA agent:
```python
agent = LDAAgent(enable_code_execution=True)
```

### Use Cases for Themis

#### 1. Damages Calculator (LDA Agent)

Replaces stub calculations with actual Python computation:

```python
# Economic damages
medical_bills = 45000
lost_wages = 120000
future_earnings_loss = 250000
economic_total = medical_bills + lost_wages + future_earnings_loss

# Present value calculation
import numpy as np
discount_rate = 0.03
years = 20
pv_future_losses = future_earnings_loss * (1 - (1 + discount_rate)**-years) / discount_rate

# Settlement range (60-80% of total)
grand_total = economic_total + pv_future_losses
settlement_range = (grand_total * 0.6, grand_total * 0.8)
```

#### 2. Timeline Analyzer (LDA Agent)

Statistical analysis of event patterns:

```python
from datetime import datetime, timedelta

events = [...]  # List of timeline events
dates = [datetime.fromisoformat(e['date']) for e in events]
dates.sort()

# Calculate gaps
gaps = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
avg_gap = sum(gaps) / len(gaps)
max_gap = max(gaps)

# Identify clusters (3+ events within 14 days)
clusters = []
for i, date in enumerate(dates):
    window = [d for d in dates if abs((d - date).days) <= 14]
    if len(window) >= 3:
        clusters.append({'date': date, 'count': len(window)})
```

### Cost

- **Free tier:** 50 hours per day per workspace
- **Overage:** $0.05 per hour per container
- **Typical usage:** 1-5 minutes per LDA run = $0.004-$0.020

### Safety

Code execution runs in a sandboxed environment with:
- No network access
- Limited memory and CPU
- 60-second timeout per execution
- No file system persistence

## Files API

### What It Does

Upload documents once and reference them across multiple API calls:

- **Persistent storage** - Files remain available across sessions
- **Reduced overhead** - No need to re-upload with each request
- **Cross-agent sharing** - All agents can access uploaded documents

### How It Works

Upload files via the LLM client:

```python
from tools.llm_client import get_llm_client

client = get_llm_client()

# Upload a case document
file_id = client.upload_file("path/to/case_document.pdf")

# Reference in subsequent requests
response = await client.generate_text(
    system_prompt="Analyze this case document",
    user_prompt="Extract key facts",
    file_ids=[file_id]
)
```

### Use Cases for Themis

1. **Multi-Agent Workflows** - Upload case documents once, share across LDA/DEA/LSA
2. **Session Persistence** - Resume analysis across multiple orchestrator runs
3. **Document Libraries** - Maintain a library of template documents, forms, statutes
4. **Large Document Sets** - Process 50+ page pleadings without payload limits

### Management

```python
# List all uploaded files
files = client.list_files()
for f in files:
    print(f"{f['id']}: {f['filename']} (uploaded {f['created_at']})")

# Delete old files
client.delete_file(file_id)
```

### Cost

Files API storage is included in standard API pricing. No additional charges.

## MCP Connector

### What It Does

Connect to **Model Context Protocol (MCP)** servers for external tool integration:

- Legal research databases (Westlaw, LexisNexis)
- Document repositories (Box, SharePoint, OneDrive)
- Case management systems (Clio, MyCase)
- Workflow automation (Zapier, Make)

### Configuration

Create `.mcp.json` in project root:

```json
{
  "servers": {
    "legal-research": {
      "url": "${LEGAL_RESEARCH_MCP_URL}",
      "api_key": "${LEGAL_RESEARCH_API_KEY}",
      "enabled": true,
      "description": "Legal research database"
    }
  }
}
```

Set environment variables in `.env`:

```bash
LEGAL_RESEARCH_MCP_URL=https://api.legaldb.example.com/mcp
LEGAL_RESEARCH_API_KEY=your-api-key
```

### Usage

Load MCP configuration and pass to LLM client:

```python
from tools.mcp_config import get_mcp_config
from tools.llm_client import get_llm_client

mcp_config = get_mcp_config()
mcp_servers = mcp_config.get_enabled_servers()

client = get_llm_client()
response = await client.generate_with_mcp(
    system_prompt="You are a legal research assistant",
    user_prompt="Find cases on negligence in California",
    mcp_servers=mcp_servers
)
```

### Available Integrations

| Category | Examples | Use Case |
|----------|----------|----------|
| **Legal Research** | Westlaw, LexisNexis, Fastcase | Cite checking, case law research |
| **Document Mgmt** | Box, SharePoint, Dropbox | Template libraries, case files |
| **Case Mgmt** | Clio, MyCase, PracticePanther | Deadline tracking, client data |
| **Workflow** | Zapier, Make, n8n | Automated notifications, integrations |
| **Web Scraping** | Puppeteer MCP server | Court docket monitoring, filing checks |

### Building Custom MCP Servers

See MCP documentation: https://modelcontextprotocol.io/

Example MCP server for jurisdiction-specific rules:

```python
# mcp_server.py - Jurisdiction rules MCP server
from mcp import MCPServer

server = MCPServer()

@server.tool("get_statute_of_limitations")
async def get_sol(jurisdiction: str, claim_type: str) -> dict:
    # Return SOL for jurisdiction + claim type
    return {"jurisdiction": jurisdiction, "claim_type": claim_type, "sol_years": 2}
```

## CLAUDE.md Documentation

### What It Does

Special markdown file that Claude automatically loads into context on every interaction. Contains:

- Legal domain knowledge (citation formats, standards)
- Development guidelines (testing, code style)
- Tool documentation (bash commands, scripts)
- Practice pack instructions

### Location

Place `CLAUDE.md` at project root: `/home/user/themis-framework/CLAUDE.md`

### Benefits

1. **Consistent Context** - Every Claude session has legal domain knowledge
2. **Reduced Prompting** - No need to repeat instructions
3. **Team Alignment** - Standardized practices across developers
4. **Onboarding** - New team members see guidelines automatically

### What's Included in Themis CLAUDE.md

- Agent architecture overview
- Legal analysis principles (IRAC, Bluebook citations)
- Development commands (testing, linting)
- Tool system documentation
- Stub mode explanation
- Practice pack development guide

## Custom Slash Commands

### What It Does

Parameterized prompt templates stored in `.claude/commands/` directory. Execute with `/command-name arguments`.

### Available Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `/analyze-case` | Full case analysis workflow | `/analyze-case path/to/matter.json` |
| `/generate-demand` | Create demand letter for PI case | `/generate-demand packs/fixtures/case.json` |
| `/run-tests` | Execute test suite | `/run-tests agents` |
| `/review-code` | Perform code review | `/review-code agents/lda.py` |
| `/create-pack` | Generate new practice pack | `/create-pack employment_law` |

### Creating Custom Commands

Create `.claude/commands/my-command.md`:

```markdown
---
description: Short description of command
---

Command prompt template here.

Use $ARGUMENTS for parameterization:

Process the matter at: $ARGUMENTS

Steps:
1. Load matter
2. Run analysis
3. Generate output
```

Usage: `/my-command path/to/file`

## Configuration

### Environment Variables

See `.env.example` for complete configuration options.

**Key settings:**

```bash
# Enable/disable features
USE_EXTENDED_THINKING=true        # Extended thinking mode
USE_PROMPT_CACHING=true            # 1-hour prompt caching
ENABLE_CODE_EXECUTION=false        # Code execution tool

# Model selection
MODEL=claude-3-5-sonnet-20241022   # Claude model version

# MCP integration
LEGAL_RESEARCH_MCP_URL=...         # MCP server URLs
LEGAL_RESEARCH_API_KEY=...         # MCP API keys
```

### Programmatic Configuration

Override defaults in code:

```python
from tools.llm_client import LLMClient

# Custom configuration
client = LLMClient(
    model="claude-sonnet-4-5",
    use_extended_thinking=True,
    use_prompt_caching=True,
    enable_code_execution=True
)

# Use for specific agent
from agents.lda import LDAAgent

lda = LDAAgent(enable_code_execution=True)
lda.tools["llm_client"] = client
```

## Usage Examples

### Example 1: Demand Letter with Code Execution

```python
from packs.personal_injury.run import main
import asyncio

# Enable code execution for damages calculation
import os
os.environ["ENABLE_CODE_EXECUTION"] = "true"

# Run personal injury pack
asyncio.run(main("packs/personal_injury/fixtures/sample_matter.json"))
```

Output includes:
- Computed damages with present value calculations
- Timeline analysis with gap detection
- Settlement range recommendations

### Example 2: Multi-Case Batch Processing with Caching

```python
from orchestrator.service import OrchestratorService
import asyncio

async def process_batch(matter_files):
    service = OrchestratorService()

    results = []
    for matter_file in matter_files:
        # Subsequent runs hit 1-hour cache
        result = await service.execute(matter_file)
        results.append(result)

    return results

# Process 50 similar PI cases - 94% cost reduction via caching
matters = [f"case_{i}.json" for i in range(50)]
asyncio.run(process_batch(matters))
```

### Example 3: MCP-Enabled Legal Research

```python
from tools.mcp_config import get_mcp_config
from tools.llm_client import get_llm_client

async def research_case_law(query: str):
    mcp_config = get_mcp_config()
    mcp_servers = mcp_config.get_enabled_servers()

    client = get_llm_client()
    response = await client.generate_with_mcp(
        system_prompt="You are a legal research assistant with access to case law databases.",
        user_prompt=f"Research: {query}",
        mcp_servers=mcp_servers
    )

    return response

result = asyncio.run(research_case_law(
    "California negligence cases involving premises liability 2020-2024"
))
```

## Cost Optimization

### Recommendations

| Feature | Cost Impact | When to Enable |
|---------|-------------|----------------|
| **Extended Thinking** | +20-40% tokens | Complex reasoning only (DEA/LSA) |
| **Prompt Caching** | -90% costs | Always (default on) |
| **Code Execution** | +$0.004-$0.02/run | When computational accuracy needed |
| **Files API** | No extra cost | Multi-session workflows |
| **MCP Connector** | Varies by provider | External integrations needed |

### Best Practices

1. **Batch processing** - Group similar work within 1-hour windows for cache hits
2. **Selective thinking** - Enable extended thinking only for complex DEA/LSA tasks
3. **Code execution on-demand** - Enable only for LDA when damages calculations needed
4. **Monitor usage** - Track token consumption and cache hit rates
5. **Use stub mode** - Develop without API costs using stub mode (no API key)

### Cost Tracking

Themis includes cost tracking middleware:

```bash
# View cost metrics
curl http://localhost:8000/metrics | grep themis_llm_cost

# Check application logs for per-request costs
grep cost_estimate /var/log/themis/app.log
```

## Troubleshooting

### Extended Thinking Not Working

**Symptom:** No thinking blocks in responses

**Solution:**
1. Check `.env`: `USE_EXTENDED_THINKING=true`
2. Verify model supports thinking: `claude-opus-4` or `claude-sonnet-4` required
3. Check API headers: `anthropic-beta: interleaved-thinking-2025-05-14`

### Cache Not Hitting

**Symptom:** High costs despite prompt caching enabled

**Solution:**
1. Verify system prompt is identical across requests
2. Check cache TTL hasn't expired (1 hour)
3. Ensure `USE_PROMPT_CACHING=true` in `.env`
4. Look for "cache_hit" in debug logs

### Code Execution Timeout

**Symptom:** Code execution fails with timeout error

**Solution:**
1. Simplify computational logic
2. Avoid infinite loops
3. Reduce data set size
4. Check 60-second timeout limit

### MCP Server Connection Failed

**Symptom:** MCP requests fail with connection errors

**Solution:**
1. Verify MCP server URL is correct
2. Check API key is valid
3. Ensure `enabled: true` in `.mcp.json`
4. Test MCP server independently: `curl $MCP_URL/health`

### File Upload Failed

**Symptom:** File upload returns error

**Solution:**
1. Check file size (max 10MB)
2. Verify API key is set
3. Ensure file path is correct
4. Check file permissions

## References

- **Anthropic Agent Capabilities**: https://www.anthropic.com/news/agent-capabilities-api
- **Extended Thinking**: https://docs.claude.com/en/docs/build-with-claude/extended-thinking
- **Model Context Protocol**: https://modelcontextprotocol.io/
- **Claude Code Best Practices**: https://www.anthropic.com/engineering/claude-code-best-practices
- **Themis Documentation**: `docs/` directory

## Support

For issues or questions:
- GitHub Issues: https://github.com/themis-agentic-system/themis-framework/issues
- Documentation: See `docs/` directory
- CLAUDE.md: Project-specific guidelines at root

---

**Last Updated:** 2025-10-26
**Version:** 1.0
**Status:** Production Ready ✅
