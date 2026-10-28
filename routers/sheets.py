import json
import os
from datetime import datetime, timezone, timedelta
import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Any, Optional

STANDARD_HEADERS = [
    "Company",
    "Title",
    "Location",
    "URL",
    "Actual Post Date",
    "Date Found",
    "this job accepts candidate worldwide or not",
    "Contact Email",
    "Application Status",
    "Applied At"
]

class GoogleSheetsRouter:
    """Router to append matched jobs directly to a Google Sheet using gspread."""
    
    def __init__(self, credentials_json: str, sheet_name: str, worksheet_name: str = "Jobs"):
        self.credentials_json = credentials_json
        self.sheet_name = sheet_name
        self.worksheet_name = worksheet_name

    def _get_client(self) -> gspread.Client:
        """Authenticate using service account credentials from a JSON string or file path."""
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Determine if credentials_json is raw JSON content or a file path
        if not self.credentials_json:
            raise ValueError("Credentials JSON is empty or not provided.")

        try:
            # Attempt to parse as raw JSON string
            creds_data = json.loads(self.credentials_json)
            creds = Credentials.from_service_account_info(creds_data, scopes=scopes)
        except (json.JSONDecodeError, TypeError):
            # Fallback: treat as a file path
            if not os.path.exists(self.credentials_json):
                raise FileNotFoundError(
                    f"Credentials JSON is not a valid JSON string and file path does not exist: {self.credentials_json}"
                )
            creds = Credentials.from_service_account_file(self.credentials_json, scopes=scopes)
            
        return gspread.authorize(creds)

    def _get_worksheet(self) -> Optional[gspread.Worksheet]:
        """Open or create the target worksheet."""
        client = self._get_client()
        spreadsheet = client.open(self.sheet_name)
        try:
            return spreadsheet.worksheet(self.worksheet_name)
        except gspread.WorksheetNotFound:
            print(f"[Google Sheets Router] Worksheet '{self.worksheet_name}' not found. Creating it.")
            return spreadsheet.add_worksheet(title=self.worksheet_name, rows="1000", cols=str(len(STANDARD_HEADERS)))

    def get_existing_urls(self) -> List[str]:
        """Fetch all existing job URLs already stored in the worksheet to prevent duplicates."""
        if not self.credentials_json:
            return []
            
        try:
            worksheet = self._get_worksheet()
            if not worksheet:
                return []
                
            # Column 4 is URL based on headers: ["Company", "Title", "Location", "URL", ...]
            urls = worksheet.col_values(4)
            if urls and urls[0] == "URL":
                urls = urls[1:]
            return [url.strip() for url in urls if url]
        except Exception as e:
            print(f"[Google Sheets Router] Error fetching existing URLs: {e}")
            return []

    def get_unapplied_jobs(self) -> List[Dict[str, Any]]:
        """Fetch all rows where Application Status is 'Apply via URL' or 'Pending' and Applied At is empty."""
        if not self.credentials_json:
            return []
        try:
            worksheet = self._get_worksheet()
            if not worksheet:
                return []
            records = worksheet.get_all_records()
            unapplied = []
            for row in records:
                status = str(row.get("Application Status", "")).strip()
                applied_at = str(row.get("Applied At", "")).strip()
                if ("Apply via" in status or "Pending" in status) and not applied_at:
                    unapplied.append({
                        "Company": row.get("Company", ""),
                        "Title": row.get("Title", ""),
                        "Location": row.get("Location", ""),
                        "URL": row.get("URL", ""),
                        "Contact Email": row.get("Contact Email", ""),
                        "Application Status": status,
                        "Applied At": applied_at
                    })
            return unapplied
        except Exception as e:
            print(f"[Google Sheets Router] Error fetching unapplied jobs: {e}")
            return []

    def _convert_to_am_pm(self, time_str: str) -> str:
        """Convert a 24-hour time string like '2026-07-12 21:33:01 BST' to 12-hour AM/PM format '2026-07-12 09:33:01 PM BST'."""
        if not time_str:
            return ""
        try:
            dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S BST")
            return dt.strftime("%Y-%m-%d %I:%M:%S %p BST")
        except Exception:
            return time_str

    def _current_bst_timestamp(self) -> str:
        """Return current timestamp in BST 12-hour format."""
        bst = timezone(timedelta(hours=6))
        now = datetime.now(bst)
        return now.strftime("%Y-%m-%d %I:%M:%S %p BST")

    def append_jobs(self, jobs: List[Dict[str, Any]]) -> bool:
        """Append list of jobs to the target Google Sheet, creating worksheet / headers if needed."""
        if not jobs:
            print("[Google Sheets Router] No jobs to append.")
            return True

        if not self.credentials_json:
            print("[Google Sheets Router] GOOGLE_CREDENTIALS_JSON not configured. Skipping sheets export.")
            return False

        try:
            worksheet = self._get_worksheet()
            if not worksheet:
                return False

            # Inspect existing records to verify or upgrade headers
            existing_records = worksheet.get_all_values()
            
            if not existing_records:
                worksheet.append_row(STANDARD_HEADERS)
            elif len(existing_records[0]) < len(STANDARD_HEADERS):
                # Upgrade existing header row with the new tracking columns
                worksheet.update(range_name='A1:J1', values=[STANDARD_HEADERS])

            # Prepare rows to append
            rows_to_append = []
            for job in jobs:
                loc_lower = job.get("Location", "").lower()
                is_worldwide = "worldwide" in loc_lower or "global" in loc_lower or "anywhere" in loc_lower
                worldwide_val = "Yes" if is_worldwide else "No"
                
                contact_email = job.get("Contact Email") or job.get("email", "")
                status = job.get("Application Status") or job.get("Status") or job.get("status") or job.get("initial_status", "Pending")
                applied_at = job.get("Applied At") or job.get("applied_at") or ""
                if not applied_at and ("Applied" in status or "Drafted" in status):
                    applied_at = self._current_bst_timestamp()

                rows_to_append.append([
                    job.get("Company", ""),
                    job.get("Title", ""),
                    job.get("Location", ""),
                    job.get("URL", ""),
                    self._convert_to_am_pm(job.get("Actual Post Date", "")),
                    self._convert_to_am_pm(job.get("Date Found", "")),
                    worldwide_val,
                    contact_email,
                    status,
                    applied_at
                ])
                
            # Perform bulk append
            if rows_to_append:
                worksheet.append_rows(rows_to_append, value_input_option="USER_ENTERED")
                print(f"[Google Sheets Router] Successfully appended {len(rows_to_append)} rows to '{self.sheet_name}' -> '{self.worksheet_name}'")
            return True

        except Exception as e:
            print(f"[Google Sheets Router] Error appending rows to Google Sheets: {e}")
            return False

    def update_application_status(
        self,
        job_url: str,
        status: str,
        contact_email: Optional[str] = None,
        applied_at: Optional[str] = None
    ) -> bool:
        """
        Update the Contact Email (col 8), Application Status (col 9), and Applied At (col 10)
        for an existing row matching job_url.
        """
        if not self.credentials_json or not job_url:
            return False

        try:
            worksheet = self._get_worksheet()
            if not worksheet:
                return False

            # Find cell matching URL in Column 4 (D) first, with fallback to full sheet
            cell = worksheet.find(job_url, in_column=4)
            if not cell:
                cell = worksheet.find(job_url)
            if not cell:
                print(f"[Google Sheets Router] URL not found for status update: {job_url}")
                return False

            row = cell.row
            timestamp = applied_at or self._current_bst_timestamp()

            # Prepare batch update for columns 8 (H), 9 (I), 10 (J)
            updates = []
            if contact_email is not None:
                updates.append({'range': f'H{row}', 'values': [[contact_email]]})
            updates.append({'range': f'I{row}', 'values': [[status]]})
            updates.append({'range': f'J{row}', 'values': [[timestamp]]})

            worksheet.batch_update(updates)
            print(f"[Google Sheets Router] Updated row {row} status to '{status}' at {timestamp}")
            return True

        except Exception as e:
            print(f"[Google Sheets Router] Error updating application status: {e}")
            return False
