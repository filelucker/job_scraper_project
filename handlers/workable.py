import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from handlers.base import BaseHandler, Job

class WorkableHandler(BaseHandler):
    """Handler for companies using the Workable Job Board."""

    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        # Fetch jobs using Workable's public widget endpoint
        url = f"https://apply.workable.com/api/v1/widget/accounts/{self.token}"
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data.get("jobs", [])
        except requests.RequestException as e:
            print(f"[Workable - {self.company_name}] Network/API error: {e}")
            return []
        except ValueError as e:
            print(f"[Workable - {self.company_name}] JSON decoding error: {e}")
            return []

    def parse_job(self, raw_job: Dict[str, Any]) -> Optional[Job]:
        title = raw_job.get("title")
        url = raw_job.get("shortlink")
        
        # Get location
        loc_dict = raw_job.get("location") or {}
        city = loc_dict.get("city", "")
        country = loc_dict.get("countryName", "")
        
        if city and country:
            location = f"{city}, {country}"
        elif country:
            location = country
        else:
            location = "Remote / Not Specified"
            
        # Parse timestamp (e.g. "2026-07-11T12:00:00.000Z")
        published_str = raw_job.get("published")
        if not published_str:
            posted_time = datetime.now(timezone.utc)
        else:
            if published_str.endswith('Z'):
                published_str = published_str[:-1] + '+00:00'
            try:
                posted_time = datetime.fromisoformat(published_str)
            except ValueError:
                posted_time = datetime.now(timezone.utc)

        if not title or not url:
            return None

        return Job(
            company=self.company_name,
            title=title.strip(),
            location=location.strip(),
            url=url.strip(),
            posted_time=posted_time
        )
