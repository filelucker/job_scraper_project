import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from handlers.base import BaseHandler, Job

class JoobleHandler(BaseHandler):
    """
    Handler for Jooble Job Search API.
    Utilizes free Jooble API key.
    """
    def __init__(self, company_name: str, token: str, keywords: List[str], lookback_hours: int = 24, only_remote_or_hybrid: bool = False, api_key: str = ""):
        super().__init__(company_name, token, keywords, lookback_hours, only_remote_or_hybrid)
        self.api_key = api_key

    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        if not self.api_key:
            print(f"[Jooble] Info: JOOBLE_API_KEY is not set. Skipping Jooble.")
            return []

        url = f"https://jooble.org/api/{self.api_key}"
        query = " OR ".join([f'"{kw}"' for kw in self.keywords[:8]])
        payload = {
            "keywords": query,
            "location": "Remote" if self.only_remote_or_hybrid else ""
        }
        
        try:
            response = requests.post(url, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data.get("jobs", [])
        except Exception as e:
            print(f"[Jooble] Error querying API: {e}")
            return []

    def parse_job(self, raw_job: Dict[str, Any]) -> Optional[Job]:
        title = raw_job.get("title")
        company = raw_job.get("company", "Unknown Company")
        url = raw_job.get("link")
        location = raw_job.get("location", "Remote")
        updated_str = raw_job.get("updated")
        
        if title:
            title = title.replace("<b>", "").replace("</b>", "").replace("&nbsp;", " ").strip()

        posted_time = datetime.now(timezone.utc)
        if updated_str:
            try:
                # E.g. "2026-07-14T08:00:00.0000000+03:00"
                posted_time = datetime.fromisoformat(updated_str.strip())
            except Exception:
                pass

        if not title or not url:
            return None

        return Job(
            company=company,
            title=title,
            location=location,
            url=url,
            posted_time=posted_time
        )
