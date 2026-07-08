import sys
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
from handlers import GreenhouseHandler, LeverHandler, FallbackHandler
from routers import TelegramRouter, GoogleSheetsRouter

def main():
    print(f"=== Starting Job Scraper Pipeline at {datetime.now(timezone.utc).isoformat()} ===")
    print(f"Target Keywords: {KEYWORDS}")
    print(f"Lookback Window: {JOB_LOOKBACK_HOURS} hours")
    print(f"Scanning {len(COMPANY_BOARDS)} company job boards...\n")

    all_matched_jobs = []

    for company_name, board_config in COMPANY_BOARDS.items():
        ats_type = board_config.get("ats", "").lower()
        token = board_config.get("token", "")

        # Select the appropriate ATS handler
        if ats_type == "greenhouse":
            handler = GreenhouseHandler(company_name, token, KEYWORDS, JOB_LOOKBACK_HOURS)
        elif ats_type == "lever":
            handler = LeverHandler(company_name, token, KEYWORDS, JOB_LOOKBACK_HOURS)
        else:
            handler = FallbackHandler(company_name, token, KEYWORDS, JOB_LOOKBACK_HOURS)

        # Execute check with robust exception handling to isolate failures
        try:
            matched_jobs = handler.execute()
            if matched_jobs:
                print(f"[{company_name}] Found {len(matched_jobs)} matching job(s) posted in the last 24 hours!")
                for job in matched_jobs:
                    print(f"  - {job.title} ({job.location}) -> {job.url}")
                all_matched_jobs.extend(matched_jobs)
            else:
                # Optional: verbose logging for companies with no matches
                # print(f"[{company_name}] No matching jobs.")
                pass
        except Exception as e:
            # Prevent single board API failure from crashing the execution pipeline
            print(f"[ERROR] Fail-safe caught exception while scanning board for '{company_name}': {e}", file=sys.stderr)

    print(f"\nScan completed. Found {len(all_matched_jobs)} matching job(s) in total.")

    if not all_matched_jobs:
        print("No new jobs to route. Pipeline complete.")
        return

    # Convert matching Job objects to dictionary format
    job_dicts = [job.to_dict() for job in all_matched_jobs]

    # --- 1. Route findings to Google Sheets ---
    if GOOGLE_CREDENTIALS_JSON:
        print("\nExporting matches to Google Sheets...")
        try:
            sheets_router = GoogleSheetsRouter(
                credentials_json=GOOGLE_CREDENTIALS_JSON,
                sheet_name=GOOGLE_SHEET_NAME,
                worksheet_name=GOOGLE_WORKSHEET_NAME
            )
            sheets_success = sheets_router.append_jobs(job_dicts)
            if sheets_success:
                print("Google Sheets export completed successfully.")
            else:
                print("Google Sheets export failed. Check logs for details.")
        except Exception as e:
            print(f"[ERROR] Exception during Google Sheets routing: {e}", file=sys.stderr)
    else:
        print("\nGoogle Sheets credentials not set. Skipping sheets routing.")

    # --- 2. Route findings to Telegram ---
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        print("\nDispatching alerts to Telegram...")
        try:
            telegram_router = TelegramRouter(
                bot_token=TELEGRAM_BOT_TOKEN,
                chat_id=TELEGRAM_CHAT_ID
            )
            formatted_msg = telegram_router.format_jobs_message(job_dicts)
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
