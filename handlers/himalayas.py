import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from handlers.base import BaseHandler, Job

class HimalayasHandler(BaseHandler):
    """
    Handler for Himalayas Remote Job Board API.
    Provides verified remote tech and engineering job listings.
    Public API: No API key required.
    """
    def __init__(
        self,
        company_name: str,
        token: str,
        keywords: List[str],
        lookback_hours: int = 6,
        only_remote_or_hybrid: bool = False,
        compound_rules: Optional[List[Dict[str, Any]]] = None
    ):
        super().__init__(
            company_name=company_name,
            token=token,
            keywords=keywords,
            lookback_hours=lookback_hours,
            only_remote_or_hybrid=only_remote_or_hybrid,
            compound_rules=compound_rules
        )
        self.api_url = "https://himalayas.app/jobs/api"

    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        """Fetch remote jobs from Himalayas public REST API."""
        try:
            resp = requests.get(
                self.api_url,
                params={"limit": 100},
                headers={"User-Agent": "JobScraperBot/1.0"},
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("jobs", [])
        except Exception as e:
            print(f"[Himalayas] Error fetching jobs: {e}")
            return []

    def parse_job(self, raw_job: Dict[str, Any]) -> Optional[Job]:
        title = raw_job.get("title")
        url = raw_job.get("applicationLink") or raw_job.get("guid")
        if not title or not url:
            return None

        company = raw_job.get("companyName") or "Unknown"
        location = raw_job.get("location") or "Remote"
        if "remote" not in location.lower():
            location = f"{location} (Remote)"

        description = raw_job.get("description") or raw_job.get("excerpt") or ""
        tags = raw_job.get("categories") or []

        # Parse publication date (unix timestamp)
        pub_ts = raw_job.get("pubDate")
        posted_time = datetime.now(timezone.utc)
        if isinstance(pub_ts, (int, float)):
            try:
                posted_time = datetime.fromtimestamp(pub_ts, tz=timezone.utc)
            except Exception:
                pass
        elif isinstance(pub_ts, str):
            try:
                posted_time = datetime.fromisoformat(pub_ts)
            except Exception:
                pass

        desc_lower = description.lower()
        has_relocation = "relocation" in desc_lower or any("relocat" in str(t).lower() for t in tags)
        has_visa = "visa" in desc_lower or "sponsorship" in desc_lower or any("visa" in str(t).lower() for t in tags)

        return Job(
            company=company,
            title=title,
            location=location,
            url=url,
            posted_time=posted_time,
            description=description,
            tags=tags,
            has_relocation=has_relocation,
            has_visa_sponsorship=has_visa
        )
