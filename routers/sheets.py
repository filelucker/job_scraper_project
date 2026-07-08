import json
import os
import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Any

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

    def append_jobs(self, jobs: List[Dict[str, Any]]) -> bool:
        """Append list of jobs to the target Google Sheet, creating worksheet / headers if needed."""
        if not jobs:
            print("[Google Sheets Router] No jobs to append.")
            return True

        if not self.credentials_json:
            print("[Google Sheets Router] GOOGLE_CREDENTIALS_JSON not configured. Skipping sheets export.")
            return False

        try:
            client = self._get_client()
            
            # Open the Google Sheet by name
            try:
                spreadsheet = client.open(self.sheet_name)
            except gspread.SpreadsheetNotFound:
                print(f"[Google Sheets Router] Spreadsheet '{self.sheet_name}' not found. Please share the sheet with your service account email.")
                return False

            # Retrieve or create target worksheet
            try:
                worksheet = spreadsheet.worksheet(self.worksheet_name)
            except gspread.WorksheetNotFound:
                print(f"[Google Sheets Router] Worksheet '{self.worksheet_name}' not found. Creating it.")
                worksheet = spreadsheet.add_worksheet(title=self.worksheet_name, rows="1000", cols="5")
                
            # If worksheet is brand new/empty, initialize headers
            existing_records = worksheet.get_all_values()
            headers = ["Company", "Title", "Location", "URL", "Date Found"]
            
            if not existing_records:
                worksheet.append_row(headers)
                
            # Prepare rows to append
            rows_to_append = []
            for job in jobs:
                rows_to_append.append([
                    job.get("Company", ""),
                    job.get("Title", ""),
                    job.get("Location", ""),
                    job.get("URL", ""),
                    job.get("Date Found", "")
                ])
                
            # Perform bulk append
            if rows_to_append:
                worksheet.append_rows(rows_to_append, value_input_option="USER_ENTERED")
                print(f"[Google Sheets Router] Successfully appended {len(rows_to_append)} rows to '{self.sheet_name}' -> '{self.worksheet_name}'")
            return True

        except Exception as e:
            print(f"[Google Sheets Router] Error appending rows to Google Sheets: {e}")
            return False
