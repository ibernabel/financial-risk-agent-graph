# Phase 5: OSINT Research Implementation

## Overview

Implemented OSINT (Open-Source Intelligence) capabilities for validating informal businesses using public online data sources. The system searches Google Maps, Instagram, and Facebook to calculate a Digital Veracity Score (DVS) that indicates business legitimacy.

## Implementation Summary

### Components Delivered

1. **SerpAPI Client** - Google Maps search with rate limiting
2. **Social Media Scrapers** - Instagram and Facebook public profile scrapers
3. **DVS Calculator** - Weighted scoring algorithm (5 factors)
4. **OSINT Agent** - Orchestration with parallel searches and error handling

### Test Results

**23/23 tests passing** ✅

- SerpAPI Client: 8/8 tests
- Social Scrapers: 6/6 tests
- DVS Calculator: 9/9 tests

## Technical Architecture

### 1. SerpAPI Client (`app/tools/serpapi_client.py`)

**Purpose**: Google Maps business location verification

**Key Features**:

- Google Maps search via SerpAPI
- Token bucket rate limiter (10 req/min)
- Address fuzzy matching (Jaccard similarity)
- Graceful error handling

**Models**:

```python
class GoogleMapsResult(BaseModel):
    found: bool
    place_id: Optional[str]
    rating: Optional[float]
    reviews_count: int
    address: Optional[str]
    address_match_score: float  # 0.0-1.0
```

---

### 2. Social Media Scrapers

#### Browser Manager (`app/tools/browser_manager.py`)

Singleton Playwright browser with anti-detection:

- Custom user agent
- Viewport configuration
- JavaScript stealth injection
- Shared context for efficiency

#### Instagram Scraper (`app/tools/instagram_scraper.py`)

**Search Strategy**:

1. Google search for Instagram profile
2. Extract username from results
3. Scrape public profile metadata

**Data Extracted**:

- Username, followers, post count
- Bio text
- Profile existence

**Limitations**: Cannot access post dates without authentication

#### Facebook Scraper (`app/tools/facebook_scraper.py`)

**Search Strategy**:

1. Google search for Facebook business page
2. Extract page URL
3. Scrape public page metadata

**Data Extracted**:

- Page URL, likes count
- About section
- Page existence

**Limitations**: Cannot access post dates or check-ins without authentication

---

### 3. Digital Veracity Score (DVS) Calculator

**Algorithm** (PRD Section 3):

| Factor               | Weight | Scoring Logic                                  |
| -------------------- | ------ | ---------------------------------------------- |
| Google Maps Presence | 30%    | Found = 1.0, Not found = 0.0                   |
| Reviews Count        | 15%    | >10 = 1.0, 5-10 = 0.7, 1-4 = 0.4, 0 = 0.0      |
| Instagram Activity   | 25%    | Posts + followers = 1.0, Low = 0.6, None = 0.0 |
| Facebook Page        | 15%    | >100 likes = 1.0, Some = 0.4, None = 0.0       |
| Name Consistency     | 15%    | Exact = 1.0, Partial = 0.5, Mismatch = 0.0     |

**Output**:

```python
class DVSResult(BaseModel):
    score: float  # 0.0-1.0
    confidence: float  # Based on data completeness
    breakdown: dict[str, float]
    evidence_count: int
    sources_checked: list[str]
```

**DVS Threshold**: ~70% acceptable for informal businesses

---

### 4. OSINT Agent Node (`app/agents/osint/node.py`)

**Workflow**:

1. Extract business name/address from triage
2. **Parallel searches** (Google Maps, Instagram, Facebook)
3. Calculate DVS from all findings
4. Return `OSINTFindings` with evidence

**Error Handling**:

- Per-source exception handling
- Graceful degradation (DVS = 0.0 if all fail)
- Detailed logging for debugging

**Performance**:

- Parallel execution via `asyncio.gather()`
- Rate limiting prevents quota exhaustion
- ~10-15 seconds per business (with rate limits)

---

## Configuration

### Environment Variables

```bash
# .env
SERPAPI_KEY=your_serpapi_key_here
```

### Settings (`app/core/config.py`)

```python
class ExternalServicesSettings(BaseSettings):
    serpapi_key: str
    serpapi_rate_limit: int = 10  # requests/minute
    serpapi_timeout: int = 30  # seconds
```

---

## Integration with Workflow

### State Flow

