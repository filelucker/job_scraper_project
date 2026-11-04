# Autonomous Job Scraper & AI Auto-Apply Pipeline

## System Overview

A modular, enterprise-grade Python automation engine that concurrently scans **2,780+ top company career boards and global aggregators**, matches listings using compound keyword rules, generates **custom-tailored LaTeX resumes on the fly**, and applies automatically across multiple channels (**Direct Applicant Tracking System (ATS) APIs, SMTP Email, and Playwright Web Form Agents with Cloudflare Turnstile evasion**).

Matches and application statuses are synced in real time to **Google Sheets** with 12-hour Bangladesh Standard Time (BST, UTC+6) timestamps. Notifications, tailored CV PDFs, and form preview screenshots for items requiring review, manual action, or encountering errors are dispatched to **Telegram**, followed by a consolidated pipeline execution summary upon run completion.

---

## Local Interface & Invariants

### Root Scripts & Configuration

- `run_pipeline.py`: Main CLI entrypoint orchestrating board discovery, resume tailoring, and multi-channel application dispatch.
  - `main()`: Orchestrates the scan-tailor-apply workflow:
    - Spawns concurrent thread pools (up to 10 workers) across `COMPANY_BOARDS`.
    - Deduplicates matching jobs by normalized URL across boards.
    - Queries Google Sheets and local state (`scraped_jobs.json`) to identify `new_jobs`.
    - Enforces a 15-minute runtime safety budget (`PIPELINE_MAX_RUN_SECONDS = 900`) to prevent Continuous Integration (CI) runner timeouts.
    - Routes applications through `AutoApplyDispatcher`.
    - Persists statuses and 12-hour BST timestamps to Google Sheets.
    - Emits alert cards, preview screenshots, and run summaries to Telegram.
  - `fetch_board(company_name: str, board_config: dict)`: Worker function scanning an individual company ATS or aggregator board, returning `(company_name, matched_jobs, status, error)`.
  - `class TeeLogger`: Multiplexes stdout and stderr streams to console and `pipeline.log`.
- `config.py`: Centralized configuration defining search criteria, ATS board slugs, and runtime flags.
  - `KEYWORDS`: Target whole-word matching phrases (e.g. `Flutter`, `Android`, `iOS`, `AI Mobile Developer`).
  - `COMPOUND_RULES`: Advanced boolean rules requiring title keywords AND context keywords (e.g. visa sponsorship, relocation).
  - `JOB_LOOKBACK_HOURS`: Publication window (default: `6` hours).
  - `ONLY_REMOTE_OR_HYBRID`: Geography filter restricting matches to remote, hybrid, EU, or UAE locations.
  - `COMPANY_BOARDS`: Dictionary of 2,780+ companies mapped to ATS platform types and public board slugs (e.g. Greenhouse board slug `reddit`, Lever slug `anyscale`).
  - Runtime flags: `AUTO_APPLY_ENABLED`, `AUTO_APPLY_MODE` (`auto`, `review`, `dry_run`), `BROWSER_HEADLESS`, `DRY_RUN`.

### Local Invariants

- `run_pipeline.py` terminates with exit code `0` on successful completion or graceful batch timeout, and exit code `1` with Telegram alert dispatch on unhandled fatal exceptions.
- `TeeLogger` guarantees all standard output and error streams are simultaneously emitted to console and flushed to `pipeline.log`.
- Board scanning concurrency is bounded to a maximum of 10 worker threads; transient scraper exceptions are isolated per board without crashing the orchestrator.

---

## Subdirectories & System Boundaries

- [ai](./ai/README.md): AI-powered resume tailoring engine utilizing Google Gemini or OpenAI with deterministic rule-based heuristic fallback. Generates customized LaTeX summaries, competencies, skills, and pitch emails.
- [handlers](./handlers/README.md): Modular scraping adapters, data models (`Job`, `BaseHandler`), and routing services (`JobEmailExtractor`) querying 2,780+ direct ATS boards, curated remote platforms, and aggregators.
- [routers](./routers/README.md): External integration sinks managing Google Sheets live tracking (`GoogleSheetsRouter`), Telegram push notifications and document uploads (`TelegramRouter`), and SMTP email dispatch (`EmailRouter`).
- [services](./services/README.md): Core execution services including multi-channel routing (`AutoApplyDispatcher`), direct ATS appliers (Greenhouse, Lever), Playwright browser agent (`PlaywrightBrowserApplier`), dynamic form inspection (`FormAgent`), CAPTCHA evasion (`CaptchaSolver`), LaTeX compilation (`LatexCompiler`), and canonical URL resolution (`UrlResolver`).
- [templates](./templates/resume_template.tex): Master LaTeX CV template dynamically tailored per job listing.
- [tests](./tests/): Comprehensive unit test suite covering pipeline orchestration, handlers, auto-apply dispatchers, and CAPTCHA solvers.
- [.github](./.github/workflows/job_scraper.yml): Continuous Integration (CI) and automated scheduled deployment workflows.

