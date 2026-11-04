# handlers

## Overview
The `handlers` component package contains the data models and modular scraping adapters for querying company Applicant Tracking Systems (ATS), job aggregation APIs, and RSS feeds. It provides a unified extraction pipeline: fetching raw listings, standardizing records into `Job` objects, performing URL normalization, and filtering by publication lookback window, keyword/compound rule boundaries, and location constraints.

## Interface
- `class Job`: Core standardized data model representing a job posting.
  - Attributes: `company: str`, `title: str`, `location: str`, `url: str`, `posted_time: datetime`, `description: str`, `tags: List[str]`, `has_visa_sponsorship: bool`, `has_relocation: bool`.
  - `normalize_url(url: str) -> str`: Strips marketing UTMs, tracking parameters, and localized paths while preserving canonical listing IDs (`jk` for Indeed, `id` for Hacker News, job IDs for LinkedIn).
  - `to_dict() -> Dict[str, Any]`: Formats job into a dictionary mapped to Bangladesh Standard Time (BST) timestamps for Google Sheets and Telegram.
- `class BaseHandler`: Abstract base class defining the scraping and filtering lifecycle.
  - `__init__(company_name: str, token: str, keywords: List[str], lookback_hours: int = 24, only_remote_or_hybrid: bool = False, compound_rules: Optional[List[Dict[str, Any]]] = None)`
  - `fetch_raw_jobs() -> List[Dict[str, Any]]`: Abstract method fetching raw API/feed payloads.
  - `parse_job(raw_job: Dict[str, Any]) -> Optional[Job]`: Abstract method transforming raw payload into a `Job`.
  - `matches_keywords(title: str) -> bool`: Whole-word boundary case-insensitive regex title matching.
  - `matches_compound(job: Job) -> bool`: Evaluates multi-term criteria (e.g. mobile title paired with visa sponsorship or relocation tags).
  - `matches_location(location: str, title: str, job: Optional[Job] = None) -> bool`: Verifies remote, hybrid, or EU/UAE target geography.
  - `is_within_lookback(posted_time: datetime) -> bool`: Filters postings published within the lookback window.
  - `execute() -> List[Job]`: Orchestrates fetch, parse, filter, and in-memory URL deduplication.
- `class JobEmailExtractor`: Application channel analyzer (`email_extractor.py`).
  - `detect_ats_portal(url: str) -> Optional[str]`: Identifies known ATS domains (Greenhouse, Lever, Ashby, Workable, etc.).
  - `extract_emails_from_text(text: str) -> List[str]`: Regex scanner for recruiter contact emails.
  - `select_best_email(emails: List[str]) -> Optional[str]`: Filters out generic/image/support emails.
  - `analyze_job(job: Dict[str, Any]) -> Dict[str, Any]`: Returns `apply_method`, `email`, and `initial_status`.
- Specific Handlers:
  - Native ATS: `GreenhouseHandler`, `LeverHandler`, `AshbyHandler`, `WorkdayHandler`, `WorkableHandler`, `SmartRecruitersHandler`, `JobhiveAdapterHandler`, `FallbackHandler` (RSS/XML).
  - Remote Job Boards: `RemoteOKHandler`, `LandingJobsHandler`, `TheMuseHandler`, `HackerNewsHandler`, `JobspressoHandler`, `CryptoJobsListHandler`, `NoDeskHandler`, `EUStartupsHandler`, `RemotiveHandler`, `HimalayasHandler`, `JobicyHandler`, `WorkingNomadsHandler`, `WeWorkRemotelyHandler`, `ArbeitnowHandler`, `WeAreDevelopersHandler`, `GermanTechJobsHandler`, `RelocateMeHandler`, `WellfoundHandler`.
  - Aggregators: `IndeedHandler`, `LinkedInHandler`, `AdzunaHandler`, `JoobleHandler`, `FlexjobsHandler`.

## Invariants
- `execute()` must always return a deduplicated list of `Job` instances matching all configured filters; duplicate URLs within a single scan batch are dropped.
- URL normalization must be idempotent: `normalize_url(normalize_url(u)) == normalize_url(u)`.
- All `Job.posted_time` values must be timezone-aware (UTC normalized) before comparison in `is_within_lookback`.
- Handlers must swallow transient network, decoding, or HTTP errors internally and return an empty list (`[]`) without terminating orchestrator execution.

## Side Effects
- Outbound HTTP GET/POST network calls across target company careers APIs, RSS feeds, and aggregator endpoints.
- Outbound API calls to Apify REST endpoints when `APIFY_API_TOKEN` is configured for LinkedIn or Indeed scraping.
- No local filesystem modifications.

## Verification
- Run: `python -m unittest tests/test_pipeline.py`

