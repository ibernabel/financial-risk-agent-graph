# Instagram Search Improvement Plan

## Current Limitation

### How It Works Now

The Instagram scraper uses a **Google search fallback** approach:

1. Search Google for `site:instagram.com {business_name}`
2. Extract the **first** Instagram profile link from results
3. Scrape the profile page using Playwright

### The Problem

**Low Accuracy**: The search returns the first Instagram profile Google finds, which is often **incorrect**.

**Example**:

- **Search**: "Deiquel Cake Toppers"
- **Found**: `@magichandsrd` ❌ (completely wrong profile)
- **Expected**: `@deiquelcaketoppers` (but username recently changed from `@deiquelparty`)

**Root Causes**:

1. No validation that the found profile matches the business
2. Relies on Google's ranking, not business relevance
3. Cannot handle username changes or aliases
4. No fallback if the profile name doesn't match business name

---

## Sherlock Investigation

**Tool**: [Sherlock](https://github.com/sherlock-project/sherlock) - Username search across social networks

### Test Case: Deiquel Cake Toppers

**Username**: `@deiquelcaketoppers` (current)

```
https://gitlab.gnome.org/deiquelcaketoppers
Total Websites Username Detected On: 1
```

❌ **Not found on Instagram** (only GitLab)

**Username**: `@deiquelparty` (former)

```
https://gitlab.gnome.org/deiquelparty
https://linktr.ee/deiquelparty
https://www.tiktok.com/@deiquelparty
https://www.youtube.com/@deiquelparty
Total Websites Username Detected On: 4
```

❌ **Not found on Instagram** (found on TikTok, YouTube, Linktr.ee)

### Findings

1. **Username changes** are common for businesses
2. **Sherlock** doesn't always detect Instagram profiles (privacy settings, rate limits)
3. The business may use **different usernames** across platforms

---

## Improvement Strategy

### Phase 1: Multi-Username Generation (Short-term)

**Approach**: Generate multiple username variations and test each

**Username Variations**:

1. Exact business name: `deiquelcaketoppers`
2. Remove spaces/special chars: `deiquelcaketopper`
3. Abbreviations: `dcaketoppers`, `deiquel`
4. Brand variations from Google Maps data
5. Extract from website URL if available

**Implementation**:

```python
def generate_username_variations(business_name: str, website: Optional[str] = None) -> list[str]:
    """Generate Instagram username variations."""
    variations = []

    # Normalize name
    clean_name = business_name.lower().replace(" ", "").replace("-", "")
    variations.append(clean_name)

    # Remove common business types
    for suffix in ["cake", "toppers", "store", "shop", "rd", "dominicana"]:
        if clean_name.endswith(suffix):
            variations.append(clean_name.replace(suffix, ""))

    # Extract from website domain
    if website:
        domain = website.split("//")[-1].split("/")[0].replace("www.", "")
        handle = domain.split(".")[0]
        variations.append(handle)

    return list(set(variations))  # Remove duplicates
```

**Validation**:

- Try each variation with Playwright
- Match bio/profile name against business name using fuzzy matching
- Return the best match with a confidence score

---

### Phase 2: Sherlock Integration (Medium-term)

**Approach**: Use Sherlock to validate username existence before scraping

**Benefits**:

- Fast username validation across platforms
- Detect presence on TikTok, YouTube, etc. (bonus data)
- Lower rate limit impact

**Implementation**:

```python
async def validate_username_with_sherlock(username: str) -> dict:
    """Use Sherlock to validate username across platforms."""
    # Run: sherlock {username} --timeout 5 --json
    result = subprocess.run(
        ["sherlock", username, "--timeout", "5", "--json"],
        capture_output=True,
        text=True
    )

    data = json.loads(result.stdout)

    return {
        "instagram": "https://www.instagram.com/" + username in data,
        "tiktok": data.get("TikTok", {}).get("url_user"),
        "youtube": data.get("YouTube", {}).get("url_user"),
        # ... other platforms
    }
```

---

### Phase 3: SerpAPI Instagram Search (Long-term)

**Approach**: Use SerpAPI's Instagram search API (if available)

**Benefits**:

- Native Instagram search
- Better relevance ranking
- More reliable than scraping

**Research Needed**:

- Check if SerpAPI offers Instagram search
- Evaluate API costs vs. scraping reliability
- Compare accuracy with current approach

---

## Data Flow (Proposed)

```
Business Input
    |
    v
Google Maps Search
    |
    +--> Extract business data (name, address, website)
    |
    v
Generate Username Variations
    |  (from business name + website)
    |
    v
Validate with Sherlock (optional)
    |
    v
Try Each Variation with Playwright
    |
    +--> Scrape profile data
    +--> Fuzzy match bio/name
    +--> Calculate confidence score
    |
    v
Return Best Match
    |
    +--> High Confidence (> 0.8): Use result
    +--> Medium Confidence (0.5-0.8): Flag for review
    +--> Low Confidence (< 0.5): Mark as "Not Found"
```

---

## Implementation Priorities

### Priority 1: Multi-Username Generation ⭐⭐⭐

- **Effort**: Low (1-2 hours)
- **Impact**: Medium
- **Dependencies**: None

### Priority 2: Bio/Name Fuzzy Matching ⭐⭐⭐

- **Effort**: Low (1 hour)
- **Impact**: Medium
- **Dependencies**: `text_utils` (already exists)

### Priority 3: Confidence Scoring ⭐⭐

- **Effort**: Medium (2-3 hours)
- **Impact**: High (enables human review workflow)
- **Dependencies**: Fuzzy matching

### Priority 4: Sherlock Integration ⭐

- **Effort**: Medium (3-4 hours)
- **Impact**: Medium
- **Dependencies**: Sherlock CLI installation
- **Note**: Requires system dependency (`sherlock`)

### Priority 5: SerpAPI Instagram Search

- **Effort**: High (research + implementation)
- **Impact**: Unknown (depends on API availability)
- **Dependencies**: SerpAPI feature availability

---

## Testing Strategy

### Test Cases

1. **Direct Match**: Business name = Instagram username
   - Example: "Solufime" → `@prestamos.solufime` ✅

2. **Abbreviated Match**: Business name shortened
   - Example: "Deiquel Cake Toppers" → `@deiquelcaketoppers`

3. **Brand Match**: Using brand name only
   - Example: "Préstamos Personales Solufime" → `@solufime`

4. **Website Match**: Username in website domain
   - Example: `www.solufime.com` → `@solufime`

5. **No Match**: Business not on Instagram
   - Should return `found=False` with high confidence

### Success Metrics

- **Accuracy**: % of correctly identified Instagram profiles
  - **Target**: 70%+ (vs. current ~30%)
- **False Positives**: % of incorrect profile matches
  - **Target**: < 10%

- **Coverage**: % of businesses with Instagram found
  - **Baseline**: Unknown (needs measurement)
  - **Target**: 60%+ for informal DR businesses

---

## Next Steps

1. ✅ **Document current limitation** (this document)
2. ⬜ **Implement username variation generator**
3. ⬜ **Add fuzzy matching for bio/profile name**
4. ⬜ **Add confidence scoring**
5. ⬜ **Create test dataset** (20 real Dominican businesses)
6. ⬜ **Test and measure accuracy improvement**
7. ⬜ **Evaluate Sherlock integration** (optional)

---

## Notes

- Instagram profile discovery is **inherently challenging** without direct API access
- **Username changes** are common and unpredictable
- **Manual validation** may still be needed for high-value cases
- Consider adding a **manual Instagram username field** to business rules for override
- The PRD emphasizes Instagram importance for **informal businesses in DR**

---

## References

- **Sherlock**: https://github.com/sherlock-project/sherlock
- **Current Implementation**: `app/tools/instagram_scraper.py`
- **Text Utilities**: `app/utils/text_utils.py` (fuzzy matching)
- **PRD**: Instagram critical for informal business verification in DR

---

**Status**: 📋 **Documented - Awaiting Implementation**

**Owner**: TBD

**Created**: 2026-02-10

**Last Updated**: 2026-02-10
