import os
import sys
import json
import concurrent.futures
from datetime import datetime, timezone, timedelta
from config import (
    KEYWORDS,
    COMPOUND_RULES,
    JOB_LOOKBACK_HOURS,
    ONLY_REMOTE_OR_HYBRID,
    COMPANY_BOARDS,
    LINKEDIN_GLOBAL_LOCATIONS,
    INDEED_GLOBAL_DOMAINS,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    GOOGLE_CREDENTIALS_JSON,
    GOOGLE_SHEET_NAME,
    GOOGLE_WORKSHEET_NAME,
    ADZUNA_APP_ID,
    ADZUNA_APP_KEY,
    JOOBLE_API_KEY,
    APIFY_API_TOKEN,
    APIFY_LINKEDIN_ACTOR,
    APIFY_INDEED_ACTOR,
    APIFY_LINKEDIN_LOCATION,
    APIFY_INDEED_LOCATION,
    APIFY_INDEED_COUNTRY,
    GERMANTECHJOBS_COOKIE,
    JOBCOPILOT_TOKEN,
    RELOCATEME_COOKIE,
    RELOCATEME_FEED_URL,
    AUTO_APPLY_ENABLED,
    AUTO_APPLY_MODE,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
    SENDER_NAME,
    GEMINI_API_KEY,
    OPENAI_API_KEY,
    DRY_RUN
)
from handlers import (
    GreenhouseHandler, LeverHandler, FallbackHandler, AshbyHandler,
    WorkdayHandler, WorkableHandler, SmartRecruitersHandler, JobhiveAdapterHandler,
    AdzunaHandler, JoobleHandler, FlexjobsHandler, LinkedInHandler, IndeedHandler,
    ArbeitnowHandler, WeAreDevelopersHandler, GermanTechJobsHandler, RelocateMeHandler
)
from handlers.email_extractor import JobEmailExtractor
from routers import TelegramRouter, GoogleSheetsRouter, EmailRouter
from ai.tailor import ResumeTailor
from services.compiler import LatexCompiler
from services.apply_dispatcher import AutoApplyDispatcher

# Pre-import key packages to avoid thread import lock contention / deadlocks during concurrent scans
try:
    import anyio
    import httpcore
    import httpx
    try:
        from ats_scrapers.models import ATSType
        from ats_scrapers.scrapers.base import get_scraper
    except ImportError:
        from jobhive.models import ATSType
        from jobhive.scrapers.base import get_scraper
    JOBHIVE_AVAILABLE = True
    JOBHIVE_ATS_TYPES = {t.value for t in ATSType}
except ImportError:
    JOBHIVE_AVAILABLE = False
    JOBHIVE_ATS_TYPES = set()


# --- Monkeypatch requests to limit per-host concurrent connections and add timeout/stagger safeguards ---
import requests
import threading
import time
import random
from collections import defaultdict
from urllib.parse import urlparse

_host_locks = defaultdict(threading.Lock)
_host_counts = defaultdict(int)
MAX_PER_HOST = 2

_original_session_request = requests.Session.request

def _get_host(url):
    try:
        return urlparse(url).hostname or "unknown"
    except Exception:
        return "unknown"

def patched_session_request(self, method, url, *args, **kwargs):
    host = _get_host(url)
    
    # Introduce small random stagger delay to spread requests
    time.sleep(random.uniform(0.1, 0.4))
    
    while True:
        with _host_locks[host]:
            if _host_counts[host] < MAX_PER_HOST:
                _host_counts[host] += 1
                break
        time.sleep(0.2)
        
    try:
        if 'timeout' not in kwargs:
            kwargs['timeout'] = 30
        return _original_session_request(self, method, url, *args, **kwargs)
    finally:
        with _host_locks[host]:
            _host_counts[host] -= 1

requests.Session.request = patched_session_request

class TeeLogger:
    def __init__(self, log_file, original_stream):
        self.log_file = log_file
        self.original_stream = original_stream

    def write(self, data):
        try:
            self.original_stream.write(data)
        except UnicodeEncodeError:
            encoding = getattr(self.original_stream, 'encoding', 'utf-8') or 'utf-8'
            clean_data = data.encode(encoding, errors='replace').decode(encoding)
            self.original_stream.write(clean_data)
        self.log_file.write(data)
        self.log_file.flush()

    def flush(self):
        self.original_stream.flush()
        self.log_file.flush()

