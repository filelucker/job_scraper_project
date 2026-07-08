import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from handlers.base import BaseHandler, Job

class GreenhouseHandler(BaseHandler):
    """Handler for companies using the Greenhouse Job Board API."""
    
    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{self.token}/jobs"
        try:
            response = requests.get(url, timeout=15)
            # Raise exception for bad HTTP response status
            response.raise_for_status()
            data = response.json()
            return data.get("jobs", [])
        except requests.RequestException as e:
            print(f"[Greenhouse - {self.company_name}] Network/API error: {e}")
            return []
        except ValueError as e:
            print(f"[Greenhouse - {self.company_name}] JSON decoding error: {e}")
            return []

    def parse_job(self, raw_job: Dict[str, Any]) -> Optional[Job]:
        title = raw_job.get("title")
        absolute_url = raw_job.get("absolute_url")
        
        # Get location (Greenhouse structure: {"name": "..."})
        location_dict = raw_job.get("location") or {}
        location = location_dict.get("name", "Remote / Not Specified")
        
        # Parse timestamp (Greenhouse standard is 'updated_at' string)
        updated_at_str = raw_job.get("updated_at")
        if not updated_at_str:
            # Fallback to current time if no date field exists
            posted_time = datetime.now(timezone.utc)
        else:
            # Handle standard 'Z' Zulu timezone suffix in datetime string
            if updated_at_str.endswith('Z'):
                updated_at_str = updated_at_str[:-1] + '+00:00'
            try:
                posted_time = datetime.fromisoformat(updated_at_str)
            except ValueError:
                posted_time = datetime.now(timezone.utc)

        if not title or not absolute_url:
            return None

        return Job(
            company=self.company_name,
            title=title.strip(),
            location=location.strip(),
            url=absolute_url.strip(),
            posted_time=posted_time
        )
