# Reverse-Engineering & API Discovery Tools

This directory houses the reverse-engineering tooling and API specifications adapted from [`goodnight000/api-anything`](https://github.com/goodnight000/api-anything) to convert complex, JavaScript-rendered job boards and career portals into ultra-fast, zero-overhead direct APIs.

---

## Directory Structure

```text
tools/
├── README.md                 # Architecture and usage guide
├── endpoint_discovery.py     # Playwright network interceptor & spec generator
├── spec_runner.py            # Python engine to execute api-anything JSON specs
├── specs/                    # Project-specific custom job board specs
└── api_anything/             # Vendored upstream repository (pre-bundled specs & TS source)
    ├── sites/                # 80+ pre-bundled specs (ashby, workday, linkedin, etc.)
    └── src/                  # Upstream TypeScript source
```

---

## 1. `endpoint_discovery.py`

A Playwright-driven network interceptor that captures background XHR/Fetch/GraphQL requests while navigating any career board.

### Key Capabilities:
- **Telemetry Filtering:** Strips out analytics, tracking, and metric endpoints (Google Analytics, Sentry, Datadog, etc.).
- **Spec Generation:** Automatically generates an `api-anything`-compatible JSON specification containing endpoints, HTTP methods, headers, and response extraction paths.
- **Tier 1 Verification:** Automatically tests whether the captured endpoint can be called directly via plain Python HTTP requests (`requests`) without requiring a browser.

### Usage:
```bash
# Analyze a target URL and generate a spec
python tools/endpoint_discovery.py --url "https://wellfound.com/jobs" --output tools/specs/wellfound.json

# Interactive mode (opens a browser window for you to perform actions)
python tools/endpoint_discovery.py --url "https://company.myworkdayjobs.com/careers" --interactive
```

---

## 2. `spec_runner.py`

A pure Python execution engine that reads `api-anything` specification files (like `tools/api_anything/sites/workday.json` or `tools/api_anything/sites/linkedin.json`) and executes them using the **Three-Tier Fallback Strategy**:

1. **Tier 1 (Plain HTTP):** Executes direct requests via `requests.Session` with template variable interpolation and cookie transforms (`strip-quotes`).
2. **Tier 2 (Browser-Assisted):** If Tier 1 encounters Cloudflare challenges or authentication gates, falls back to Playwright.
3. **Response Extraction:** Extracts target JSON objects using dot-notation (`data.jobBoard.jobPostings`, `elements[*].items[*]`).

### Usage in Code:
```python
from tools.spec_runner import SpecRunner

runner = SpecRunner("tools/api_anything/sites/ashby.json")
result = runner.execute("listJobs", params={"company": "openai"})
print(result)
```

---

## 3. High-Feasibility Implementations in Core Handlers

1. **[`handlers/wellfound.py`](file:///d:/Projects/job_scraper_project/handlers/wellfound.py):** Upgraded with a Tier 1 HTTP extractor (`__NEXT_DATA__` extraction via direct GET) that executes in milliseconds, with transparent fallback to Tier 2 Playwright if blocked.
2. **[`handlers/linkedin.py`](file:///d:/Projects/job_scraper_project/handlers/linkedin.py):** Upgraded to support LinkedIn Voyager API (using `li_at` and `JSESSIONID` from `tools/api_anything/sites/linkedin.json`) and public guest job search, removing mandatory reliance on paid Apify credits.