---

## Global Invariants

- **Verified Submission Statuses**: Every application attempt is categorized by channel outcome. Genuinely completed applications receive `Applied (Greenhouse API)`, `Applied (Lever API)`, `Applied (Direct Email)`, or `Applied (Web Portal)` (verified form completion via Playwright agent). Login-gated aggregators (Indeed, LinkedIn, Glassdoor) or blocked forms receive `Requires Manual Apply (...)` with a tailored CV dispatched to Telegram. In `review` mode, processed applications receive `Drafted (Preview Generated)`.
- **Strict Deduplication**: All discovered job listings must be normalized and deduplicated across existing Google Sheets records, local state cache (`scraped_jobs.json`), and the active run batch before queueing for auto-apply.
- **CI Runtime Safety Guard**: The pipeline enforces a 15-minute runtime ceiling (`PIPELINE_MAX_RUN_SECONDS = 900`). If exceeded, remaining unapplied jobs in the queue receive the terminal status `Applied (Portal Dispatched - Batch Limit)` with direct application links dispatched to Telegram, gracefully releasing CI runner resources while preventing infinite re-queueing in subsequent runs.
- **Compiler Circuit Breaker**: `LatexCompiler` limits Tectonic compilation to 15 seconds. If a timeout occurs or Tectonic is unavailable, further compilation attempts for the run are disabled, falling back to [`master_resume.pdf`](./master_resume.pdf) to preserve execution budget.
- **Timezone Consistency**: All timestamped records stored in Google Sheets use Bangladesh Standard Time (BST, UTC+6) in 12-hour AM/PM format, while internal `Job` representations and log outputs maintain UTC+6 timestamps.

---

## Global Side Effects

- **Network Access**: Outbound HTTPS requests to 2,780+ ATS APIs, Google Sheets API, Telegram Bot API, Gemini/OpenAI endpoints, and SMTP servers.
- **Filesystem Persistence**: Generates tailored resume PDFs in `output_resumes/`, saves browser automation screenshots in `output_resumes/screenshots/`, stores local cache in `scraped_jobs.json`, and records logs in `pipeline.log`.
- **Browser Automation**: Launches headless Chromium instances via Playwright with user data persistence in `output_resumes/browser_profile`.
- **External State Mutation**: Appends and updates rows in the target Google Sheet and sends notifications/files to Telegram.

---

## System Verification

- Run all unit tests:
  ```bash
  python -m unittest discover tests
  ```

---

## Key Features & Architecture

```text
job_scraper_project/
├── run_pipeline.py                 # Main CLI entrypoint orchestrating scan, tailor, and dispatch
├── config.py                       # Keywords, compound rules, company boards, and environment config
├── candidate_profile.json          # Structured candidate profile & screening answers
├── master_resume.pdf               # Static fallback PDF resume
├── README.md                       # Repository Blueprint & Architecture Guide
├── ai/                             # [Component Package] Resume tailoring engine
│   ├── tailor.py
│   └── README.md
├── handlers/                       # [Component Package] Modular board & ATS scrapers
│   ├── base.py
│   ├── email_extractor.py
│   ├── greenhouse.py / lever.py / ashby.py / workable.py / workday.py / smartrecruiters.py
│   ├── remoteok.py / landingjobs.py / themuse.py / hackernews.py / himalayas.py
│   ├── remotive.py / jobicy.py / workingnomads.py / weworkremotely.py
│   ├── arbeitnow.py / wearedevelopers.py / germantechjobs.py / relocateme.py / wellfound.py
│   ├── indeed.py / linkedin.py / adzuna.py / jooble.py / flexjobs.py / fallback.py
│   └── README.md
├── routers/                        # [Component Package] Notification & storage sinks
│   ├── sheets.py
│   ├── telegram.py
│   ├── email_router.py
│   └── README.md
├── services/                       # [Component Package] Application & automation services
│   ├── apply_dispatcher.py
│   ├── apply_greenhouse.py / apply_lever.py
│   ├── apply_browser.py
│   ├── form_agent.py
│   ├── captcha_solver.py
│   ├── compiler.py
│   ├── profile_loader.py / url_resolver.py
│   └── README.md
├── templates/
│   └── resume_template.tex         # Master LaTeX CV template
├── tests/                          # 50 unit tests across pipeline, auto-apply, and solver suites
│   ├── test_pipeline.py
│   ├── test_auto_apply.py
│   ├── test_automation.py
│   └── test_captcha_solver.py
└── .github/
    └── workflows/
        └── job_scraper.yml         # GitHub Actions automated scheduled pipeline
```

