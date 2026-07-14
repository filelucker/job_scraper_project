import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from handlers.base import BaseHandler, Job

class AdzunaHandler(BaseHandler):
    """
    Handler for Adzuna Job Search API.
    Utilizes free developer app_id and app_key.
    """
    def __init__(self, company_name: str, token: str, keywords: List[str], lookback_hours: int = 24, only_remote_or_hybrid: bool = False, app_id: str = "", app_key: str = ""):
        super().__init__(company_name, token, keywords, lookback_hours, only_remote_or_hybrid)
        self.app_id = app_id
        self.app_key = app_key

    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        if not self.app_id or not self.app_key:
            print(f"[Adzuna] Info: ADZUNA_APP_ID or ADZUNA_APP_KEY is not set. Skipping Adzuna.")
            return []

        # Use target keywords. Match at least one of the keywords
        query = " OR ".join([f'"{kw}"' for kw in self.keywords[:8]])
        url = f"https://api.adzuna.com/v1/api/jobs/us/search/1"
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "results_per_page": 50,
            "what": query,
            "max_days_old": max(1, self.lookback_hours // 24)
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except Exception as e:
            print(f"[Adzuna] Error querying API: {e}")
            return []

    def parse_job(self, raw_job: Dict[str, Any]) -> Optional[Job]:
        title = raw_job.get("title")
        company = raw_job.get("company", {}).get("display_name", "Unknown Company")
        url = raw_job.get("redirect_url")
        location = raw_job.get("location", {}).get("display_name", "Remote / USA")
        created_str = raw_job.get("created")
        
        if title:
            title = title.replace("<strong>", "").replace("</strong>", "").replace("&nbsp;", " ").strip()
            
        posted_time = datetime.now(timezone.utc)
        if created_str:
            try:
                clean_date = created_str.strip()
                if clean_date.endswith("Z"):
                    clean_date = clean_date[:-1] + "+00:00"
                posted_time = datetime.fromisoformat(clean_date)
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
