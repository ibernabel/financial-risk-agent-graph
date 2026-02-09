# Logging & Monitoring Strategy

## Overview

This document outlines the logging and monitoring strategy for CreditFlow AI to ensure observability, debugging capability, and production readiness.

## Logging Architecture

### Structured Logging

All logs use structured JSON format for easy parsing and aggregation:

```python
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()
```

### Log Levels

- **DEBUG**: Detailed diagnostic information (disabled in production)
- **INFO**: General informational messages (workflow progress, state transitions)
- **WARNING**: Warning messages (retries, fallbacks, deprecated features)
- **ERROR**: Error messages (handled exceptions, validation failures)
- **CRITICAL**: Critical errors (system failures, data corruption)

### Log Context

All logs include contextual information:

```python
logger.info(
    "triage_completed",
    case_id=state.case_id,
    applicant_age=state.applicant.get("age"),
    status=result.status,
    processing_time_ms=elapsed_ms,
    rejection_reason=result.rejection_reason if result.status == "REJECTED" else None
)
```

### Agent-Specific Logging

Each agent logs key events:

**Triage Agent:**

- Validation start/completion
- Rule evaluation results
- Rejection reasons

**Financial Analyst:**

- Document parsing start/completion
- Pattern detection results
- Financial behavior score calculation

**OSINT Researcher:**

- Data source queries
- Verification results
- Confidence scores

**IRS Engine:**

- Score calculation inputs
- Risk factor weights
- Final IRS score

**Underwriter:**

- Decision inputs
- Approval/rejection decision
- Human escalation triggers

## Monitoring Strategy

### Application Metrics

**Performance Metrics:**

- Request latency (p50, p95, p99)
- Workflow execution time per agent
- Database query performance
- External API response times (TransUnion, OSINT sources)

**Business Metrics:**

- Total applications processed
- Approval rate
- Rejection rate by reason
- Average processing time
- Human escalation rate

**Error Metrics:**

- Error rate by agent
- Failed API calls
- Validation errors
- Timeout occurrences

### Infrastructure Metrics

- CPU utilization
- Memory usage
- Disk I/O
- Network throughput
- Database connection pool status
- PostgreSQL checkpoint performance

### Alerting Rules

**Critical Alerts (PagerDuty/Slack):**

- Error rate > 5% for 5 minutes
- API availability < 99%
- Database connection failures
- Workflow execution failures

**Warning Alerts (Slack):**

- Response time p95 > 5 seconds
- Memory usage > 80%
- Disk usage > 85%
- High rejection rate (> 50%)

## Implementation

### Recommended Tools

**Logging:**

- **Local Development:** Console output with pretty formatting
- **Production:** JSON logs to stdout → CloudWatch/ELK/Datadog

**APM (Application Performance Monitoring):**

- **Sentry:** Error tracking and performance monitoring
- **Datadog APM:** Full-stack observability
- **New Relic:** Alternative APM solution

**Metrics:**

- **Prometheus:** Metrics collection
- **Grafana:** Visualization dashboards
- **CloudWatch:** AWS-native monitoring

**Distributed Tracing:**

- **OpenTelemetry:** Industry-standard tracing
- **Jaeger:** Trace visualization
- **Datadog APM:** Integrated tracing

### Example Implementation

```python
# app/core/logging.py
import structlog
import logging
from pythonjsonlogger import jsonlogger

def configure_logging(log_level: str = "INFO"):
    """Configure structured logging for the application."""

    # Configure standard logging
    logHandler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(name)s %(levelname)s %(message)s'
    )
    logHandler.setFormatter(formatter)
    logging.basicConfig(level=log_level, handlers=[logHandler])

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

# Usage in agents
from app.core.logging import configure_logging
import structlog

configure_logging(log_level="INFO")
logger = structlog.get_logger(__name__)

async def triage_node(state: AgentState) -> dict:
    start_time = time.time()

    logger.info(
        "triage_started",
        case_id=state.case_id,
        applicant_age=state.applicant.get("age"),
        loan_amount=state.loan.get("requested_amount")
    )

    try:
        # Triage logic...
        result = TriageResult(...)

        logger.info(
            "triage_completed",
            case_id=state.case_id,
            status=result.status,
            processing_time_ms=(time.time() - start_time) * 1000
        )

        return {"triage_result": result}

    except Exception as e:
        logger.error(
            "triage_failed",
            case_id=state.case_id,
            error=str(e),
            exc_info=True
        )
        raise
```

### Metrics Collection

```python
# app/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
triage_total = Counter(
    'creditflow_triage_total',
    'Total triage operations',
    ['status']
)

triage_duration = Histogram(
    'creditflow_triage_duration_seconds',
    'Triage processing duration'
)

active_workflows = Gauge(
    'creditflow_active_workflows',
    'Number of active workflows'
)

# Usage
with triage_duration.time():
    result = await triage_node(state)

triage_total.labels(status=result.status).inc()
```

## Dashboards

### Operational Dashboard

- Request rate (requests/minute)
- Error rate
- Response time (p50, p95, p99)
- Active workflows
- Database connection pool

### Business Dashboard

- Applications processed (hourly/daily)
- Approval vs rejection rate
- Average processing time
- Top rejection reasons
- Human escalation rate

### Agent Performance Dashboard

- Processing time per agent
- Error rate per agent
- Pattern detection accuracy
- Credit score distribution
- IRS score distribution

## Log Retention

- **Development:** 7 days
- **Staging:** 30 days
- **Production:** 90 days (compliance requirement)
- **Audit Logs:** 7 years (regulatory requirement)

## Privacy & Security

- **PII Masking:** Automatically mask sensitive data (cedula, phone numbers, addresses)
- **Encryption:** Logs encrypted at rest and in transit
- **Access Control:** Role-based access to logs and metrics
- **Audit Trail:** All log access logged for compliance

## Next Steps

1. **Phase 3:** Implement structured logging across all agents
2. **Phase 4:** Set up Prometheus + Grafana for metrics
3. **Phase 5:** Configure Sentry for error tracking
4. **Phase 6:** Create operational dashboards
5. **Production:** Deploy monitoring stack to production environment
