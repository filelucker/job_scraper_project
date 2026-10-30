# Autonomous Job Scraper & AI Auto-Apply Pipeline 🚀

A modular, enterprise-grade Python automation engine that concurrently scans **1,000+ top company career boards and global aggregators**, matches listings using compound keyword rules, generates **custom-tailored LaTeX resumes on the fly**, and applies automatically across multiple channels (**Direct ATS APIs, SMTP Email, and Playwright Web Form Agents with Cloudflare Turnstile evasion**).

Matches and application statuses are synced in real time to **Google Sheets** and dispatched to **Telegram** alongside tailored CV PDFs and form preview screenshots.

---

## Key Features

- 🧩 **Comprehensive Multi-ATS & Aggregator Network**:
  - **Native ATS APIs**: Greenhouse, Lever, Ashby, Workday, Workable, SmartRecruiters.
  - **Job Platforms & Curated Boards**: LinkedIn (Apify), Indeed (Apify), Arbeitnow, WeAreDevelopers, Relocate.me, FlexJobs, Adzuna, Jooble.
  - **Jobhive Adapter Integration**: Extends coverage to Breezy, BambooHR, Personio, Rippling, BuiltIn, Wanted (APAC), Programathor, and hundreds more.
  - **Fallback XML/RSS Handler**: Gracefully consumes custom company RSS/XML feeds.
- 🎯 **Advanced Compound & Context Matching**:
  - High-precision whole-word title matching (e.g. `Flutter`, `Android`, `iOS`, `AI Mobile Developer`).
  - Compound rule evaluation pairing titles with contextual benefits (e.g. matching `Senior Android Developer` + `visa sponsorship` or `relocation`).
  - Intelligent location filtering (`ONLY_REMOTE_OR_HYBRID`) with international remote detection.
