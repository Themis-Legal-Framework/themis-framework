# LLM-COUNSEL

**Multi-Model Legal Strategy Deliberation System**

LLM-COUNSEL adapts [Andrej Karpathy's llm-council](https://github.com/karpathy/llm-council) architecture for litigation support. Instead of a "Chairman" synthesizing general responses, a **Lead Counsel** synthesizes legal strategy from multiple AI attorneys, each bringing different perspectives and specializations.

## Core Value Proposition

Small law firms can access the equivalent of a senior partner meeting where multiple expert attorneys deliberate on strategy—powered by AI.

## How It Works

```
Legal Question → Stage 1 (Initial Analyses) → Stage 2 (Peer Assessment) → Stage 3 (Lead Counsel Strategy)
```

### Three-Stage Deliberation Process

1. **Stage 1: Initial Legal Analyses**
   - Multiple AI attorneys analyze your question from different perspectives
   - Each attorney has a specialized role (Plaintiff's Strategist, Defense Analyst, etc.)

2. **Stage 2: Peer Assessment**
   - Each attorney blind-reviews and ranks the other analyses
   - Evaluates legal soundness, strategic merit, risk assessment, practical viability

3. **Stage 3: Lead Counsel Synthesis**
   - A Lead Counsel synthesizes all analyses and rankings
   - Produces a comprehensive legal strategy memorandum

## Legal Team Roles

| Role | Focus Area |
|------|------------|
| **Plaintiff's Strategist** | Aggressive case theory, damages maximization |
| **Defense Analyst** | Weaknesses, counterarguments, risk assessment |
| **Procedural Specialist** | Motions strategy, timing, procedural advantages |
| **Evidence Counsel** | Admissibility, discovery strategy, preservation |
| **Appellate Consultant** | Preserving issues, standard of review, precedent |
| **Settlement Strategist** | Settlement value, mediation strategy, leverage |

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- [OpenRouter API Key](https://openrouter.ai/keys)

### Installation

```bash
# Clone the repository
git clone https://github.com/Themis-Legal-Framework/llm-counsel.git
cd llm-counsel

# Create environment file
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY

# Install Python dependencies (using uv recommended)
uv sync
# Or with pip:
pip install -e .

# Install frontend dependencies
cd frontend && npm install && cd ..

# Start the application
./start.sh
```

### Access

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8001
- **API Documentation**: http://localhost:8001/docs

## Usage

1. **Create a Matter**: Click "New Matter" in the sidebar
2. **Configure**: Set practice area, jurisdiction, and client name
3. **Ask a Question**: Enter your legal question and any relevant context
4. **Review Results**: Browse through each stage's output
5. **Export**: Download the Lead Counsel memorandum

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/matters` | GET | List all matters |
| `/api/matters` | POST | Create new matter |
| `/api/matters/{id}` | GET | Get specific matter |
| `/api/matters/{id}` | DELETE | Delete matter |
| `/api/matters/{id}/messages` | POST | Submit question, trigger deliberation |
| `/api/deliberate` | POST | Quick deliberation (no matter) |
| `/api/config/team` | GET | Get legal team configuration |

## Configuration

### Legal Team (backend/config.py)

```python
COUNSEL_TEAM = [
    {
        "model": "anthropic/claude-sonnet-4-20250514",
        "role": "plaintiff_strategist",
        "display_name": "Plaintiff's Strategist"
    },
    {
        "model": "openai/gpt-4o",
        "role": "defense_analyst",
        "display_name": "Defense Analyst"
    },
    # ... more attorneys
]

LEAD_COUNSEL_MODEL = "anthropic/claude-sonnet-4-20250514"
```

### Team Presets

- **balanced_litigation**: General civil litigation
- **plaintiff_aggressive**: Plaintiff-focused strategy
- **defense_focused**: Defense-oriented risk assessment
- **appellate_prep**: Appellate preservation focus
- **settlement_evaluation**: Settlement and negotiation focus

## Technology Stack

- **Backend**: FastAPI (Python 3.10+)
- **Frontend**: React + Vite + TailwindCSS
- **LLM API**: OpenRouter (multi-provider access)
- **Storage**: JSON files

## Cost Estimate

Using OpenRouter with 4 counsel members + 1 Lead Counsel:

| Stage | API Calls | Typical Tokens |
|-------|-----------|----------------|
| Stage 1 | 4 (parallel) | ~2K input, ~1K output each |
| Stage 2 | 4 (parallel) | ~4K input, ~500 output each |
| Stage 3 | 1 | ~6K input, ~2K output |
| **Total** | **9 calls** | ~30K tokens per question |

**Estimated cost**: $0.10-0.50 per legal question (varies by model)

## Project Structure

```
llm-counsel/
├── backend/
│   ├── main.py              # FastAPI server
│   ├── config.py            # Team configuration
│   ├── counsel.py           # 3-stage deliberation logic
│   ├── openrouter.py        # OpenRouter API client
│   ├── storage.py           # JSON persistence
│   ├── prompts/             # Legal prompt templates
│   │   ├── personas.py      # Attorney role definitions
│   │   ├── stage1.py        # Initial analysis prompts
│   │   ├── stage2.py        # Peer review prompts
│   │   └── stage3.py        # Lead counsel prompts
│   └── utils/               # Utilities
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js
│   │   └── components/
│   └── package.json
├── data/
│   └── conversations/       # Stored matters
├── start.sh                 # Startup script
└── pyproject.toml
```

## Security Considerations

- All data stored locally (no cloud sync by default)
- API keys stored in `.env` (never committed)
- Matters stored as JSON in `data/conversations/`

## Disclaimer

This tool generates AI-powered legal analysis for informational purposes only. All outputs require review by a licensed attorney before implementation. This is not legal advice.

## Credits

- Created by **Scott D. Hughes**
- Architecture inspired by [karpathy/llm-council](https://github.com/karpathy/llm-council)
- Part of the [Themis Legal Framework](https://github.com/Themis-Legal-Framework)

## License

MIT License - See LICENSE file for details.
