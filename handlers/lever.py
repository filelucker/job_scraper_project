import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from handlers.base import BaseHandler, Job

class LeverHandler(BaseHandler):
    """Handler for companies using the Lever API."""

    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        url = f"https://api.lever.co/v0/postings/{self.token}?mode=json"
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            # Lever returns a JSON array of postings directly
            data = response.json()
            if isinstance(data, list):
                return data
            return []
        except requests.RequestException as e:
            print(f"[Lever - {self.company_name}] Network/API error: {e}")
            return []
        except ValueError as e:
            print(f"[Lever - {self.company_name}] JSON decoding error: {e}")
            return []

    def parse_job(self, raw_job: Dict[str, Any]) -> Optional[Job]:
        title = raw_job.get("title")
        hosted_url = raw_job.get("hostedUrl")
        
        # Lever location categorization
        categories = raw_job.get("categories") or {}
        location = categories.get("location", "Remote / Not Specified")
        
        # Lever date parsing (createdAt is an epoch millisecond timestamp integer)
        created_at_val = raw_job.get("createdAt")
        if created_at_val is None:
            posted_time = datetime.now(timezone.utc)
        else:
            try:
                # If millisecond timestamp
                if isinstance(created_at_val, (int, float)):
                    posted_time = datetime.fromtimestamp(created_at_val / 1000.0, tz=timezone.utc)
                else:
                    # Fallback for ISO strings if any API variation uses string dates
                    posted_time_str = str(created_at_val)
                    if posted_time_str.endswith('Z'):
                        posted_time_str = posted_time_str[:-1] + '+00:00'
                    posted_time = datetime.fromisoformat(posted_time_str)
            except Exception:
                posted_time = datetime.now(timezone.utc)

        if not title or not hosted_url:
            return None

        return Job(
            company=self.company_name,
            title=title.strip(),
            location=location.strip(),
            url=hosted_url.strip(),
            posted_time=posted_time
        )