---

## Installation & Setup

### Prerequisites

- **Python**: v3.11 or higher
- **LaTeX Engine (Optional)**: [Tectonic](https://tectonic-typesetting.github.io/) (modern, self-contained LaTeX engine; automated compilation skips gracefully to `master_resume.pdf` if absent).

### Clone and Install Dependencies

```bash
git clone https://github.com/filelucker/job_scraper_project.git
cd job_scraper_project

# Install Python requirements
pip install -r requirements.txt

# Install Playwright browser binaries
playwright install chromium
```

### Candidate Profile Configuration

Ensure [`candidate_profile.json`](./candidate_profile.json) is populated at the project root. This file provides the structured data source used by `ResumeTailor` to customize LaTeX resumes and by `FormAgent` to answer screening questions (name, email, phone, location, portfolio URLs, work authorization, years of experience, and salary expectations).

### Environment Configuration (`.env`)

Create a `.env` file in the root directory (refer to [`.env.example`](./.env.example)):

```ini
# Telegram Alerts
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_or_channel_id

# Google Sheets Live Tracking
# Place your Google Cloud service_account.json in the project root and share the spreadsheet with the service account email
GOOGLE_CREDENTIALS_JSON=service_account.json
GOOGLE_SHEET_NAME="Job Scraper Results"
GOOGLE_WORKSHEET_NAME="Jobs"

# Auto-Apply & Resume Tailoring Settings
AUTO_APPLY_ENABLED=true
# Options: 'auto' (fully automated submission), 'review' (pre-fills form and saves preview screenshot & CV to Telegram), 'dry_run' (simulates API calls)
AUTO_APPLY_MODE=auto
DRY_RUN=false
GEMINI_API_KEY=your_gemini_api_key        # Optional: AI tailoring & field answering
OPENAI_API_KEY=your_openai_api_key        # Optional: Fallback AI provider

# SMTP Email Application
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password
SENDER_NAME="Md Moniruzzaman"

# Anti-Bot & Browser Automation
BROWSER_HEADLESS=true
PLAYWRIGHT_USER_DATA_DIR=output_resumes/browser_profile
# Optional paid CAPTCHA solvers (fallback for Turnstile/reCAPTCHA on datacenter IPs)
CAPSOLVER_API_KEY=your_capsolver_key
TWOCAPTCHA_API_KEY=your_2captcha_key

# Pipeline Safety & Lookback Window
PIPELINE_MAX_RUN_SECONDS=900              # Maximum pipeline execution ceiling in seconds (15 mins)
JOB_LOOKBACK_HOURS=6                      # Scan postings from the last 6 hours
```

---

## Usage

### Run the Pipeline Locally

```bash
python run_pipeline.py
```

### Run Unit Tests

Execute the canonical verification command:
```bash
python -m unittest discover tests
```

---

## GitHub Actions Automated Deployment

The repository includes an automated workflow in [`.github/workflows/job_scraper.yml`](./.github/workflows/job_scraper.yml) executing every 6 hours (`0 */6 * * *`) or via manual dispatch:

1. Push your repository to GitHub.
2. In your repository, go to **Settings > Secrets and variables > Actions**.
3. Add your repository secrets:
   - `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`
   - `GOOGLE_CREDENTIALS_JSON` (raw service account JSON string)
   - `GEMINI_API_KEY` or `OPENAI_API_KEY`
   - `SMTP_USER` and `SMTP_PASSWORD` (if using email application)
   - `CAPSOLVER_API_KEY` (if using paid CAPTCHA solving)
4. The workflow runs on Ubuntu with `xvfb-run` (X Virtual Framebuffer, providing the virtual X11 display context required by Playwright browser agents on headless Linux) and uploads tailored resumes as run artifacts.

---

## License

This project is licensed under the MIT License.
