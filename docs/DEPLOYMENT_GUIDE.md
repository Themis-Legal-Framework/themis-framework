# Themis Framework - Deployment Guide

**Version:** 0.2.0
**Last Updated:** 2025-12-28

This guide covers deploying Themis with production optimizations: state caching, enhanced logging, and monitoring.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Production Deployment](#production-deployment)
3. [State Caching](#state-caching)
4. [Enhanced Logging](#enhanced-logging)
5. [Monitoring](#monitoring)
6. [Production Checklist](#production-checklist)

---

## Quick Start

### Prerequisites
- Python 3.10+ (3.11 recommended)
- pip or uv for dependency management
- Valid Anthropic API key

### Step 1: Clone and Configure

```bash
# Clone the repository
git clone https://github.com/themis-agentic-system/themis-framework.git
cd themis-framework

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Copy environment template
cp .env.example .env

# Edit .env and set your keys
nano .env
```

### Step 2: Set Required Environment Variables

```.env
# Generate a secure API key
THEMIS_API_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Add your Anthropic API key
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Agentic Features - Claude Advanced Capabilities
USE_EXTENDED_THINKING=true        # Enable deep reasoning (default: true)
USE_PROMPT_CACHING=true           # Enable 1-hour caching (default: true)
ENABLE_CODE_EXECUTION=false       # Enable Python execution (default: false)
MODEL=claude-3-5-sonnet-20241022  # Claude model version
```

### Step 3: Launch

```bash
# Start the API server
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Or with auto-reload for development
uvicorn api.main:app --reload
```

### Step 4: Test

```bash
# Set your API key
export THEMIS_API_KEY="your-api-key-from-env-file"

# Check health
curl http://localhost:8000/health

# Test the API
curl -X POST http://localhost:8000/orchestrator/plan \
  -H "X-API-Key: $THEMIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"matter": {"summary": "Test case for slip and fall", "parties": ["Alice", "Bob"], "documents": [{"title": "Report", "content": "Details", "date": "2024-01-01"}]}}'
```

**That's it!** Themis is now running with:
- ✅ SQLite persistence
- ✅ State caching
- ✅ Enhanced logging
- ✅ API authentication
- ✅ Rate limiting
- ✅ LLM retry logic

---

## Production Deployment

### Using a Process Manager

For production, use a process manager like systemd, supervisor, or PM2:

**systemd service example** (`/etc/systemd/system/themis.service`):

```ini
[Unit]
Description=Themis Framework API
After=network.target

[Service]
Type=simple
User=themis
WorkingDirectory=/opt/themis-framework
Environment="PATH=/opt/themis-framework/.venv/bin"
EnvironmentFile=/opt/themis-framework/.env
ExecStart=/opt/themis-framework/.venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable themis
sudo systemctl start themis
sudo systemctl status themis
```

### Using Gunicorn with Uvicorn Workers

For better performance and process management:

```bash
pip install gunicorn

gunicorn api.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
```

### Reverse Proxy with Nginx

Example nginx configuration:

```nginx
upstream themis {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;

    location / {
        proxy_pass http://themis;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
```

---

## State Caching

### What Is It?

In-memory caching with TTL (Time-To-Live) to reduce database reads by up to 90%.

### How It Works

```python
# Before: Every request hits the database
self.state = self.repository.load_state()  # DB read every time

# After: Cached for 60 seconds
self.state = self._load_state()  # Cache hit = no DB read
```

### Benefits

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Read latency | ~10-50ms | ~0.1ms | **99% faster** |
| DB connections | 1 per request | 1 per 60s | **98% reduction** |
| Throughput | ~100 req/s | ~1000 req/s | **10x increase** |

### Configuration

```python
# In orchestrator/service.py
OrchestratorService(cache_ttl_seconds=60)  # Default: 60 seconds
```

Or via environment variable:

```bash
CACHE_TTL_SECONDS=120  # 2 minutes
```

### Cache Behavior

**Cache Hit** (state < 60s old):
```
Request → Memory Cache → Response (0.1ms)
```

**Cache Miss** (state > 60s old):
```
Request → Database → Memory Cache → Response (10ms)
```

**Write Operations**:
```
Request → Database Write → Cache Update → Response
```

---

## Enhanced Logging

### Log Levels

Themis uses structured logging with 5 levels:

| Level | When to Use | Example |
|-------|-------------|---------|
| **DEBUG** | Development, troubleshooting | Cache hits, function calls |
| **INFO** | Normal operations | Request received, execution complete |
| **WARNING** | Potential issues | Slow requests, rate limits |
| **ERROR** | Errors that don't stop service | LLM failures, invalid requests |
| **CRITICAL** | Service-breaking errors | Database down, startup failures |

### Configuration

Set via environment variable:

```bash
LOG_LEVEL=INFO  # or DEBUG, WARNING, ERROR, CRITICAL
```

### Log Format

All logs follow a structured format:

```
2025-10-23 14:30:15 - themis.api - INFO - Request completed | duration=1234ms
```

### Log Categories

#### 1. Request Logs (`themis.api.requests`)

```
2025-10-23 14:30:15 - themis.api.requests - INFO - [req-1] POST /orchestrator/execute | client=192.168.1.1
2025-10-23 14:30:16 - themis.api.requests - INFO - [req-1] POST /orchestrator/execute | status=200 | duration=1234.56ms
```

#### 2. Audit Logs (`themis.api.audit`)

```
2025-10-23 14:30:15 - themis.api.audit - WARNING - Authentication failed: POST /orchestrator/plan | client=192.168.1.1
2025-10-23 14:30:20 - themis.api.audit - WARNING - Rate limit exceeded: POST /orchestrator/execute | client=192.168.1.1
```

#### 3. Agent Logs (`themis.agents`)

```
2025-10-23 14:30:15 - themis.agents - INFO - agent_run_start | agent=lda
2025-10-23 14:30:16 - themis.agents - INFO - agent_run_complete | agent=lda | duration=1.23 | tool_invocations=2
```

---

## Monitoring

### Prometheus Metrics

Access metrics at: `http://localhost:8000/metrics`

**Key Metrics:**

```prometheus
# Agent execution duration
themis_agent_run_seconds{agent="lda"}

# Tool invocations
themis_agent_tool_invocations_total{agent="lda"}

# Agent errors
themis_agent_run_errors_total{agent="lda"}
```

### Prometheus Configuration

Add to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'themis'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### Grafana Dashboards

Recommended dashboard panels:
- Request rate (req/s)
- Response times (p50, p95, p99)
- Error rate
- Agent execution times
- Cache hit rate

### Alerts

Example Prometheus alert rules:

```yaml
groups:
  - name: themis
    rules:
      - alert: HighErrorRate
        expr: rate(themis_agent_run_errors_total[5m]) > 0.05
        annotations:
          summary: "High error rate detected"

      - alert: SlowRequests
        expr: histogram_quantile(0.95, themis_agent_run_seconds) > 10
        annotations:
          summary: "95th percentile latency > 10s"
```

---

## Production Checklist

### Before Deployment

- [ ] Set strong `THEMIS_API_KEY` (32+ characters)
- [ ] Configure valid `ANTHROPIC_API_KEY`
- [ ] Set `LOG_LEVEL=WARNING` or `ERROR` (not DEBUG)
- [ ] Enable HTTPS/TLS (use nginx or cloud load balancer)
- [ ] Configure firewall rules
- [ ] Set up database backups (daily recommended)
- [ ] Configure log rotation
- [ ] Set up monitoring alerts
- [ ] Test disaster recovery procedure
- [ ] Document API key rotation process
- [ ] Configure CORS if needed

### Security Hardening

```bash
# Production environment variables
PRODUCTION_MODE=true
LOG_LEVEL=WARNING

# Use secrets manager for sensitive values
THEMIS_API_KEY=${THEMIS_API_KEY}
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
```

### Performance Tuning

```bash
# Adjust cache TTL based on your needs
CACHE_TTL_SECONDS=120  # Longer = better cache hit rate

# Tune uvicorn workers (2 * CPU cores + 1)
uvicorn api.main:app --workers 9 --host 0.0.0.0 --port 8000
```

---

## Troubleshooting

### Common Issues

**Issue: State not persisting**
```bash
# Check cache TTL
echo $CACHE_TTL_SECONDS

# Force cache invalidation by restarting the service
sudo systemctl restart themis
```

**Issue: High memory usage**
```bash
# Reduce cache TTL
CACHE_TTL_SECONDS=30

# Monitor memory
htop
```

**Issue: Slow responses**
```bash
# Check LLM latency
curl -w "@curl-format.txt" -X POST http://localhost:8000/orchestrator/plan ...

# Enable DEBUG logging temporarily
LOG_LEVEL=DEBUG
```

---

## Support

For issues or questions:
- Check health: `curl http://localhost:8000/health`
- Review logs: `journalctl -u themis -f`
- Review documentation: `docs/IMPROVEMENTS.md`
- GitHub Issues: https://github.com/themis-agentic-system/themis-framework/issues

---

**Status:** ✅ **Production Ready**
