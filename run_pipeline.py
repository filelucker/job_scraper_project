import os
import sys
import json
import concurrent.futures
from datetime import datetime, timezone
from config import (
    KEYWORDS,
    JOB_LOOKBACK_HOURS,
    COMPANY_BOARDS,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    GOOGLE_CREDENTIALS_JSON,
    GOOGLE_SHEET_NAME,
    GOOGLE_WORKSHEET_NAME
)
from handlers import GreenhouseHandler, LeverHandler, FallbackHandler, AshbyHandler, WorkdayHandler, WorkableHandler, SmartRecruitersHandler
from routers import TelegramRouter, GoogleSheetsRouter

def fetch_board(company_name: str, board_config: dict):
    """Worker function to execute a single company's job board scan."""
    ats_type = board_config.get("ats", "").lower()
    token = board_config.get("token", "")

    # Alert users if fallback token is an inactive stub
    if ats_type == "fallback":
        is_rss = token.startswith("http://") or token.startswith("https://") or token.endswith(".xml")
        if not is_rss:
            print(f"[Fallback - {company_name}] Warning: Token '{token}' is not an active RSS URL/file. Skipping stub.", file=sys.stderr)
            return company_name, [], None

    # Select the appropriate ATS handler
    if ats_type == "greenhouse":
        handler = GreenhouseHandler(company_name, token, KEYWORDS, JOB_LOOKBACK_HOURS)
    elif ats_type == "lever":
        handler = LeverHandler(company_name, token, KEYWORDS, JOB_LOOKBACK_HOURS)
    elif ats_type == "ashby":
        handler = AshbyHandler(company_name, token, KEYWORDS, JOB_LOOKBACK_HOURS)
    elif ats_type == "workday":
        handler = WorkdayHandler(company_name, token, KEYWORDS, JOB_LOOKBACK_HOURS)
    elif ats_type == "workable":
        handler = WorkableHandler(company_name, token, KEYWORDS, JOB_LOOKBACK_HOURS)
    elif ats_type == "smartrecruiters":
        handler = SmartRecruitersHandler(company_name, token, KEYWORDS, JOB_LOOKBACK_HOURS)
    else:
        handler = FallbackHandler(company_name, token, KEYWORDS, JOB_LOOKBACK_HOURS)

    try:
        matched_jobs = handler.execute()
        return company_name, matched_jobs, None
    except Exception as e:
        return company_name, [], e

def main():
    print(f"=== Starting Job Scraper Pipeline at {datetime.now(timezone.utc).isoformat()} ===")
    print(f"Target Keywords: {KEYWORDS}")
    print(f"Lookback Window: {JOB_LOOKBACK_HOURS} hours")
    print(f"Scanning {len(COMPANY_BOARDS)} company job boards...\n")

    all_matched_jobs = []

    # Run scans concurrently in a thread pool to avoid sequential execution bottlenecks
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
                company_name, matched_jobs, err = future.result()
                if err:
                    print(f"[ERROR] Fail-safe caught exception while scanning board for '{company_name}': {err}", file=sys.stderr)
                elif matched_jobs:
                    print(f"[{company_name}] Found {len(matched_jobs)} matching job(s) posted in the last 24 hours!")
                    for job in matched_jobs:
                        print(f"  - {job.title} ({job.location}) -> {job.url}")
                    all_matched_jobs.extend(matched_jobs)
            except Exception as e:
                print(f"[ERROR] Thread execution failed for '{company_name}': {e}", file=sys.stderr)

    print(f"\nScan completed. Found {len(all_matched_jobs)} matching job(s) in total.")

    if not all_matched_jobs:
        print("No matches found. Pipeline complete.")
        return

    # Convert matching Job objects to dictionary format
    job_dicts = [job.to_dict() for job in all_matched_jobs]

    # --- Deduplication logic ---
    existing_urls = []
    sheets_active = False

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

    if not new_jobs:
        print("No new jobs to route. Pipeline complete.")
        return

    # --- 1. Route findings to Google Sheets ---
    if GOOGLE_CREDENTIALS_JSON and sheets_active:
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
    new_urls_to_cache = list(set(local_existing_urls + [job["URL"] for job in new_jobs]))
    try:
        with open(local_state_file, "w") as f:
            json.dump(new_urls_to_cache, f, indent=2)
        print(f"Updated local state cache in '{local_state_file}'.")
    except Exception as e:
        print(f"[Warning] Failed to write local state file '{local_state_file}': {e}", file=sys.stderr)

    # --- 2. Route findings to Telegram ---
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        print("\nDispatching alerts to Telegram...")
        try:
            telegram_router = TelegramRouter(
                bot_token=TELEGRAM_BOT_TOKEN,
                chat_id=TELEGRAM_CHAT_ID
            )
            formatted_msg = telegram_router.format_jobs_message(new_jobs)
            telegram_success = telegram_router.send_message(formatted_msg)
            if telegram_success:
                print("Telegram notification dispatched successfully.")
            else:
                print("Telegram notification dispatch failed.")
        except Exception as e:
            print(f"[ERROR] Exception during Telegram routing: {e}", file=sys.stderr)
    else:
        print("\nTelegram Bot Token/Chat ID not set. Skipping Telegram routing.")

    print("\n=== Pipeline finished ===")

if __name__ == "__main__":
    main()
