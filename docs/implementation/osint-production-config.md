# OSINT Production Enhancements - Configuration Guide

## Overview

This document describes the production enhancements added to the OSINT Researcher agent, including caching, metrics collection, and retry logic.

## Features

### 1. Redis Caching (24-hour TTL)

**Purpose**: Reduce API calls and improve response times for repeated OSINT searches.

**Configuration** (`.env`):

```bash
# Redis connection
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=  # Optional

# Feature flag
ENABLE_OSINT_CACHE=false  # Set to true to enable
```

**How it works**:

- Cache key generated from hash of business name + address
- Results cached for 24 hours
- Automatic cache invalidation after TTL
- Manual invalidation via API endpoint

### 2. Metrics Collection

**Purpose**: Track OSINT performance, success rates, and identify issues.

**Configuration** (`.env`):

```bash
ENABLE_OSINT_METRICS=true  # Enabled by default
```

**Metrics tracked**:

- Success rate per source (Google Maps, Instagram, Facebook)
- Average latency per source
- Average DVS scores
- Recent errors with timestamps

**Access metrics**:

```bash
GET /api/v1/osint/metrics
```

### 3. Retry Logic

**Purpose**: Handle transient network failures gracefully.

**Implementation**:

- Exponential backoff with jitter
- Configurable max attempts (default: 3)
- Automatic retry on network errors

**Usage**:

```python
from app.utils.retry import async_retry

@async_retry(max_attempts=3, initial_delay=1.0)
async def my_network_call():
    # Your code here
    pass
```

## API Endpoints

### Get OSINT Metrics

```http
GET /api/v1/osint/metrics
```

**Response**:

```json
{
  "total_operations": 150,
  "overall_success_rate": 78.5,
  "average_latency_ms": 2500,
  "average_dvs": 0.65,
  "by_source": {
    "google_maps": {
      "success_rate": 85.0,
      "avg_latency_ms": 1200
    },
    "instagram": {
      "success_rate": 72.0,
      "avg_latency_ms": 1800
    },
    "facebook": {
      "success_rate": 68.0,
      "avg_latency_ms": 2100
    }
  },
  "recent_errors": [...]
}
```

### Get Cache Statistics

```http
GET /api/v1/osint/cache/stats
```

**Response**:

```json
{
  "enabled": true,
  "osint_keys_count": 45,
  "total_keys": 100,
  "hits": 120,
  "misses": 30,
  "hit_rate": 80.0
}
```

### Invalidate Cache Entry

```http
POST /api/v1/osint/cache/invalidate
Content-Type: application/json

{
  "business_name": "Colmado La Bendición",
  "business_address": "Los Mina, Santo Domingo Este"
}
```

### Clear All Cache

```http
DELETE /api/v1/osint/cache/clear
```

## Redis Setup

### Local Development (Docker)

```bash
# Start Redis container
docker run -d \
  --name creditflow-redis \
  -p 6379:6379 \
  redis:7-alpine

# Enable caching in .env
echo "ENABLE_OSINT_CACHE=true" >> .env
```

### Production (Redis Cloud)

```bash
# Update .env with Redis Cloud credentials
REDIS_HOST=redis-12345.c1.us-east-1-1.ec2.cloud.redislabs.com
REDIS_PORT=12345
REDIS_PASSWORD=your-password-here
ENABLE_OSINT_CACHE=true
```

## Performance Impact

### Without Caching

- Average latency: ~3000ms per OSINT search
- API costs: $0.002 per search (SerpAPI)
- Rate limits: 100 searches/day (free tier)

### With Caching (24h TTL)

- Cache hit latency: ~50ms
- API cost savings: ~70% (assuming 70% cache hit rate)
- Effective rate limit: 300+ searches/day

## Monitoring Best Practices

1. **Track Success Rates**: Monitor `/osint/metrics` daily
   - Alert if overall success rate < 70%
   - Alert if any source success rate < 50%

2. **Monitor Cache Performance**:
   - Target cache hit rate: > 60%
   - If hit rate < 40%, consider increasing TTL

3. **Latency Monitoring**:
   - Target average latency: < 3000ms
   - Alert if latency > 5000ms consistently

4. **Error Tracking**:
   - Review `recent_errors` in metrics
   - Common errors: network timeouts, rate limits, scraping failures

## Troubleshooting

### Cache Not Working

```bash
# Check Redis connection
redis-cli ping
# Should return: PONG

# Check feature flag
grep ENABLE_OSINT_CACHE .env
# Should show: ENABLE_OSINT_CACHE=true

# Check logs
tail -f logs/creditflow.log | grep "OSINT cache"
```

### High Error Rates

```bash
# Check metrics
curl http://localhost:8000/api/v1/osint/metrics

# Common fixes:
# 1. Verify SERPAPI_KEY is valid
# 2. Check network connectivity
# 3. Verify Playwright is installed: playwright install
# 4. Increase rate limiting delays
```

## Future Enhancements

- [ ] Distributed caching with Redis Cluster
- [ ] Prometheus metrics export
- [ ] Grafana dashboards
- [ ] Automated cache warming
- [ ] ML-based DVS threshold optimization