def fetch_board(company_name: str, board_config: dict):
    """Worker function to execute a single company's job board scan."""
    ats_type = board_config.get("ats", "").lower()
    token = board_config.get("token", "")

    # Alert users if fallback token is an inactive stub
    if ats_type == "fallback":
        is_rss = token.startswith("http://") or token.startswith("https://") or token.endswith(".xml")
        if not is_rss:
            print(f"[Fallback - {company_name}] Warning: Token '{token}' is not an active RSS URL/file. Skipping stub.", file=sys.stderr)
            return company_name, [], "skipped", None

    # Skip boards requiring missing API keys to prevent logs cluttering
    if ats_type == "usajobs" and not os.getenv("USAJOBS_API_KEY"):
        print(f"[USAJobs - {company_name}] Info: USAJOBS_API_KEY is not set. Skipping board.", file=sys.stderr)
        return company_name, [], "skipped", None

    if ats_type == "wellfound" and not os.getenv("FIRECRAWL_API_KEY"):
        print(f"[Wellfound - {company_name}] Info: FIRECRAWL_API_KEY is not set. Skipping board.", file=sys.stderr)
        return company_name, [], "skipped", None

    if ats_type == "adzuna" and (not ADZUNA_APP_ID or not ADZUNA_APP_KEY):
        print(f"[Adzuna - {company_name}] Info: ADZUNA_APP_ID or ADZUNA_APP_KEY is not set. Skipping board.", file=sys.stderr)
        return company_name, [], "skipped", None

    if ats_type == "jooble" and not JOOBLE_API_KEY:
        print(f"[Jooble - {company_name}] Info: JOOBLE_API_KEY is not set. Skipping board.", file=sys.stderr)
        return company_name, [], "skipped", None

    if ats_type == "linkedin" and (not APIFY_API_TOKEN or APIFY_API_TOKEN.startswith("your_apify_")):
        print(f"[LinkedIn - {company_name}] Info: APIFY_API_TOKEN is not set or is placeholder. Skipping board.", file=sys.stderr)
        return company_name, [], "skipped", None

    if ats_type == "indeed" and (not APIFY_API_TOKEN or APIFY_API_TOKEN.startswith("your_apify_")):
        print(f"[Indeed - {company_name}] Info: APIFY_API_TOKEN is not set or is placeholder. Skipping board.", file=sys.stderr)
        return company_name, [], "skipped", None

    if ats_type == "germantechjobs" and not GERMANTECHJOBS_COOKIE and not JOBCOPILOT_TOKEN:
        print(f"[GermanTechJobs - {company_name}] Info: GERMANTECHJOBS_COOKIE or JOBCOPILOT_TOKEN is not set. Skipping board.", file=sys.stderr)
        return company_name, [], "skipped", None


    # Skip scrapers known to be blocked by cloud anti-bot/WAFs or rate limits to prevent hangs and log spam
    if ats_type in ("jobsch", "flexjobs", "programathor", "wanted", "jobs_cz") and not os.getenv("ENABLE_UNSTABLE_AGGREGATORS"):
        print(f"[{company_name}] Info: Scraper is disabled by default due to cloud anti-bot/WAF blocking. Skipping board.", file=sys.stderr)
        return company_name, [], "skipped", None

    # Skip extremely heavy national public-sector aggregators by default to prevent long runs or hangs
    if ats_type in ("arbetsformedlingen", "bundesagentur", "eures") and not os.getenv("ENABLE_NATIONAL_AGGREGATORS"):
        print(f"[{company_name}] Info: National aggregator is disabled by default to prevent long execution times. Set ENABLE_NATIONAL_AGGREGATORS=1 to enable.", file=sys.stderr)
        return company_name, [], "skipped", None

    # Select the appropriate ATS handler
    # We prefer optimized native handlers first for speed and timeout robustness.
    # We fall back to the Jobhive adapter handler if no native handler is available but Jobhive supports it.
    if ats_type == "greenhouse":
        handler = GreenhouseHandler(company_name, token, KEYWORDS, JOB_LOOKBACK_HOURS, only_remote_or_hybrid=ONLY_REMOTE_OR_HYBRID, compound_rules=COMPOUND_RULES)
    elif ats_type == "lever":
        handler = LeverHandler(company_name, token, KEYWORDS, JOB_LOOKBACK_HOURS, only_remote_or_hybrid=ONLY_REMOTE_OR_HYBRID, compound_rules=COMPOUND_RULES)
    elif ats_type == "ashby":
        handler = AshbyHandler(company_name, token, KEYWORDS, JOB_LOOKBACK_HOURS, only_remote_or_hybrid=ONLY_REMOTE_OR_HYBRID, compound_rules=COMPOUND_RULES)
    elif ats_type == "workday":
        handler = WorkdayHandler(company_name, token, KEYWORDS, JOB_LOOKBACK_HOURS, only_remote_or_hybrid=ONLY_REMOTE_OR_HYBRID, compound_rules=COMPOUND_RULES)
    elif ats_type == "workable":
        handler = WorkableHandler(company_name, token, KEYWORDS, JOB_LOOKBACK_HOURS, only_remote_or_hybrid=ONLY_REMOTE_OR_HYBRID, compound_rules=COMPOUND_RULES)
    elif ats_type == "smartrecruiters":
        handler = SmartRecruitersHandler(company_name, token, KEYWORDS, JOB_LOOKBACK_HOURS, only_remote_or_hybrid=ONLY_REMOTE_OR_HYBRID, compound_rules=COMPOUND_RULES)
    elif ats_type == "arbeitnow":
        handler = ArbeitnowHandler(company_name, token, KEYWORDS, JOB_LOOKBACK_HOURS, only_remote_or_hybrid=ONLY_REMOTE_OR_HYBRID, compound_rules=COMPOUND_RULES)
    elif ats_type == "wearedevelopers":
        handler = WeAreDevelopersHandler(company_name, token, KEYWORDS, JOB_LOOKBACK_HOURS, only_remote_or_hybrid=ONLY_REMOTE_OR_HYBRID, compound_rules=COMPOUND_RULES)
    elif ats_type == "germantechjobs":
        handler = GermanTechJobsHandler(company_name, token, KEYWORDS, JOB_LOOKBACK_HOURS, only_remote_or_hybrid=ONLY_REMOTE_OR_HYBRID, session_cookie=GERMANTECHJOBS_COOKIE, auth_token=JOBCOPILOT_TOKEN, compound_rules=COMPOUND_RULES)
    elif ats_type == "relocateme":
        handler = RelocateMeHandler(company_name, token, KEYWORDS, JOB_LOOKBACK_HOURS, only_remote_or_hybrid=ONLY_REMOTE_OR_HYBRID, session_cookie=RELOCATEME_COOKIE, feed_url=RELOCATEME_FEED_URL, compound_rules=COMPOUND_RULES)
    elif ats_type == "adzuna":
        handler = AdzunaHandler(company_name, token, KEYWORDS, JOB_LOOKBACK_HOURS, only_remote_or_hybrid=ONLY_REMOTE_OR_HYBRID, app_id=ADZUNA_APP_ID, app_key=ADZUNA_APP_KEY, compound_rules=COMPOUND_RULES)
    elif ats_type == "jooble":
        handler = JoobleHandler(company_name, token, KEYWORDS, JOB_LOOKBACK_HOURS, only_remote_or_hybrid=ONLY_REMOTE_OR_HYBRID, api_key=JOOBLE_API_KEY, compound_rules=COMPOUND_RULES)
    elif ats_type == "flexjobs":
        handler = FlexjobsHandler(company_name, token, KEYWORDS, JOB_LOOKBACK_HOURS, only_remote_or_hybrid=ONLY_REMOTE_OR_HYBRID, compound_rules=COMPOUND_RULES)
    elif ats_type == "linkedin":
        handler = LinkedInHandler(
            company_name,
            token,
            KEYWORDS,
            JOB_LOOKBACK_HOURS,
            only_remote_or_hybrid=ONLY_REMOTE_OR_HYBRID,
            apify_api_token=APIFY_API_TOKEN,
            actor_name=APIFY_LINKEDIN_ACTOR,
            location=APIFY_LINKEDIN_LOCATION,
            countries=[{"linkedin_location": loc} for loc in LINKEDIN_GLOBAL_LOCATIONS],
            compound_rules=COMPOUND_RULES
        )
    elif ats_type == "indeed":
        handler = IndeedHandler(
            company_name,
            token,
            KEYWORDS,
            JOB_LOOKBACK_HOURS,
            only_remote_or_hybrid=ONLY_REMOTE_OR_HYBRID,
            apify_api_token=APIFY_API_TOKEN,
            actor_name=APIFY_INDEED_ACTOR,
            location=APIFY_INDEED_LOCATION,
            country=APIFY_INDEED_COUNTRY,
            countries=[{"indeed_domain": dom} for dom in INDEED_GLOBAL_DOMAINS],
            compound_rules=COMPOUND_RULES
        )
    elif JOBHIVE_AVAILABLE and ats_type in JOBHIVE_ATS_TYPES:
        handler = JobhiveAdapterHandler(company_name, token, KEYWORDS, JOB_LOOKBACK_HOURS, ats_type=ats_type, only_remote_or_hybrid=ONLY_REMOTE_OR_HYBRID, compound_rules=COMPOUND_RULES)
    else:
        handler = FallbackHandler(company_name, token, KEYWORDS, JOB_LOOKBACK_HOURS, only_remote_or_hybrid=ONLY_REMOTE_OR_HYBRID, compound_rules=COMPOUND_RULES)

    try:
        matched_jobs = handler.execute()
        return company_name, matched_jobs, "scanned", None
    except Exception as e:
        return company_name, [], "failed", e

