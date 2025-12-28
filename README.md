Themis Framework
================

An open framework for building multi-agent legal reasoning systems that blend data analysis, doctrinal expertise, and strategic counsel under a unified orchestrator.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) ![Themis Status](https://img.shields.io/badge/status-beta-blue) ![Tests](https://img.shields.io/badge/tests-203-4caf50) ![Docker](https://img.shields.io/badge/docker-ready-0db7ed) ![Python](https://img.shields.io/badge/python-3.10%2B-3776ab)

Table of Contents
-----------------
- [Why Themis?](#why-themis)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Quick Start](#quick-start)
- [Usage Examples](#usage-examples)
- [Practice Packs](#practice-packs)
- [Development Guide](#development-guide)
- [Observability & Metrics](#observability--metrics)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)

Why Themis?
-----------
Modern legal work blends facts + law + strategy. Themis models this as a crew of specialist AI agents working together:

### 🤖 The Agent Team

**LDA (Legal Data Analyst) 📊**

- Parses case documents and extracts structured facts
- Computes damages calculations and builds timelines
- Prepares evidentiary exhibits and summaries
- Identifies missing information and data gaps
- **NEW (2025):** Uses code execution tool for computational tasks (damages calculations, timeline analysis)

**DEA (Doctrinal Expert Agent) ⚖️**

- Applies black-letter law with verifiable citations
- Spots legal issues and analyzes claims
- Guards against hallucinations with source tracking
- Provides both controlling and contrary authorities
- **NEW (2025):** Uses extended thinking for complex multi-issue analysis

**LSA (Legal Strategy Agent) 🎯**

- Crafts negotiation strategies and client counsel
- Drafts client-facing documents with appropriate tone
- Performs risk assessment and identifies weaknesses
- Develops contingency plans and fallback positions
- **NEW (2025):** Uses extended thinking for strategic planning

**DDA (Document Drafting Agent) ✍️**

- Generates formal legal documents using modern legal prose
- Supports complaints, motions, demand letters, and memoranda
- Formats citations according to Bluebook and jurisdiction standards
- Validates document completeness and analyzes tone quality
- Ensures plain language and accessibility standards
- **Note:** Fully implemented but integration with default routing policy is in progress

**Orchestrator 🎼**

- Routes tasks to the right specialist agent across 5 legal phases:
  1. **INTAKE_FACTS** - Initial document parsing and fact extraction (LDA)
  2. **ISSUE_FRAMING** - Legal issue identification (DEA)
  3. **RESEARCH_RETRIEVAL** - Authority retrieval and citation (DEA)
  4. **APPLICATION_ANALYSIS** - Legal analysis application (DEA/LDA)
  5. **DRAFT_REVIEW** - Strategy and document review (LSA)
- Maintains shared memory across the workflow with state persistence
- Performs reflection (consistency checks, citation verification)
- Assembles final deliverables ready for human review
- Builds task graphs (DAGs) with topological ordering for execution

### 🛡️ Built for High-Stakes Legal Work
Themis draws inspiration from multi-agent healthcare systems and adapts the approach for high-stakes legal reasoning where:

- Provenance is tracked for every fact and citation
- Defensibility is ensured through structured validation
- Human review is the final step before any client communication

Key Features
------------
### 🚀 Agentic Enhancements (2025)
NEW: 7 cutting-edge capabilities from Anthropic's 2025 API features:

- **Extended Thinking Mode** – Deeper reasoning for complex legal analysis with interleaved thinking
- **1-Hour Prompt Caching** – Up to 90% cost reduction and 85% latency improvement
- **Code Execution Tool** – Python code execution for damages calculations, timelines, and statistical analysis
- **Files API** – Upload case documents once, reference across multiple sessions
- **MCP Connector** – Integration with Model Context Protocol servers for external tools
- **CLAUDE.md** – Automatic context loading with legal domain knowledge and team guidelines
- **Slash Commands** – Parameterized workflow templates (6 built-in commands)

See `docs/AGENTIC_ENHANCEMENTS.md` for complete guide and `TEST_RESULTS.md` for verification (26/26 tests passing).

### Production-Ready Infrastructure
- ✅ Docker Deployment – Complete stack with PostgreSQL, Prometheus, and Grafana
- ✅ Authentication & Security – API key auth with rotation support, rate limiting (10-60 req/min), audit logging
- ✅ Performance Optimized – SQLite + in-memory state caching (TTL-based) provides 500x faster reads and 10x higher throughput
- ✅ Comprehensive Testing – 203 tests across all components
- ✅ Type Safety – Pydantic models for Matter, Document, Event, Issue, Authority with validation
- ✅ Circuit Breaker – Prevents cascading failures with configurable thresholds and automatic recovery

### Intelligent Agent System
- 🤖 LLM-Powered Agents – Claude 3.5 Sonnet integration with structured outputs and extended thinking
- 🔄 Automatic Retry Logic – Configurable retry policies with exponential backoff, jitter, and re-execution support
- 🎯 Smart Routing – Phase-based orchestration with signal propagation and task graphs
- 📝 Stub Mode – Run without API keys using heuristic fallback generation for testing and development
- ⚡ Async Execution – Background job processing with webhook callbacks and status polling

### Observability & Monitoring
- 📊 Prometheus Metrics – Agent latency, tool invocations, error rates
- 📝 Structured Logging – JSON logs with request tracking, context, and request IDs
- 💰 Cost Tracking – LLM API usage estimation middleware
- 🔍 Audit Trail – Security-critical operation logging with client IP tracking
- 🛡️ Request Middleware – Logging, audit, cost tracking, payload size limiting (10MB max)

### Developer Experience
- 📚 Comprehensive Documentation – 5 detailed guides covering deployment to code review
- 🧪 Practice Packs – Pre-built workflows for Personal Injury and Criminal Defense
- 🔧 Extensible Design – Tool injection, custom agents, and practice pack templates
- 🐳 Docker Ready – Multi-stage builds optimized for production

System Architecture
-------------------
### Directory Structure
```
themis-framework/
├── agents/                 # 🤖 Specialist agents (LDA, DEA, LSA, DDA)
│   ├── base.py            # Base agent with metrics, logging, tool invocation
│   ├── constants.py       # Centralized configuration constants
│   ├── tooling.py         # Tool specification and registration
│   ├── lda.py             # Legal Data Analyst (facts, timelines, damages)
│   ├── dea.py             # Doctrinal Expert (legal analysis, citations)
│   ├── lsa.py             # Legal Strategist (strategy, risk assessment)
│   ├── dda.py             # Document Drafting Agent (formal legal documents)
│   └── dda_tools.py       # DDA tool implementations (section generation, validation)
│
├── orchestrator/          # 🎼 Agent coordination and workflow management
│   ├── main.py            # Simple sequential orchestrator
│   ├── service.py         # Production service with state management
│   ├── policy.py          # Routing policy and phase definitions
│   ├── router.py          # FastAPI routes for orchestration
│   ├── state.py           # State management abstractions
│   ├── models.py          # Pydantic models for type safety
│   ├── exceptions.py      # Custom exception hierarchy
│   ├── validation.py      # Input validation layer
│   ├── task_graph.py      # DAG-based task execution
│   ├── tracing.py         # Execution tracing and observability
│   ├── document_type_detector.py  # Auto-detection of document types
│   └── storage/           # State persistence (SQLite with TTL caching)
│
├── api/                   # 🌐 FastAPI REST interface
│   ├── main.py            # Application setup, middleware, routes
│   ├── security.py        # API key authentication
│   ├── middleware.py      # Logging, cost tracking, audit middleware
│   └── logging_config.py  # Structured logging configuration
│
├── tools/                 # 🔧 Utilities and integrations
│   ├── llm_client.py      # Anthropic Claude client (production mode)
│   ├── stub_llm_client.py # Stub LLM handler for testing without API keys
│   ├── mcp_config.py      # Model Context Protocol configuration manager
│   ├── document_parser.py # PDF/text extraction with LLM analysis
│   ├── metrics.py         # Prometheus metrics registry
│   └── registry.py        # Tool registration system
│
├── packs/                 # 📦 Practice area workflows
│   ├── personal_injury/   # Personal injury practice pack (intake through trial)
│   │   ├── run.py         # CLI and workflow orchestration
│   │   ├── schema.py      # Matter validation schema
│   │   ├── complaint_generator.py  # Jurisdiction-specific complaints
│   │   ├── jurisdictions.py        # State-specific rules
│   │   └── fixtures/      # Sample matters for testing
│   │
│   └── criminal_defense/  # Criminal defense workflows
│       ├── run.py         # CLI and workflow orchestration
│       ├── schema.py      # Criminal matter schema
│       └── fixtures/      # Sample criminal matters
│
├── tests/                 # 🧪 Comprehensive test suite (35 tests)
│   ├── test_agents.py     # Agent functionality tests
│   ├── test_metrics.py    # Metrics collection tests
│   ├── test_edge_cases.py # Edge case handling
│   ├── test_error_handling.py  # Error scenarios
│   ├── test_integration.py     # Full workflow tests
│   ├── orchestrator/      # Orchestrator component tests
│   └── packs/             # Practice pack integration tests
│
├── docs/                  # 📚 Technical documentation
│   ├── AGENTIC_ENHANCEMENTS.md  # Complete guide to 2025 agentic features
│   ├── API_REFERENCE.md         # API endpoint documentation
│   ├── CODE_REVIEW_REPORT.md    # Comprehensive code review
│   ├── DEPLOYMENT_GUIDE.md      # Production deployment
│   ├── DOCKER_README.md         # Docker quick reference
│   ├── IMPLEMENTATION_SUMMARY.md # Technical implementation details
│   ├── IMPROVEMENTS.md          # Production features overview
│   ├── REDEPLOY.md              # Redeployment procedures
│   ├── REVIEW_FINDINGS.md       # Detailed review findings
│   ├── SECURITY_IMPROVEMENTS.md # Security enhancements
│   ├── TEST_RESULTS.md          # Test verification report
│   └── THEMIS_CODE_REVIEW.md    # Original code review
│
├── .claude/               # 🤖 NEW: Claude Code integration
│   └── commands/          # Slash command workflow templates
│       ├── analyze-case.md       # Full case analysis workflow
│       ├── create-pack.md        # New practice pack boilerplate
│       ├── deploy-docker.md      # Docker stack deployment
│       ├── generate-demand.md    # PI demand letter generation
│       ├── review-code.md        # Code review checklist
│       └── run-tests.md          # Test suite execution
│
├── infra/                 # 🏗️ Infrastructure configuration
│   ├── init-db.sql        # PostgreSQL initialization
│   └── prometheus.yml     # Metrics collection config
│
├── qa/                    # ✅ Quality assurance tests
│   └── test_smoke.py      # Module import tests
│
├── QUICKSTART.md          # 🚀 Quick start guide
├── CLAUDE.md              # 🤖 Agent guide with legal domain knowledge
├── README.md              # 📖 This file
├── Dockerfile             # 🐳 Production container build
├── docker-compose.yml     # 🐳 Full deployment stack
├── pyproject.toml         # 📦 Python dependencies
├── Makefile               # 🛠️ Development commands
├── .env.example           # ⚙️ Environment template (includes new agentic features)
├── .env.docker            # ⚙️ Docker environment template
└── .mcp.json              # 🔌 NEW: MCP server configuration template
```

### Agent Workflow
```
┌─────────────────────────────────────────────────────────────┐
│                         User Request                         │
│                    (Matter Payload)                          │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Orchestrator (Planning)                     │
│  • Builds task graph (DAG) with 6 phases                     │
│  • Routes to primary agent per phase based on intent         │
│  • Assigns supporting agents for cross-validation            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     Phase Execution                          │
│                                                              │
│  ┌──────────────────┐    ┌──────────────────┐               │
│  │ 1. INTAKE_FACTS  │───>│ 2. ISSUE_FRAMING │               │
│  │    (LDA)         │    │    (DEA/LDA)     │               │
│  └──────────────────┘    └────────┬─────────┘               │
│                                   │                          │
│  ┌──────────────────┐    ┌───────▼──────────┐               │
│  │ 4. APPLICATION   │<───│ 3. RESEARCH      │               │
│  │    (DEA/LDA)     │    │    (DEA)         │               │
│  └────────┬─────────┘    └──────────────────┘               │
│           │                                                  │
│  ┌────────▼─────────┐    ┌──────────────────┐               │
│  │ 5. DRAFT_REVIEW  │───>│ 6. DOC_ASSEMBLY  │               │
│  │    (LSA)         │    │    (DDA)         │               │
│  └──────────────────┘    └──────────────────┘               │
│                                                              │
│  Each phase: Primary agent + Supporting agents               │
│  Signal propagation between phases                           │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
           ┌────────────────────────────────────────────────────┐
           │              Exit Condition Checks                  │
           │  • Validates required signals present               │
           │  • Marks steps as attention_required if missing     │
           │  • Aggregates artifacts from all phases             │
           └──────────────────────────┬─────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────┐
│     Human Review-Ready Artifacts        │
│  • Timeline spreadsheet                 │
│  • Draft demand letter                  │
│  • Legal analysis report                │
│  • Strategy recommendations             │
│  • Formal legal documents (complaints,  │
│    motions, memos)                      │
└─────────────────────────────────────────┘
```

**Agent Routing by Phase:**
| Phase | Default Agent | Alternative (by intent) |
|-------|---------------|------------------------|
| INTAKE_FACTS | LDA | - |
| ISSUE_FRAMING | DEA | LDA (damages/timeline) |
| RESEARCH_RETRIEVAL | DEA | - |
| APPLICATION_ANALYSIS | DEA | LDA (damages/valuation) |
| DRAFT_REVIEW | LSA | - |
| DOCUMENT_ASSEMBLY | DDA | - |

### State Management & Persistence
Themis implements a hybrid state management strategy for optimal performance:

**In-Memory Caching (TTL-based):**
- Configurable TTL (default: 60 seconds via `CACHE_TTL_SECONDS`)
- Write-through caching strategy
- 500x faster reads compared to direct database access
- 10x higher request throughput under load
- Automatic cache invalidation on expiry

**SQLite Persistence:**
- Plans stored in `orchestrator_state.db`
- Execution records with complete artifact storage
- Atomic writes with transaction support
- Lightweight, zero-config deployment
- Migrations support for schema evolution

**State Repository Pattern:**
- Abstract `StateRepository` interface
- Pluggable storage backends (SQLite default, PostgreSQL ready)
- Plan CRUD operations (save, retrieve, list)
- Execution history tracking

**What Gets Cached:**
- Execution plans with task graphs
- Agent execution results
- Artifact outputs (timelines, demand letters, complaints)
- Reflection results and quality checks

### Type Safety & Data Models
Themis uses Pydantic for runtime validation and type safety across all data structures:

**Core Models:**
- **Matter** – Complete legal matter with validation (min 10 char summary, required parties/documents)
- **Document** – Case documents with title, content, date, and metadata
- **Event** – Timeline events with date and description validation
- **Issue** – Legal issues with area classification (tort, contract, property, etc.)
- **Authority** – Legal citations with citation text and source tracking
- **Goals** – Client objectives with settlement ranges and desired outcomes
- **Damages** – Structured damage breakdown (economic, non-economic, punitive)
- **Metadata** – Matter metadata (jurisdiction, case type, filing dates)

**Validation Features:**
- Date format validation (YYYY-MM-DD)
- Non-negative damages validation
- String length limits (10,000 char per field)
- Script injection prevention
- Control character sanitization
- Required field enforcement with detailed 422 error messages

### Modular Architecture
Themis follows a modular design with clear separation of concerns:

**Agent Layer:**
- `agents/base.py` – Abstract base class with metrics, logging, and tool invocation
- `agents/constants.py` – Centralized magic numbers and configuration values
- `agents/tooling.py` – Tool specification and registration system
- `agents/dda_tools.py` – Document drafting tool implementations (separated from agent logic)

**LLM Layer:**
- `tools/llm_client.py` – Production Claude API client (~500 lines)
- `tools/stub_llm_client.py` – Testing stub handler (~880 lines, no API required)

**Orchestrator Layer:**
- `orchestrator/exceptions.py` – Custom exception hierarchy for consistent error handling
- `orchestrator/validation.py` – Input validation using Pydantic models
- `orchestrator/service.py` – Main orchestration logic with caching

### Error Handling
Themis provides a structured exception hierarchy for consistent error handling:

```python
ThemisError                    # Base exception with to_dict() for JSON responses
├── ValidationError            # Input validation failures (matter, params)
├── PlanNotFoundError          # Missing plan references
├── ExecutionNotFoundError     # Missing execution references
├── AgentNotFoundError         # Unregistered agent references
├── AgentExecutionError        # Agent runtime failures
├── ConnectorError             # External connector issues
├── DocumentGenerationError    # Document drafting failures
└── LLMError                   # LLM API operation failures
```

**Benefits:**
- All exceptions include structured `details` dict for debugging
- `to_dict()` method enables JSON serialization for API responses
- Specific exception types enable precise error handling
- Validation errors include field names and invalid values

Quick Start
-----------
### Prerequisites
- Python 3.10+ (3.11 recommended)
- pip or uv for dependency management
- Anthropic API Key (optional for stub mode)
- Docker (optional, for containerized deployment)

### Installation
```bash
# Clone the repository
git clone https://github.com/themis-agentic-system/themis-framework.git
cd themis-framework

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate

# Install dependencies
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY (or leave blank for stub mode)

# Optional: Configure agentic features (2025)
# USE_EXTENDED_THINKING=true        # Enable deep reasoning (default: true)
# USE_PROMPT_CACHING=true           # Enable 1-hour caching (default: true)
# ENABLE_CODE_EXECUTION=false       # Enable Python execution (default: false)
# See .env.example for all configuration options
```

### Run the API
```bash
# Start the FastAPI server
uvicorn api.main:app --reload

# API will be available at:
# - OpenAPI docs: http://localhost:8000/docs
# - Health check: http://localhost:8000/health
# - Metrics: http://localhost:8000/metrics
```

### Run Tests
```bash
# Run all tests
make test
# or
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_agents.py -v

# Run with coverage
python -m pytest tests/ --cov=agents --cov=orchestrator --cov=tools
```

### Test a Practice Pack
```bash
# Personal Injury demand letter
python -m packs.personal_injury.run \
  --matter packs/personal_injury/fixtures/sample_matter.json

# Criminal Defense case analysis
python -m packs.criminal_defense.run \
  --matter packs/criminal_defense/fixtures/dui_with_refusal.json

# List available fixtures
python -m packs.personal_injury.run --list
```

Usage Examples
--------------
### Example 1: API Orchestration
```python
import httpx
import asyncio

async def run_legal_analysis():
    matter = {
        "summary": "Client injured in slip-and-fall at grocery store",
        "parties": ["Jane Doe (Plaintiff)", "SuperMart Inc. (Defendant)"],
        "documents": [
            {
                "title": "Incident Report",
                "content": "On Jan 15, 2024, customer slipped on wet floor...",
                "date": "2024-01-15"
            }
        ],
        "events": [
            {"date": "2024-01-15", "description": "Slip and fall incident"},
            {"date": "2024-01-20", "description": "Medical treatment"}
        ],
        "goals": {
            "settlement": "$50,000 for medical bills and lost wages"
        }
    }

    async with httpx.AsyncClient() as client:
        # Create execution plan
        plan_response = await client.post(
            "http://localhost:8000/orchestrator/plan",
            json={"matter": matter},
            headers={"X-API-Key": "your-api-key"}
        )
        plan = plan_response.json()

        # Execute the plan
        exec_response = await client.post(
            "http://localhost:8000/orchestrator/execute",
            json={"plan_id": plan["plan_id"]},
            headers={"X-API-Key": "your-api-key"}
        )
        result = exec_response.json()

        print(f"Status: {result['status']}")
        print(f"Artifacts: {list(result['artifacts'].keys())}")

asyncio.run(run_legal_analysis())
```

> For complete API documentation including all endpoints, authentication, rate limits, and examples, see [docs/API_REFERENCE.md](docs/API_REFERENCE.md).

### Example 2: Custom Agent
```python
from agents.base import BaseAgent
from typing import Any

class CustomLegalAgent(BaseAgent):
    """Custom agent for specialized legal analysis."""

    REQUIRED_TOOLS = ("my_tool", "another_tool")

    def __init__(self, tools: dict[str, Any] | None = None):
        super().__init__(name="custom")
        self.tools = self._default_tools() | (tools or {})

    async def _run(self, matter: dict[str, Any]) -> dict[str, Any]:
        """Execute custom legal analysis."""

        # Use tools
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

    def _default_tools(self) -> dict:
        return {
            "my_tool": lambda matter: {"result": "analysis"},
            "another_tool": lambda matter: {"result": "data"}
        }
```

### Example 3: Docker Deployment
```bash
# Copy environment template
cp .env.docker .env

# Edit .env with your configuration
nano .env  # Add ANTHROPIC_API_KEY, THEMIS_API_KEY, etc.

# Start full stack (API + PostgreSQL + Prometheus + Grafana)
docker-compose up -d

# Check logs
docker-compose logs -f themis-api

# Run tests in container
docker-compose exec themis-api pytest tests/

# Access services:
# - API: http://localhost:8000
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000 (admin/admin)

# Stop stack
docker-compose down
```

Practice Packs
--------------
Practice packs bundle domain-specific prompts, validation schemas, and output formatters.

### 📋 Personal Injury Practice Pack (`packs/personal_injury`)
**Purpose:** Generate demand letters, complaints, and settlement packages for PI cases

**Features:**

- Jurisdiction-aware complaint generation (CA, NY, TX, FL, IL)
- Automated timeline creation from events
- Medical expense summaries with totals
- Evidence checklists with sourcing requirements
- Statute of limitations tracking
- Damages calculations (economic + non-economic)
- Jurisdiction-specific affirmative defenses and jury instructions

**11 Document Generators Across 5 Phases:**

**Intake Phase:**
- Case Intake Memorandum

**Pre-Suit Phase:**
- Settlement Demand Letter

**Litigation Phase:**
- Civil Complaint (jurisdiction-specific)
- Answer/Responsive Pleading
- Written Discovery (interrogatories, RFPs, RFAs)
- Deposition Outline

**ADR Phase:**
- Mediation Statement
- Settlement Agreement

**Trial Phase:**
- Trial Brief
- Witness & Exhibit Lists
- Proposed Jury Instructions

**Additional Artifacts:**
- `timeline.csv` – Chronological event timeline
- `evidence_checklist.txt` – Evidence requirements
- `medical_expense_summary.csv` – Medical damages breakdown
- `statute_tracker.txt` – SOL monitoring

**Usage:**
```bash
# Run with a fixture
python -m packs.personal_injury.run \
  --matter packs/personal_injury/fixtures/sample_matter.json

# Audit available assets
python -m packs.personal_injury.run --audit
```

**Available Fixtures:**

- `nominal_collision_matter.json` – Standard auto accident
- `edgecase_sparse_slip_and_fall.json` – Minimal data scenario
- `medical_malpractice_new_york.json` – NY med mal case
- `dog_bite_california.json` – CA premises liability

### ⚖️ Criminal Defense Pack (`packs/criminal_defense`)
**Purpose:** Analyze criminal cases, generate defense strategies, and prepare motions

**Current Status:** Schema and workflow infrastructure in place, document generators in development

**Implemented Features:**

- Criminal matter schema (charges, arrests, evidence, motions)
- Fixture-based test data (DUI, drug possession, felony assault)
- Case processing workflow
- Integration with orchestrator service

**Planned Capabilities:**

- Charge analysis with severity assessment
- Prior record evaluation
- Fourth Amendment analysis for searches/seizures
- Miranda rights compliance checking
- Suppression motion generation
- Plea negotiation frameworks
- Discovery request generation
- Witness interview guides

**Usage:**
```bash
# Run with a fixture
python -m packs.criminal_defense.run \
  --matter packs/criminal_defense/fixtures/dui_with_refusal.json

# List available fixtures
python -m packs.criminal_defense.run --list-fixtures
```

**Available Fixtures:**

- `dui_with_refusal.json` – DUI with breathalyzer refusal
- `drug_possession_traffic_stop.json` – Possession from vehicle search
- `felony_assault_self_defense.json` – Self-defense claim

### 🛠️ Creating Custom Practice Packs
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
from orchestrator.service import OrchestratorService

def main():
    matter = load_matter(sys.argv[1])
    service = OrchestratorService()
    result = asyncio.run(service.execute(matter))
    persist_outputs(result)

# 4. Add fixtures and test
```

Development Guide
-----------------
### Development Commands
```bash
# Linting and formatting
make lint                    # Run ruff checks
ruff check --fix .          # Auto-fix issues

# Testing
make test                    # Run all tests
pytest tests/ -v            # Verbose test output
pytest tests/test_agents.py::test_lda_agent_schema  # Single test
pytest tests/ --cov         # With coverage report

# Quality assurance
make qa                      # Run QA checks
pytest qa/ -v               # QA test suite

# Docker operations
docker-compose up -d         # Start services
docker-compose logs -f       # Watch logs
docker-compose exec themis-api bash  # Shell into container
```

### Project Standards
#### Code Quality
- ✅ Type hints on all function signatures
- ✅ Docstrings for all public functions and classes
- ✅ Maximum line length: 120 characters (black/ruff default)
- ✅ Use `from __future__ import annotations` for forward refs

#### Agent Development
- ✅ All agents must inherit from BaseAgent
- ✅ Include provenance metadata in all responses
- ✅ Track `unresolved_issues` for follow-up
- ✅ Support tool injection for testability

#### Testing
- ✅ Write tests for all new agents and tools
- ✅ Use fixtures in `conftest.py` for shared test data
- ✅ Mock LLM calls with custom tools in tests
- ✅ Aim for >80% code coverage

### Testing Philosophy
```python
# Good test example
def test_agent_handles_missing_data(sample_matter):
    """Verify agent gracefully handles missing required fields."""
    matter = {**sample_matter, "parties": []}  # Remove required field
    agent = LDAAgent()
    result = asyncio.run(agent.run(matter))

    # Should complete but flag the issue
    assert result["agent"] == "lda"
    assert "Matter payload did not list any known parties" in result["unresolved_issues"]
```

### Adding New Practice Packs
```text
Create directory structure:

packs/my_pack/
├── __init__.py
├── run.py                  # CLI entry point
├── schema.py               # JSON Schema validation
├── fixtures/               # Test matters
│   ├── sample_matter.json
│   └── edge_case.json
└── README.md               # Pack documentation

Define the schema (schema.py):

MATTER_SCHEMA = {
    "type": "object",
    "properties": {
        "metadata": {"type": "object"},
        "parties": {"type": "array"},
        # ... domain-specific fields
    },
    "required": ["metadata", "parties"]
}

Implement the workflow (run.py):

async def main():
    matter = load_matter(args.matter_file)
    validate_schema(matter, MATTER_SCHEMA)

    service = OrchestratorService()
    result = await service.execute(matter)

    persist_outputs(result, output_dir)

Add tests (tests/test_my_pack.py):

def test_my_pack_validates_matter():
    with pytest.raises(ValidationError):
        load_matter("invalid_matter.json")

def test_my_pack_generates_artifacts():
    result = run_pack("sample_matter.json")
    assert "expected_artifact.txt" in result.artifacts

Document usage (README.md):

# My Pack

## Purpose
Brief description of what this pack does

## Usage
python -m packs.my_pack.run --matter path/to/matter.json

## Artifacts
- artifact1.txt - Description
- artifact2.csv - Description
```

Observability & Metrics
-----------------------
### Middleware Stack
Themis uses a comprehensive middleware pipeline for production-grade observability:

**Request Logging Middleware:**
- HTTP request/response logging with status codes
- Automatic request ID generation (`X-Request-ID`)
- Client IP tracking and user agent capture
- Response time measurement (`X-Response-Time-Ms` header)
- Slow request detection (warnings for >1 second)
- Severity-based logging (INFO for 2xx, WARNING for 4xx, ERROR for 5xx)

**Audit Logging Middleware:**
- Security event logging for authentication attempts
- Failed authentication tracking (401/403 responses)
- Client IP correlation for security analysis

**Cost Tracking Middleware:**
- LLM API usage estimation per request
- Token consumption tracking (future enhancement)

**Payload Size Limiting:**
- Maximum 10MB request body size
- 413 response for oversized payloads
- Protection against memory exhaustion attacks

### Prometheus Metrics
Themis exposes metrics in Prometheus format at `/metrics`:

```bash
# View metrics
curl http://localhost:8000/metrics

# Key metrics:
themis_agent_run_seconds_bucket{agent="lda",le="0.5"}     # Latency histogram
themis_agent_tool_invocations_total{agent="dea"}          # Tool usage counter
themis_agent_run_errors_total{agent="lsa"}                # Error counter
```

### Structured Logging
All logs include structured context with automatic sanitization:

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "event": "agent_run_complete",
  "agent": "lda",
  "duration": 2.45,
  "tool_invocations": 3,
  "request_id": "req_abc123",
  "client_ip": "192.168.1.100"
}
```

**Security Features:**
- Sensitive data redaction (API keys, passwords)
- Control character sanitization
- Script tag removal (XSS prevention)
- String truncation (512 char limit in logs)

### Monitoring Stack
When running via Docker Compose:

- Prometheus (:9090) – Metrics collection and querying
- Grafana (:3000) – Visualization dashboards (admin/admin)

Pre-configured dashboards:

- Agent Performance (latency, throughput, error rates)
- System Health (CPU, memory, request rates)
- Cost Tracking (LLM API usage estimates)

Documentation
-------------
### Available Documentation

| Document | Description |
| --- | --- |
| `README.md` | Main project overview (this file) |
| `QUICKSTART.md` | Quick start guide for new users |
| `CLAUDE.md` | Agent guide with legal domain knowledge |
| `docs/AGENTIC_ENHANCEMENTS.md` | Complete guide to 2025 agentic features |
| `docs/API_REFERENCE.md` | Complete API endpoint documentation |
| `docs/CODE_REVIEW_REPORT.md` | Comprehensive code review |
| `docs/DEPLOYMENT_GUIDE.md` | Production deployment instructions |
| `docs/DOCKER_README.md` | Docker setup and configuration |
| `docs/IMPROVEMENTS.md` | Production features and enhancements |
| `docs/IMPLEMENTATION_SUMMARY.md` | Technical implementation details |
| `docs/TEST_RESULTS.md` | Test verification report |
| `.claude/commands/*.md` | Slash command workflow templates (6 commands) |

Contributing
------------
We welcome contributions! Here's how to get started:

### Contribution Process
```bash
# Fork the repository and create a feature branch
git checkout -b feature/my-new-feature

# Make your changes following our coding standards

# Add tests for new functionality
# Update documentation as needed
# Run linting and tests locally
# Ensure quality checks pass:
make lint    # Code quality
make test    # All tests pass
make qa      # QA checks

# Commit with descriptive messages:
git commit -m "Add feature: brief description

Longer explanation of what changed and why.
Fixes #123"

# Push and create a pull request:
git push origin feature/my-new-feature
```

Wait for CI checks – GitHub Actions will run:

- Linting (ruff)
- Test suite (pytest)
- QA validation

### Contribution Guidelines
- ✅ Follow existing code style and conventions
- ✅ Write tests for new features
- ✅ Update documentation for user-facing changes
- ✅ Keep PRs focused and atomic
- ✅ Respond to review feedback promptly

### Code of Conduct
Please review our Code of Conduct (coming soon) before contributing.

### Areas We'd Love Help With
- 🧪 Additional test coverage (especially API and edge cases)
- 📚 More practice packs for different legal domains
- 🐛 Bug fixes and performance improvements
- 📖 Documentation improvements and examples
- 🌐 Internationalization and multi-jurisdiction support

License
-------
Themis Framework is released under the MIT License.

```
Copyright (c) 2024-2025 Themis Maintainers

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

Support
-------
- 📧 Email: Contact the maintainers (coming soon)
- 💬 Discussions: GitHub Discussions
- 🐛 Bug Reports: GitHub Issues
- 📖 Documentation: See `docs/` directory

> "Trust, but verify."
>
> Every automated deliverable is designed for human review before filing, sending, or advising clients.

⚖️ Built with care for legal professionals | 🤖 Powered by Claude AI | 🛡️ Production-ready

[⬆ Back to Top](#themis-framework)
