API Reference
=============

Themis Framework exposes a REST API for orchestrating multi-agent legal workflows.

Base URL
--------
- Default: `http://localhost:8000`

Authentication
--------------
**Methods:**
- Header: `Authorization: Bearer {your-api-key}`
- Header: `X-API-Key: {your-api-key}`

**Development Mode:**
- No authentication required when `THEMIS_API_KEY` environment variable is not set
- Production deployment: Set `THEMIS_API_KEY` in `.env` file

**Key Rotation:**
- Supports primary and previous API keys
- Set `THEMIS_API_KEY_PREVIOUS` for graceful key rotation
- Both keys remain valid during rotation period

Orchestration Endpoints
-----------------------

### POST /orchestrator/plan
Create an execution plan from a matter payload.

**Rate Limit:** 20 requests/minute

**Request Body:**
```json
{
  "matter": {
    "summary": "Brief case description",
    "parties": ["Party 1", "Party 2"],
    "documents": [
      {
        "title": "Document Title",
        "content": "Document text...",
        "date": "2024-01-15"
      }
    ],
    "events": [
      {
        "date": "2024-01-15",
        "description": "Event description"
      }
    ],
    "goals": {
      "settlement": "Desired outcome"
    }
  }
}
```

**Response:**
```json
{
  "plan_id": "plan_abc123",
  "status": "planned",
  "tasks": [
    {
      "agent": "lda",
      "phase": "INTAKE_FACTS",
      "description": "Extract facts and build timeline"
    }
  ],
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Status Codes:**
- `200 OK` - Plan created successfully
- `400 Bad Request` - Invalid matter payload
- `401 Unauthorized` - Missing or invalid API key
- `422 Unprocessable Entity` - Validation error
- `429 Too Many Requests` - Rate limit exceeded

---

### POST /orchestrator/execute
Execute a workflow with a plan ID or matter payload.

**Rate Limit:** 10 requests/minute

**Request Body (with plan_id):**
```json
{
  "plan_id": "plan_abc123"
}
```

**Request Body (with matter):**
```json
{
  "matter": {
    "summary": "Case description",
    "parties": ["Party 1", "Party 2"],
    ...
  }
}
```

**Response:**
```json
{
  "plan_id": "plan_abc123",
  "status": "completed",
  "artifacts": {
    "timeline": "2024-01-15,Incident occurred\n...",
    "demand_letter": "Dear Counsel,\n\n...",
    "legal_analysis": "The following issues were identified..."
  },
  "execution_time": 12.34,
  "agents_executed": ["lda", "dea", "lsa"]
}
```

**Status Codes:**
- `200 OK` - Execution completed successfully
- `400 Bad Request` - Invalid request (missing plan_id or matter)
- `401 Unauthorized` - Missing or invalid API key
- `404 Not Found` - Plan ID not found
- `422 Unprocessable Entity` - Validation error
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Execution failed

---

### GET /orchestrator/plans/{plan_id}
Retrieve a stored execution plan.

**Rate Limit:** 60 requests/minute

**Path Parameters:**
- `plan_id` (string, required) - The plan identifier

**Response:**
```json
{
  "plan_id": "plan_abc123",
  "status": "planned",
  "tasks": [...],
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Status Codes:**
- `200 OK` - Plan retrieved successfully
- `401 Unauthorized` - Missing or invalid API key
- `404 Not Found` - Plan not found
- `429 Too Many Requests` - Rate limit exceeded

---

### GET /orchestrator/artifacts/{plan_id}
Retrieve execution results and artifacts.

**Rate Limit:** 60 requests/minute

**Path Parameters:**
- `plan_id` (string, required) - The plan identifier

**Response:**
```json
{
  "plan_id": "plan_abc123",
  "status": "completed",
  "artifacts": {
    "timeline": "CSV content...",
    "demand_letter": "Letter content...",
    "legal_analysis": "Analysis content..."
  },
  "execution_time": 12.34,
  "completed_at": "2024-01-15T10:35:00Z"
}
```

**Status Codes:**
- `200 OK` - Artifacts retrieved successfully
- `401 Unauthorized` - Missing or invalid API key
- `404 Not Found` - Plan not found or not executed
- `429 Too Many Requests` - Rate limit exceeded

System Endpoints
----------------

### GET /health
Health check and readiness probe.

**Rate Limit:** None

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Status Codes:**
- `200 OK` - Service is healthy

---

### GET /metrics
Prometheus-format metrics for monitoring.

**Rate Limit:** None

**Response:**
```text
# HELP themis_agent_run_seconds Agent execution time
# TYPE themis_agent_run_seconds histogram
themis_agent_run_seconds_bucket{agent="lda",le="0.5"} 10
themis_agent_run_seconds_bucket{agent="lda",le="1.0"} 25
...

# HELP themis_agent_tool_invocations_total Total tool invocations
# TYPE themis_agent_tool_invocations_total counter
themis_agent_tool_invocations_total{agent="lda"} 150
themis_agent_tool_invocations_total{agent="dea"} 200
...

# HELP themis_agent_run_errors_total Total agent execution errors
# TYPE themis_agent_run_errors_total counter
themis_agent_run_errors_total{agent="lsa"} 3
```

**Status Codes:**
- `200 OK` - Metrics retrieved successfully

Error Response Format
--------------------
All error responses follow a consistent format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common Errors:**

**400 Bad Request:**
```json
{
  "detail": "Request must include either 'plan_id' or 'matter'"
}
```

**401 Unauthorized:**
```json
{
  "detail": "Invalid API key"
}
```

**422 Validation Error:**
```json
{
  "detail": [
    {
      "loc": ["body", "matter", "summary"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**429 Rate Limit:**
```json
{
  "detail": "Rate limit exceeded. Try again in 60 seconds."
}
```

Rate Limiting
-------------
Rate limits are applied per API key:

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/orchestrator/plan` | 20 requests | 1 minute |
| `/orchestrator/execute` | 10 requests | 1 minute |
| `/orchestrator/plans/*` | 60 requests | 1 minute |
| `/orchestrator/artifacts/*` | 60 requests | 1 minute |
| `/health` | Unlimited | - |
| `/metrics` | Unlimited | - |

**Rate Limit Headers:**
- `X-RateLimit-Limit` - Maximum requests allowed
- `X-RateLimit-Remaining` - Requests remaining in current window
- `X-RateLimit-Reset` - Timestamp when limit resets

Request/Response Headers
-----------------------

**Request Headers:**
- `Authorization: Bearer {token}` - API authentication
- `X-API-Key: {key}` - Alternative API authentication
- `Content-Type: application/json` - Required for POST requests

**Response Headers:**
- `X-Request-ID` - Unique request identifier for debugging
- `X-Response-Time-Ms` - Server processing time in milliseconds
- `Content-Type: application/json` - JSON response format

Payload Limits
--------------
- **Maximum request body size:** 10 MB
- **Request timeout:** 120 seconds (2 minutes)
- **Field limits:**
  - String fields: 10,000 characters
  - Array fields: 1,000 items

Examples
--------

### Using curl

**Create and execute a plan:**
```bash
# Create plan
curl -X POST http://localhost:8000/orchestrator/plan \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d @matter.json

# Execute plan
curl -X POST http://localhost:8000/orchestrator/execute \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"plan_id": "plan_abc123"}'

# Get artifacts
curl http://localhost:8000/orchestrator/artifacts/plan_abc123 \
  -H "X-API-Key: your-api-key"
```

### Using Python (httpx)

```python
import httpx
import json

API_KEY = "your-api-key"
BASE_URL = "http://localhost:8000"

async def execute_legal_workflow():
    headers = {"X-API-Key": API_KEY}

    # Load matter
    with open("matter.json") as f:
        matter = json.load(f)

    async with httpx.AsyncClient() as client:
        # Create plan
        plan_resp = await client.post(
            f"{BASE_URL}/orchestrator/plan",
            json={"matter": matter},
            headers=headers
        )
        plan_resp.raise_for_status()
        plan = plan_resp.json()

        # Execute
        exec_resp = await client.post(
            f"{BASE_URL}/orchestrator/execute",
            json={"plan_id": plan["plan_id"]},
            headers=headers
        )
        exec_resp.raise_for_status()
        result = exec_resp.json()

        print(f"Status: {result['status']}")
        print(f"Artifacts: {list(result['artifacts'].keys())}")

        return result
```

### Using JavaScript (fetch)

```javascript
const API_KEY = "your-api-key";
const BASE_URL = "http://localhost:8000";

async function executeLegalWorkflow(matter) {
  const headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
  };

  // Create plan
  const planResp = await fetch(`${BASE_URL}/orchestrator/plan`, {
    method: "POST",
    headers,
    body: JSON.stringify({ matter })
  });
  const plan = await planResp.json();

  // Execute
  const execResp = await fetch(`${BASE_URL}/orchestrator/execute`, {
    method: "POST",
    headers,
    body: JSON.stringify({ plan_id: plan.plan_id })
  });
  const result = await execResp.json();

  console.log(`Status: ${result.status}`);
  console.log(`Artifacts: ${Object.keys(result.artifacts)}`);

  return result;
}
```

OpenAPI Documentation
--------------------
Interactive API documentation is available when the server is running:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

The interactive documentation allows you to:
- Browse all endpoints and schemas
- Try API requests directly from your browser
- View example requests and responses
- Download the OpenAPI specification

See Also
--------
- [Quick Start Guide](../QUICKSTART.md) - Get started with Themis
- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Production deployment instructions
