import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from handlers.base import BaseHandler, Job

class SmartRecruitersHandler(BaseHandler):
    """Handler for companies using the SmartRecruiters Job Board API."""

    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        url = f"https://api.smartrecruiters.com/v1/companies/{self.token}/postings"
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data.get("content", [])
        except requests.RequestException as e:
            print(f"[SmartRecruiters - {self.company_name}] Network/API error: {e}")
            return []
        except ValueError as e:
            print(f"[SmartRecruiters - {self.company_name}] JSON decoding error: {e}")
            return []

    def parse_job(self, raw_job: Dict[str, Any]) -> Optional[Job]:
        title = raw_job.get("name")
        job_id = raw_job.get("id")
        
        # SmartRecruiters URL format: https://jobs.smartrecruiters.com/{company_identifier}/{id}
        url = f"https://jobs.smartrecruiters.com/{self.token}/{job_id}" if job_id else None
        
        # Get location
        loc_dict = raw_job.get("location") or {}
        location = loc_dict.get("fullLocation")
        if not location:
            city = loc_dict.get("city", "")
            country = loc_dict.get("country", "")
            if city and country:
                location = f"{city}, {country}"
            elif country:
                location = country
            else:
                location = "Remote / Not Specified"
                
        # Parse timestamp (e.g. "2017-01-25T00:29:21.000Z")
        released_str = raw_job.get("releasedDate")
        if not released_str:
            posted_time = datetime.now(timezone.utc)
        else:
            if released_str.endswith('Z'):
                released_str = released_str[:-1] + '+00:00'
            try:
                posted_time = datetime.fromisoformat(released_str)
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
