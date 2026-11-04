# routers

## Overview
The `routers` component package handles output routing, persistent tracking, and notification dispatches for the scraping and application pipeline. It routes data to three external sinks: Google Sheets for live application status tracking and URL deduplication, Telegram for instant candidate push notifications (including preview screenshots and tailored CV attachments), and SMTP for automated email application delivery.

## Interface
- `class GoogleSheetsRouter`: Live spreadsheet tracking and deduplication engine (`sheets.py`).
  - `__init__(credentials_json: str, sheet_name: str = "Job Scraper Results", worksheet_name: str = "Jobs")`
  - `get_existing_urls() -> List[str]`: Fetches all tracked job URLs (Column 4) for pre-scan deduplication.
  - `get_applied_urls() -> Set[str]`: Returns URLs marked with finalized applied statuses.
  - `get_unapplied_jobs(max_jobs: int = 5) -> List[Dict[str, Any]]`: Retrieves pending rows for reprocessing.
  - `append_jobs(jobs: List[Dict[str, Any]]) -> bool`: Bulk appends standardized job records with 10 columns (`Company`, `Title`, `Location`, `URL`, `Actual Post Date`, `Date Found`, `Worldwide (Yes/No)`, `Contact Email`, `Application Status`, `Applied At`).
  - `update_application_status(job_url: str, status: str, contact_email: Optional[str] = None, applied_at: Optional[str] = None) -> bool`: Updates Columns 8 (Email), 9 (Status), and 10 (Applied At) matching a job URL.
- `class TelegramRouter`: Push notification and alert dispatch service (`telegram.py`).
  - `__init__(bot_token: str, chat_id: str)`
  - `escape_markdown(text: str) -> str`: Escapes Markdown V1 reserved characters (`_`, `*`, `[`, `]`, `` ` ``).
  - `format_jobs_message(jobs: List[Dict[str, Any]], lookback_hours: int = 24) -> str`: Formats batch discovered job lists.
  - `format_auto_apply_update(job: Dict[str, Any], result: Dict[str, Any]) -> str`: Formats individual application status cards.
  - `format_run_summary(duration_seconds: float, total_configured: int, scanned_count: int, skipped_count: int, failed_boards: List[Tuple[str, Any]], total_found: int, total_new: int, total_applied: int, total_drafted: int, total_unapplied: int, total_failed: int = 0, failed_jobs: Optional[List[Tuple[str, str]]] = None) -> str`: Formats execution metrics and failed board diagnostics.
  - `send_message(message: str) -> bool`: Sends Markdown message with automatic line-preserving splitting at 3,800 characters.
  - `send_photo(photo_path: str, caption: Optional[str] = None) -> bool`: Uploads application preview screenshots.
  - `send_document(document_path: str, caption: Optional[str] = None) -> bool`: Uploads tailored CV PDF documents.
- `class EmailRouter`: SMTP candidate application dispatcher (`email_router.py`).
  - `__init__(smtp_host: Optional[str] = None, smtp_port: Optional[int] = None, smtp_user: Optional[str] = None, smtp_password: Optional[str] = None, sender_name: Optional[str] = None, dry_run: bool = False)`
  - `send_application(recipient_email: str, subject: str, body_text: str, body_html: str, pdf_path: str, attachment_filename: Optional[str] = None) -> Dict[str, Any]`: Sends multipart MIME email (plain text + HTML + attached PDF resume).

## Invariants
- `GoogleSheetsRouter` preserves a strict 10-column schema (`STANDARD_HEADERS`).
- Date and time entries written to Google Sheets must be converted to 12-hour AM/PM format with Bangladesh Standard Time (`BST`) timezone annotations.
- Telegram message payloads exceeding 3,800 characters must be partitioned across newline boundaries to prevent API message truncation errors.
- If `dry_run` is enabled, `EmailRouter` simulates email dispatch and logs intent without establishing external SMTP socket connections.

## Side Effects
- Outbound HTTPS network calls to Google Sheets API (`gspread` / Google Drive API) for worksheet reads, appends, and cell updates.
- Outbound HTTPS network calls to Telegram Bot API (`https://api.telegram.org`) for messages, photos, and document uploads.
- Outbound SMTP connections (ports 587 STARTTLS or 465 SSL) for live email delivery.

## Verification
- Run: `python -m unittest tests/test_pipeline.py`