def main():
    start_time = datetime.now()
    scanned_boards = []
    skipped_boards = []
    failed_boards = []
    all_matched_jobs = []
    new_jobs = []

    log_filename = "pipeline.log"
    try:
        log_file = open(log_filename, "w", encoding="utf-8")
    except Exception as e:
        print(f"Failed to open log file: {e}", file=sys.stderr)
        return
    
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    sys.stdout = TeeLogger(log_file, original_stdout)
    sys.stderr = TeeLogger(log_file, original_stderr)
    
    try:
        print(f"=== Starting Job Scraper Pipeline at {datetime.now(timezone.utc).isoformat()} ===")
        print(f"Target Keywords: {KEYWORDS}")
        print(f"Lookback Window: {JOB_LOOKBACK_HOURS} hours")
        print(f"Scanning {len(COMPANY_BOARDS)} company job boards...\n")

        # Run scans concurrently in a thread pool to avoid sequential execution bottlenecks.
        # We limit concurrency to 10 to avoid triggering rate-limiting WAF (Cloudflare) blocks.
        max_workers = min(10, len(COMPANY_BOARDS))
        print(f"Scanning boards concurrently with up to {max_workers} threads...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_board = {
                executor.submit(fetch_board, company_name, board_config): company_name
                for company_name, board_config in COMPANY_BOARDS.items()
            }
            
            for future in concurrent.futures.as_completed(future_to_board):
                company_name = future_to_board[future]
                try:
                    company_name, matched_jobs, status, err = future.result()
                    if status == "failed":
                        print(f"[ERROR] Fail-safe caught exception while scanning board for '{company_name}': {err}", file=sys.stderr)
                        failed_boards.append((company_name, str(err)))
                    elif status == "skipped":
                        skipped_boards.append(company_name)
                    else:
                        scanned_boards.append(company_name)
                        if matched_jobs:
                            print(f"[{company_name}] Found {len(matched_jobs)} matching job(s) posted in the last 24 hours!")
                            for job in matched_jobs:
                                print(f"  - {job.title} ({job.location}) -> {job.url}")
                            all_matched_jobs.extend(matched_jobs)
                except Exception as e:
                    print(f"[ERROR] Thread execution failed for '{company_name}': {e}", file=sys.stderr)
                    failed_boards.append((company_name, str(e)))

        print(f"\nScan completed. Found {len(all_matched_jobs)} matching job(s) in total.")

        sheets_active = False

        if all_matched_jobs:
            # Convert matching Job objects to dictionary format
            job_dicts = [job.to_dict() for job in all_matched_jobs]

            # --- Deduplication logic ---
            existing_urls = []

            # 1. Fetch existing URLs from Google Sheets if configured
            if GOOGLE_CREDENTIALS_JSON:
                print("\nChecking existing jobs in Google Sheets for deduplication...")
                try:
                    sheets_router = GoogleSheetsRouter(
                        credentials_json=GOOGLE_CREDENTIALS_JSON,
                        sheet_name=GOOGLE_SHEET_NAME,
                        worksheet_name=GOOGLE_WORKSHEET_NAME
                    )
                    existing_urls = sheets_router.get_existing_urls()
                    sheets_active = True
                    print(f"Found {len(existing_urls)} job URLs already in Google Sheets.")
                except Exception as e:
                    print(f"[ERROR] Exception during Google Sheets check: {e}", file=sys.stderr)
            else:
                print("\nGoogle Sheets credentials not set. Skipping sheets duplication check.")

            # 2. Fetch existing URLs from local state file
            local_state_file = "scraped_jobs.json"
            local_existing_urls = []
            if os.path.exists(local_state_file):
                try:
                    with open(local_state_file, "r") as f:
                        local_existing_urls = json.load(f)
                except Exception as e:
                    print(f"[Warning] Failed to load local state file '{local_state_file}': {e}", file=sys.stderr)

            # Combine Google Sheets & local cache to form a comprehensive deduplication set
            all_existing_urls = set(existing_urls + local_existing_urls)

            # Filter job list to only new listings
            new_jobs = [job for job in job_dicts if job["URL"] not in all_existing_urls]
            print(f"Filtered out {len(job_dicts) - len(new_jobs)} duplicate(s). {len(new_jobs)} new job(s) to process.")
        else:
            print("No matches found. Skipping deduplication and export.")

        # --- Enrich jobs with application method / email detection ---
        if new_jobs:
            print("\nAnalyzing application channels for new jobs...")
            for job in new_jobs:
                analysis = JobEmailExtractor.analyze_job(job)
                job["Contact Email"] = analysis.get("email") or ""
                job["Application Status"] = analysis.get("initial_status", "Pending")
                job["apply_method"] = analysis.get("apply_method", "WEB_PORTAL")
                if job["Contact Email"]:
                    print(f"  • {job.get('Company')} -> Application Email found: {job['Contact Email']}")

        # --- 2. Auto-Apply & Customized CV Pipeline ---
        if new_jobs and AUTO_APPLY_ENABLED:
            print(f"\n[Auto-Apply] Processing {len(new_jobs)} new job(s) via AutoApplyDispatcher in '{AUTO_APPLY_MODE}' mode...")
            try:
                dispatcher = AutoApplyDispatcher(
                    mode=AUTO_APPLY_MODE,
                    gemini_api_key=GEMINI_API_KEY,
                    openai_api_key=OPENAI_API_KEY,
                    smtp_config={
                        "host": SMTP_HOST,
                        "port": SMTP_PORT,
                        "user": SMTP_USER,
                        "password": SMTP_PASSWORD,
                        "sender_name": SENDER_NAME
                    }
                )
            except Exception as init_err:
                print(f"[Auto-Apply] Error initializing dispatcher: {init_err}", file=sys.stderr)
                dispatcher = None

            if dispatcher:
                bst_tz = timezone(timedelta(hours=6))
                for job in new_jobs:
                    company = job.get("Company", "Company")
                    title = job.get("Title", "Job")
                    url = job.get("URL", "")

                    try:
                        res = dispatcher.process_job(job)
                        status_text = res.get("status", "Processed")
                        pdf_path = res.get("pdf_path")
                        channel = res.get("channel", "UNKNOWN")
                        timestamp = datetime.now(bst_tz).strftime("%Y-%m-%d %I:%M:%S %p BST")

                        # Attach status and timestamp to job record for Google Sheets and Telegram
                        job["Status"] = status_text
                        job["status"] = status_text
                        job["Application Status"] = status_text
                        job["Applied At"] = timestamp

                        # Determine if application succeeded automatically without human intervention
                        status_lower = status_text.lower()
                        is_applied = (
                            res.get("success", False)
                            and status_lower.startswith("applied")
                            and not any(x in status_lower for x in ("draft", "fail", "error", "manual"))
                        )

                        if is_applied:
                            print(f"[Auto-Apply] Successfully auto-applied to {company} ({title}) via {channel}. Suppressing Telegram PDF/draft notification as requested.")
                        else:
                            # Auto-apply failed, drafted, or requires manual / human intervention -> send alert + tailored CV PDF to Telegram
                            print(f"[Auto-Apply] Manual action / review needed for {company} ({title}) [Status: {status_text}]. Dispatching draft & tailored PDF to Telegram...")
                            if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                                try:
                                    tg = TelegramRouter(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
                                    tg_msg = tg.format_auto_apply_update(job=job, result=res)
                                    screenshot = res.get("screenshot_path")

                                    # Send screenshot as an inline preview image with the card as its caption
                                    screenshot_sent = False
                                    if screenshot and os.path.exists(screenshot):
                                        screenshot_sent = tg.send_photo(screenshot, caption=tg_msg)

                                    # If no screenshot or photo send failed, send as text card
                                    if not screenshot_sent:
                                        tg.send_message(tg_msg)

                                    # Attach tailored CV PDF so user can manually apply
                                    if pdf_path and os.path.exists(pdf_path):
                                        tg.send_document(pdf_path, caption=f"📄 Tailored CV for {company} (Manual Action Needed)")

                                except Exception as tg_err:
                                    print(f"[Auto-Apply] Failed sending Telegram update: {tg_err}")

                    except Exception as apply_err:
                        print(f"[Auto-Apply] Error processing application for {company}: {apply_err}", file=sys.stderr)
                        err_status = f"Failed ({apply_err})"
                        job["Status"] = err_status
                        job["status"] = err_status
                        job["Application Status"] = err_status
                        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                            try:
                                tg = TelegramRouter(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
                                failed_res = {
                                    "channel": "ERROR",
                                    "success": False,
                                    "status": err_status,
                                    "error": str(apply_err)
                                }
                                tg_msg = tg.format_auto_apply_update(job=job, result=failed_res)
                                tg.send_message(tg_msg)
                            except Exception as tg_err:
                                print(f"[Auto-Apply] Failed sending Telegram error update: {tg_err}")
        elif new_jobs and not AUTO_APPLY_ENABLED:
            print("\n[Auto-Apply] AUTO_APPLY_ENABLED is false. Skipping automated tailoring/application.")

        # --- 3. Optional: Reprocess existing unapplied jobs in Google Sheets ---
        if sheets_active and GOOGLE_CREDENTIALS_JSON and AUTO_APPLY_ENABLED and os.getenv("AUTO_APPLY_REPROCESS_UNAPPLIED", "false").lower() in ("true", "1"):
            print("\n[Auto-Apply] Checking for unapplied 'Apply via URL' rows in Google Sheets to re-process...")
            try:
                unapplied_jobs = sheets_router.get_unapplied_jobs()
                if unapplied_jobs:
                    print(f"[Auto-Apply] Found {len(unapplied_jobs)} unapplied job(s) in sheet. Processing...")
                    if not dispatcher:
                        dispatcher = AutoApplyDispatcher(mode=AUTO_APPLY_MODE)
                    for ujob in unapplied_jobs:
                        u_url = ujob.get("URL", "")
                        u_company = ujob.get("Company", "Company")
                        try:
                            res = dispatcher.process_job(ujob)
                            u_status = res.get("status", "Applied (Web Portal)")
                            sheets_router.update_application_status(
                                job_url=u_url,
                                status=u_status,
                                contact_email=ujob.get("Contact Email", "")
                            )
                        except Exception as e:
                            print(f"[Auto-Apply] Failed reprocessing sheet job {u_company}: {e}")
            except Exception as e:
                print(f"[Auto-Apply] Error checking unapplied jobs in sheet: {e}")

        # --- 4. Route findings to Google Sheets (Bulk append with final status & dates) ---
        if new_jobs and GOOGLE_CREDENTIALS_JSON and sheets_active:
            print("\nExporting new matches to Google Sheets...")
            try:
                sheets_success = sheets_router.append_jobs(new_jobs)
                if sheets_success:
                    print("Google Sheets export completed successfully.")
                else:
                    print("Google Sheets export failed. Check logs for details.")
            except Exception as e:
                print(f"[ERROR] Exception during Google Sheets routing: {e}", file=sys.stderr)

        # --- Update local state cache ---
        if new_jobs:
            local_state_file = "scraped_jobs.json"
            local_existing_urls = []
            if os.path.exists(local_state_file):
                try:
                    with open(local_state_file, "r") as f:
                        local_existing_urls = json.load(f)
                except Exception as e:
                    pass
            new_urls_to_cache = list(set(local_existing_urls + [job["URL"] for job in new_jobs]))
            try:
                with open(local_state_file, "w") as f:
                    json.dump(new_urls_to_cache, f, indent=2)
                print(f"Updated local state cache in '{local_state_file}'.")
            except Exception as e:
                print(f"[Warning] Failed to write local state file '{local_state_file}': {e}", file=sys.stderr)

        # --- 3. Route findings to Telegram (only if auto-apply did not run, to prevent duplicate spam) ---
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            if not AUTO_APPLY_ENABLED and new_jobs:
                print("\nDispatching alerts to Telegram...")
                try:
                    telegram_router = TelegramRouter(
                        bot_token=TELEGRAM_BOT_TOKEN,
                        chat_id=TELEGRAM_CHAT_ID
                    )
                    formatted_msg = telegram_router.format_jobs_message(new_jobs, lookback_hours=JOB_LOOKBACK_HOURS)
                    telegram_success = telegram_router.send_message(formatted_msg)
                    if telegram_success:
                        print("Telegram notification dispatched successfully.")
                    else:
                        print("Telegram notification dispatch failed.")
                except Exception as e:
                    print(f"[ERROR] Exception during Telegram routing: {e}", file=sys.stderr)
            elif new_jobs and AUTO_APPLY_ENABLED:
                print(f"\nAuto-apply processed {len(new_jobs)} job(s). Telegram notified for jobs requiring manual action. Skipping duplicate batch list.")
        else:
            print("\nTelegram Bot Token/Chat ID not set. Skipping Telegram routing.")

        print("\n=== Pipeline finished ===")

    except Exception as pipeline_err:
        print(f"\n[FATAL ERROR] Pipeline execution crashed: {pipeline_err}", file=sys.stderr)
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            try:
                telegram_router = TelegramRouter(
                    bot_token=TELEGRAM_BOT_TOKEN,
                    chat_id=TELEGRAM_CHAT_ID
                )
                err_msg = f"❌ *Job Scraper Pipeline Failed*\n\nAn unexpected error occurred during execution:\n`{pipeline_err}`"
                telegram_router.send_message(err_msg)
            except Exception as tg_err:
                print(f"[ERROR] Failed to send crash notification to Telegram: {tg_err}", file=sys.stderr)
        sys.exit(1)
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        log_file.close()

        # Send execution summary to Telegram
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            print("\nDispatching run summary to Telegram...")
            try:
                duration_seconds = (datetime.now() - start_time).total_seconds()
                telegram_router = TelegramRouter(
                    bot_token=TELEGRAM_BOT_TOKEN,
                    chat_id=TELEGRAM_CHAT_ID
                )
                active_new_jobs = new_jobs if ('new_jobs' in locals() and new_jobs) else []
                total_applied = sum(
                    1 for j in active_new_jobs
                    if "applied" in str(j.get("Application Status", "") or j.get("Status", "")).lower()
                )
                total_drafted = sum(
                    1 for j in active_new_jobs
                    if any(k in str(j.get("Application Status", "") or j.get("Status", "")).lower() for k in ("draft", "review"))
                )
                failed_jobs_list = [
                    (j.get("Company", "Unknown"), str(j.get("Application Status", "") or j.get("Status", "")))
                    for j in active_new_jobs
                    if any(k in str(j.get("Application Status", "") or j.get("Status", "")).lower() for k in ("fail", "error"))
                ]
                total_failed = len(failed_jobs_list)
                total_unapplied = max(0, len(active_new_jobs) - total_applied - total_drafted - total_failed)

                summary_msg = telegram_router.format_run_summary(
                    duration_seconds=duration_seconds,
                    total_configured=len(COMPANY_BOARDS),
                    scanned_count=len(scanned_boards),
                    skipped_count=len(skipped_boards),
                    failed_boards=failed_boards,
                    total_found=len(all_matched_jobs) if 'all_matched_jobs' in locals() else 0,
                    total_new=len(active_new_jobs),
                    total_applied=total_applied,
                    total_drafted=total_drafted,
                    total_unapplied=total_unapplied,
                    total_failed=total_failed,
                    failed_jobs=failed_jobs_list
                )
                telegram_router.send_message(summary_msg)
            except Exception as tg_err:
                print(f"[ERROR] Failed to send run summary to Telegram: {tg_err}")

if __name__ == "__main__":
    main()