- 🤖 **AI-Powered Resume Tailoring**:
  - Dynamically customizes master LaTeX resume templates ([templates/resume_template.tex](file:///d:/Projects/job_scraper_project/templates/resume_template.tex)) to match job descriptions using **Gemini** or **OpenAI** (with built-in smart heuristic fallback).
  - High-speed headless compilation to PDF using **Tectonic** or **pdfLaTeX**.
- 📬 **Unified Auto-Apply Dispatcher (`AutoApplyDispatcher`)**:
  - **Greenhouse Candidate API**: Direct headless application submission with tailored PDF upload.
  - **Lever Postings API**: Programmatic direct application dispatch.
  - **Email Router**: Sends personalized cover letters and PDF attachments via SMTP.
  - **Playwright Universal Web Form Agent**: Inspects unknown web application forms, answers questions using candidate profiles ([data/candidate_profile.json](file:///d:/Projects/job_scraper_project/data/candidate_profile.json)), attaches tailored PDFs, and captures review screenshots.
- 🛡️ **Anti-Bot Stealth & Cloudflare Turnstile Evasion**:
  - Persistent Chromium context (`PLAYWRIGHT_USER_DATA_DIR`) preserving cookies and `cf_clearance` tokens.
  - Anti-detection script injection (`--disable-blink-features=AutomationControlled`, prototype cleanup).
  - Free behavioral Turnstile resolver (cross-origin frame inspection and humanized coordinate clicks).
  - Optional automated token resolution via **CapSolver** or **2Captcha** API.
- 📊 **Google Sheets Live Tracking & Deduplication**:
  - Queries Google Sheets before processing to deduplicate existing URLs.
  - Logs application channels, timestamps (BST), and real-time statuses (`Applied`, `Drafted (Review Required)`, `Simulated`, `Failed`).
- 💬 **Telegram Push Notifications**:
  - Formatted alert cards with direct job links, company names, and locations.
  - Sends inline full-page preview screenshots and attaches compiled tailored CV PDFs directly to the chat.
- ⚡ **Concurrent & Resilient Architecture**:
  - Multi-threaded board scanning (configurable thread pools up to 10+ workers).
  - Network timeouts and individual board errors are isolated without interrupting the pipeline.
  - Ready for daily automated execution via **GitHub Actions**.

---

## Architecture Overview

```
job_scraper_project/
├── run_pipeline.py                 # Main CLI entrypoint orchestrating scan, tailor, and dispatch
├── config.py                       # Keywords, compound rules, company boards, and environment config
├── handlers/                       # Modular board & ATS scrapers
│   ├── base.py                     # BaseHandler abstract class and Job data model
│   ├── greenhouse.py               # Greenhouse API scraper
│   ├── lever.py                    # Lever JSON API scraper
│   ├── ashby.py                    # Ashby posting API scraper
│   ├── workday.py                  # Workday CXS scraper
│   ├── workable.py                 # Workable widget API scraper
│   ├── smartrecruiters.py          # SmartRecruiters postings API scraper
│   ├── linkedin.py                 # LinkedIn scraper via Apify
│   ├── indeed.py                   # Indeed scraper via Apify
│   ├── arbeitnow.py                # Arbeitnow tech board scraper
│   ├── wearedevelopers.py          # WeAreDevelopers scraper
│   ├── relocateme.py               # Relocate.me RSS scraper
│   ├── flexjobs.py                 # FlexJobs search scraper
│   ├── adzuna.py & jooble.py       # Global aggregator API handlers
│   ├── jobhive_adapter.py          # Adapter bridge for jobhive-py scrapers
│   └── fallback.py                 # Generic RSS/XML feed scraper
├── services/                       # Application & automation services
│   ├── apply_dispatcher.py         # Routes jobs to Greenhouse, Lever, Browser, or Email
│   ├── apply_greenhouse.py         # Headless Greenhouse API direct applier
│   ├── apply_lever.py              # Headless Lever API direct applier
│   ├── apply_browser.py            # Playwright browser agent with persistent profile
│   ├── form_agent.py               # AI dynamic form inspection and question answering
│   ├── captcha_solver.py           # Turnstile, reCAPTCHA v2 audio, and hCaptcha solver
│   ├── compiler.py                 # LaTeX compilation via Tectonic / pdflatex
│   ├── profile_loader.py           # Candidate profile reader
│   └── url_resolver.py             # Unrolls aggregators to canonical direct career links
├── ai/
│   └── tailor.py                   # AI resume tailoring engine (Gemini / OpenAI / Heuristics)
├── routers/                        # Notification and storage sinks
│   ├── sheets.py                   # Google Sheets live tracker with URL deduplication
│   ├── telegram.py                 # Telegram notification router with photo & document support
│   └── email_router.py             # SMTP email application dispatcher
├── templates/
│   └── resume_template.tex         # Master LaTeX CV template
├── data/
│   └── candidate_profile.json      # Structured candidate background, skills, and answers
└── tests/                          # Comprehensive unit test suite (37+ tests)
```

---

## Application Channels & Modes

When `AUTO_APPLY_ENABLED=true`, the `AutoApplyDispatcher` inspects each new job and determines the best channel:

| Channel | Detection Criteria | Behavior |
| :--- | :--- | :--- |
| **GREENHOUSE** | `boards.greenhouse.io` or `job-boards.greenhouse.io` | Posts candidate profile + tailored PDF directly to Greenhouse API. |
| **LEVER** | `jobs.lever.co` | Submits application payload + tailored PDF directly to Lever API. |
| **EMAIL** | Email extracted from job post description | Dispatches personalized cover email + tailored PDF via SMTP. |
| **BROWSER** | Other web career pages / platforms | Opens Playwright browser, evades Turnstile, fills form fields, captures screenshot. |

### Operational Modes (`AUTO_APPLY_MODE`)

1. **`review` (Recommended Default)**:
   - Generates tailored CV PDF and pre-fills form fields (or simulates submission).
   - Captures a preview screenshot and sends the card, screenshot, and PDF to Telegram for human sign-off.
   - Sets Google Sheets status to `Drafted (Review Required)`.
2. **`auto`**:
   - Fully automated end-to-end submission.
   - Submits through Greenhouse/Lever API or clicks Submit in Playwright browser.
   - Sends confirmation card to Telegram and marks status as `Applied`.
3. **`dry_run`**:
   - Simulates the entire process without sending live emails or submitting web forms.

---

## Anti-Bot & Cloudflare Turnstile Evasion

The browser automation engine ([services/apply_browser.py](file:///d:/Projects/job_scraper_project/services/apply_browser.py)) and solver ([services/captcha_solver.py](file:///d:/Projects/job_scraper_project/services/captcha_solver.py)) feature multi-layer defenses against Cloudflare Turnstile and bot management:

- **Persistent Browser Profile**: Stores session cookies, local storage, and `cf_clearance` clearance cookies in `output_resumes/browser_profile`.
- **Headed / Headless Mode**: Configurable via `BROWSER_HEADLESS=false` (defaults to headful locally for maximum trust score).
- **Stealth Automation Flags**: Automatically sets `--disable-blink-features=AutomationControlled`, removes `navigator.webdriver` from prototypes, and mocks Chrome runtime permissions.
- **Turnstile Frame & Coordinate Clicker**: Scans cross-origin `challenges.cloudflare.com` frames and clicks the verification box using randomized human mouse curves.
- **Optional CapSolver / 2Captcha Fallback**: If running on a cloud server or datacenter IP where Cloudflare blocks behavioral clicks, set `CAPSOLVER_API_KEY` or `TWOCAPTCHA_API_KEY` to solve challenges automatically via API.

---

## Installation & Setup

### 1. Prerequisites
- **Python**: v3.11 or higher
- **LaTeX Engine (Optional for CV compilation)**: Install [Tectonic](https://tectonic-typesetting.github.io/) or `pdflatex` (e.g. MiKTeX on Windows / TeX Live on Linux).

### 2. Clone and Install Dependencies
```bash
git clone https://github.com/filelucker/job_scraper_project.git
cd job_scraper_project

# Install Python requirements
pip install -r requirements.txt

# Install Playwright browser binaries
playwright install chromium
```

### 3. Environment Configuration (`.env`)
Create a `.env` file in the root directory (refer to [.env.example](file:///d:/Projects/job_scraper_project/.env.example)):

```ini
# ==========================================
# Telegram Alerts
# ==========================================
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_or_channel_id

# ==========================================
# Google Sheets Live Tracking
# ==========================================
# Path to service_account.json OR raw JSON string
GOOGLE_CREDENTIALS_JSON=service_account.json
GOOGLE_SHEET_NAME="Job Scraper Results"
GOOGLE_WORKSHEET_NAME="Jobs"

# ==========================================
# Aggregator & Search Tokens (Optional)
# ==========================================
APIFY_API_TOKEN=your_apify_token           # For LinkedIn & Indeed scrapers
APIFY_LINKEDIN_LOCATION=Remote
APIFY_INDEED_LOCATION=Remote
APIFY_INDEED_COUNTRY=US

# ==========================================
# Auto-Apply & Resume Tailoring Settings
# ==========================================
AUTO_APPLY_ENABLED=true
AUTO_APPLY_MODE=auto                      # 'auto', 'review', or 'dry_run'
DRY_RUN=false
GEMINI_API_KEY=your_gemini_api_key        # Optional: AI tailoring & field answering
OPENAI_API_KEY=your_openai_api_key        # Optional: Fallback AI provider

# SMTP Email Application
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password
SENDER_NAME="Your Name"

# ==========================================
# Anti-Bot & Browser Automation
# ==========================================
BROWSER_HEADLESS=false                    # Run headed locally to pass Cloudflare easily
PLAYWRIGHT_USER_DATA_DIR=output_resumes/browser_profile

# Optional Paid CAPTCHA Solvers (For cloud servers / datacenter IPs)
# CAPSOLVER_API_KEY=your_capsolver_key
# TWOCAPTCHA_API_KEY=your_2captcha_key

# ==========================================
# Lookback Window
# ==========================================
JOB_LOOKBACK_HOURS=6                      # Only scan postings from the last 6 hours
```

---

## Customizing Your Profile & Criteria

1. **Target Keywords & Rules**: Edit `KEYWORDS`, `COMPOUND_RULES`, and `ONLY_REMOTE_OR_HYBRID` in [config.py](file:///d:/Projects/job_scraper_project/config.py).
2. **Candidate Information**: Update [data/candidate_profile.json](file:///d:/Projects/job_scraper_project/data/candidate_profile.json) with your contact info, skills, GitHub/LinkedIn links, and answers to common screening questions.
3. **Master CV**: Edit [templates/resume_template.tex](file:///d:/Projects/job_scraper_project/templates/resume_template.tex) to customize your base resume sections.

---

## Usage

### Run the Pipeline Locally
```bash
python run_pipeline.py
```

### Run Unit Tests
```bash
python -m unittest discover tests
```

---

## GitHub Actions Automated Deployment

The repository includes a ready-to-use GitHub Actions workflow in [.github/workflows/job_scraper.yml](file:///d:/Projects/job_scraper_project/.github/workflows/job_scraper.yml):

1. Push your repository to GitHub.
2. In your GitHub repository, navigate to **Settings > Secrets and variables > Actions**.
3. Add your environment variables as secrets (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `GOOGLE_CREDENTIALS_JSON`, etc.).
4. The workflow runs automatically on a scheduled cron or on-demand via the **Run workflow** button.

---

## License

This project is licensed under the [MIT License](LICENSE).