```
TriageAgent → business_name, business_address
    ↓
OSINTAgent
    ├── Google Maps (SerpAPI)
    ├── Instagram (Playwright)
    └── Facebook (Playwright)
    ↓
DVS Calculator
    ↓
OSINTFindings
    ├── business_found: bool
    ├── digital_veracity_score: float (0.0-1.0)
    ├── sources_checked: list[str]
    └── evidence: dict
```

### Next Agents

OSINT findings feed into:

- **Financial Analyst** (Phase 4) - Risk assessment
- **IRS Engine** (Phase 6) - Final scoring

---

## Known Limitations & Mitigation

### 1. Scraping Stability

**Issue**: Instagram/Facebook may change HTML structure

**Mitigation**:

- Graceful degradation
- Fallback to Google search
- Regular monitoring
- Documented in confidence score

### 2. Authentication Limitations

**Issue**: Cannot access post dates without login

**Mitigation**:

- Estimate activity using follower/likes counts
- Focus on presence verification
- Document in DVS confidence

### 3. Rate Limiting

**Issue**: API quota exhaustion

**Mitigation**:

- Token bucket rate limiter
- 3-second delays between requests
- Parallel execution
- Future: caching

### 4. Privacy Compliance

**Issue**: Law 172-13 (Dominican Data Protection)

**Mitigation**:

- Only public business data
- No PII collection
- Business-focused searches only

---

## Files Created

| File                                 | Lines | Purpose                     |
| ------------------------------------ | ----- | --------------------------- |
| `app/tools/serpapi_client.py`        | 240   | SerpAPI Google Maps client  |
| `app/tools/browser_manager.py`       | 95    | Playwright browser manager  |
| `app/tools/instagram_scraper.py`     | 233   | Instagram scraper           |
| `app/tools/facebook_scraper.py`      | 239   | Facebook scraper            |
| `app/agents/osint/dvs_calculator.py` | 285   | DVS calculator              |
| `app/agents/osint/node.py`           | 145   | OSINT agent (replaced stub) |
| `tests/test_serpapi_client.py`       | 180   | SerpAPI tests               |
| `tests/test_social_scrapers.py`      | 75    | Scraper tests               |
| `tests/test_dvs_calculator.py`       | 165   | DVS tests                   |

**Total**: ~1,657 lines of production code + tests

---

## Dependencies

```toml
playwright = ">=1.40.0"
google-search-results = ">=2.4.2"
```

**Browser Installation**:

```bash
.venv/bin/playwright install chromium
```

---

## Testing Strategy

### Unit Tests (23 tests)

- **SerpAPI Client**: Rate limiting, search logic, address matching
- **Social Scrapers**: Count extraction, K/M suffix handling
- **DVS Calculator**: Scoring logic, weight distribution, edge cases

### Integration Tests (Future)

- End-to-end workflow with real business data
- API quota monitoring
- Scraper success rate tracking

### Manual Testing (Future)

- Real Dominican businesses
- Edge cases (no online presence, name variations)
- Performance benchmarking

---

## Future Enhancements

1. **Caching**: Store OSINT results (24-hour TTL)
2. **Retry Logic**: Exponential backoff for failed requests
3. **Enhanced Scrapers**: Use official APIs when available
4. **Activity Detection**: Implement post date estimation algorithms
5. **Monitoring**: Track success rates and API usage
6. **Multi-language**: Support Spanish business names

---

## Security & Privacy

### Compliance

- **Law 172-13**: Only public business data, no PII
- **Rate Limiting**: Prevents abuse and quota exhaustion
- **Error Logging**: No sensitive data in logs

### Best Practices

- API keys in `.env` (not committed)
- Stealth techniques for scraping
- Graceful degradation (no crashes)

---

## Performance Metrics

### Expected Performance

- **Google Maps**: ~2-3 seconds per search
- **Instagram**: ~5-7 seconds per search
- **Facebook**: ~5-7 seconds per search
- **Total**: ~10-15 seconds per business (parallel)

### Rate Limits

- **SerpAPI**: 10 requests/minute
- **Instagram**: 3-second delay between requests
- **Facebook**: 3-second delay between requests

---

## Deployment Checklist

- [x] Dependencies installed (`playwright`, `google-search-results`)
- [x] Chromium browser installed
- [x] `SERPAPI_KEY` configured in `.env`
- [x] All tests passing (23/23)
- [ ] Manual testing with real data
- [ ] Integration test with full workflow
- [ ] Update `ROADMAP.md`
- [ ] Monitor API usage and success rates

---

## References

- **PRD**: `docs/planning/prd.md` (Section 3: Agent 3 - OSINT Researcher)
- **Implementation Plan**: `brain/implementation_plan.md`
- **Walkthrough**: `brain/walkthrough.md`
