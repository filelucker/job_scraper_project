# Job Scraper Pipeline 🔔

A modular, production-ready Python job scraper that monitors company job boards on **Greenhouse** and **Lever**, filters new postings by customizable technology stack keywords, and routes real-time alerts to **Telegram** and **Google Sheets** via **GitHub Actions**.

---

## Features

- 🧩 **Modular ATS Architecture**: Built-in support for Greenhouse and Lever APIs, with an extensible [FallbackHandler](file:///d:/Projects/job_scraper_project/handlers/fallback.py#L8) for generic XML/RSS feeds and unsupported applicant tracking systems.
- 🔍 **Smart Title Filtering**: Employs case-insensitive, regex-based whole-word matching to capture specific technologies (e.g., matching "Android" or "AI/ML" without matching unrelated words).
- 🕒 **Lookback Validation**: Only collects listings posted or updated within a customizable window (defaults to the last 24 hours).
- 📊 **Google Sheets Integration**: Automatically appends job matches to a designated Google Sheet worksheet using a Google Service Account key, dynamically initializing column headers if the worksheet is new.
- 💬 **Telegram Notifications**: Dispatches formatted markdown alerts to a Telegram chat or channel, with built-in message splitting to respect Telegram's 4096-character limit.
- 🛡️ **Fault-Tolerant execution**: Handles API network failures gracefully; a failure on one company's board will not crash the entire scraping process.
- ⚙️ **Automated Pipeline**: Out-of-the-box GitHub Actions workflow to run the pipeline automatically on a daily cron schedule or via manual trigger.

---

## Codebase Architecture

The project is structured with high modularity in mind. Below is an overview of the key files and classes:

*   **Main Entrypoint**:
    *   [run_pipeline.py](file:///d:/Projects/job_scraper_project/run_pipeline.py): Orchestrates the scraping process, iterates over boards defined in configuration, executes handlers, and routes matched jobs to designated channels.
*   **Configuration**:
    *   [config.py](file:///d:/Projects/job_scraper_project/config.py): Contains the list of target search `KEYWORDS`, the lookback time limit, the `COMPANY_BOARDS` mapping registry, and credential loading variables.
*   **Handlers (`handlers/`)**:
    *   [handlers/base.py](file:///d:/Projects/job_scraper_project/handlers/base.py): Definess the core [Job](file:///d:/Projects/job_scraper_project/handlers/base.py#L5) model and the abstract [BaseHandler](file:///d:/Projects/job_scraper_project/handlers/base.py#L28) orchestrator.
    *   [handlers/greenhouse.py](file:///d:/Projects/job_scraper_project/handlers/greenhouse.py): Contains [GreenhouseHandler](file:///d:/Projects/job_scraper_project/handlers/greenhouse.py#L6), which queries the Greenhouse public board API.
    *   [handlers/lever.py](file:///d:/Projects/job_scraper_project/handlers/lever.py): Contains [LeverHandler](file:///d:/Projects/job_scraper_project/handlers/lever.py#L6), which queries Lever's mode-JSON API.
    *   [handlers/fallback.py](file:///d:/Projects/job_scraper_project/handlers/fallback.py): Contains [FallbackHandler](file:///d:/Projects/job_scraper_project/handlers/fallback.py#L8), supporting standard XML/RSS feed parsing.
*   **Routers (`routers/`)**:
    *   [routers/sheets.py](file:///d:/Projects/job_scraper_project/routers/sheets.py): Implements [GoogleSheetsRouter](file:///d:/Projects/job_scraper_project/routers/sheets.py#L7) using `gspread` to authenticate and write rows.
    *   [routers/telegram.py](file:///d:/Projects/job_scraper_project/routers/telegram.py): Implements [TelegramRouter](file:///d:/Projects/job_scraper_project/routers/telegram.py#L4) to build and send escaped markdown messages.
*   **Workflows**:
    *   [.github/workflows/job_scraper.yml](file:///d:/Projects/job_scraper_project/.github/workflows/job_scraper.yml): Defines the GitHub Actions pipeline.
*   **Dependencies**:
    *   [requirements.txt](file:///d:/Projects/job_scraper_project/requirements.txt): Lists required packages (`requests`, `gspread`, `google-auth`, `python-dotenv`).

---

## Setup Instructions

### 1. Prerequisites
- **Python**: v3.11 or higher.
- **Google Cloud Platform (GCP) Project** (for Google Sheets integration).
- **Telegram Bot** (for push alerts).

### 2. Installation
Clone the repository and install the Python dependencies:
```bash
pip install -r requirements.txt
```

### 3. Local Environment Configuration
Create a `.env` file in the root directory:
```env
# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_or_channel_id

# Google Sheets Configuration
# Pass either the file path to service_account.json OR the raw stringified JSON content
GOOGLE_CREDENTIALS_JSON=path/to/your/service_account.json
GOOGLE_SHEET_NAME="Job Scraper Results"
GOOGLE_WORKSHEET_NAME="Jobs"
```

> [!NOTE]
> If any of the variables (like `GOOGLE_CREDENTIALS_JSON` or `TELEGRAM_BOT_TOKEN`) are omitted or left blank, that specific router will automatically bypass during execution, letting you run the scraper with only one routing channel or console logs.

---

## Integration Configuration Guides

### Google Sheets Router Configuration
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project and enable the **Google Sheets API** and **Google Drive API**.
3. Create a **Service Account** under *IAM & Admin > Service Accounts*.
4. Generate a new **JSON Key** for your service account and download the file.
5. Create a Google Sheet, name it (e.g. `Job Scraper Results`), and **share edit access** with the client email address found inside your service account JSON file.
6. Provide the JSON file path or its raw string content as `GOOGLE_CREDENTIALS_JSON` in your `.env` file.

### Telegram Router Configuration
1. Start a conversation with `@BotFather` on Telegram.
2. Run `/newbot` and follow the steps to obtain your **Bot Token**.
3. Create a chat/group/channel, invite your new bot, and make sure the bot has send-message permissions.
4. Retrieve your **Chat ID** (you can use bots like `@userinfobot` or fetch updates via `https://api.telegram.org/bot<YourBotToken>/getUpdates` after messaging your bot).

---

## Usage

### Run Locally
To run the job scraper pipeline locally:
```bash
python run_pipeline.py
```

### Run Tests
To run the project unit tests locally:
```bash
python -m unittest tests/test_pipeline.py
```

### Modifying Job Boards
To add or remove target boards, modify the `COMPANY_BOARDS` dictionary in [config.py](file:///d:/Projects/job_scraper_project/config.py):
```python
COMPANY_BOARDS = {
    # Greenhouse API board
    "Hubspot": {"ats": "greenhouse", "token": "hubspot"},
    # Lever API board
    "Zapier": {"ats": "lever", "token": "zapier"},
    # Custom/Fallback RSS board
    "Custom Company": {"ats": "fallback", "token": "https://company.com/feed.xml"},
}
```

---

## GitHub Actions Automation

The scraper comes pre-configured to run automatically.
1. Commit the repository to GitHub.
2. In your GitHub repository, go to **Settings > Secrets and variables > Actions**.
3. Add the following **Repository Secrets**:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `GOOGLE_CREDENTIALS_JSON` (copy-paste the *entire content* of the service account JSON key file)
   - `GOOGLE_SHEET_NAME` (Optional, defaults to `"Job Scraper Results"`)
   - `GOOGLE_WORKSHEET_NAME` (Optional, defaults to `"Jobs"`)

The action in [.github/workflows/job_scraper.yml](file:///d:/Projects/job_scraper_project/.github/workflows/job_scraper.yml) will trigger:
- Automatically at **08:00 UTC** every day.
- On-demand via the **Run workflow** button on the GitHub Actions tab.
