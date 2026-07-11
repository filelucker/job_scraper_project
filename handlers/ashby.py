import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from handlers.base import BaseHandler, Job

class AshbyHandler(BaseHandler):
    """Handler for companies using the Ashby Job Board API."""
    
    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        url = f"https://api.ashbyhq.com/posting-api/job-board/{self.token}"
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data.get("jobs", [])
        except requests.RequestException as e:
            print(f"[Ashby - {self.company_name}] Network/API error: {e}")
            return []
        except ValueError as e:
            print(f"[Ashby - {self.company_name}] JSON decoding error: {e}")
            return []

    def parse_job(self, raw_job: Dict[str, Any]) -> Optional[Job]:
        title = raw_job.get("title")
        job_url = raw_job.get("jobUrl")
        location = raw_job.get("location", "Remote / Not Specified")
        
        # Ashby date parsing (publishedAt is an ISO-8601 string)
        published_at_str = raw_job.get("publishedAt")
        if not published_at_str:
            posted_time = datetime.now(timezone.utc)
        else:
            try:
                # E.g. '2024-03-21T14:51:05.794+00:00'
                if published_at_str.endswith('Z'):
                    published_at_str = published_at_str[:-1] + '+00:00'
                posted_time = datetime.fromisoformat(published_at_str)
            except ValueError:
                posted_time = datetime.now(timezone.utc)

        if not title or not job_url:
            return None

        return Job(
            company=self.company_name,
            title=title.strip(),
            location=location.strip() if isinstance(location, str) else "Remote / Not Specified",
            url=job_url.strip(),
            posted_time=posted_time
        )
