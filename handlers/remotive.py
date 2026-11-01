import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from handlers.base import BaseHandler, Job

class RemotiveHandler(BaseHandler):
    """
    Handler for Remotive Remote Jobs API.
    Provides verified remote software development job listings worldwide.
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
        self.api_url = "https://remotive.com/api/remote-jobs"

    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        """Fetch remote engineering jobs from Remotive public REST API."""
        try:
            params = {"category": "software-dev"}
            resp = requests.get(
                self.api_url,
                params=params,
                headers={"User-Agent": "JobScraperBot/1.0"},
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("jobs", [])
        except Exception as e:
            print(f"[Remotive] Error fetching jobs: {e}")
            return []

    def parse_job(self, raw_job: Dict[str, Any]) -> Optional[Job]:
        title = raw_job.get("title")
        url = raw_job.get("url")
        if not title or not url:
            return None

        company = raw_job.get("company_name") or "Unknown"
        req_loc = raw_job.get("candidate_required_location") or "Worldwide"
        location = f"Remote ({req_loc})" if "remote" not in req_loc.lower() else req_loc

        description = raw_job.get("description") or ""
        tags = raw_job.get("tags") or []

        # Parse publication date
        pub_date_str = raw_job.get("publication_date")
        posted_time = datetime.now(timezone.utc)
        if pub_date_str:
            try:
                # e.g. 2026-10-29T18:22:41
                posted_time = datetime.fromisoformat(pub_date_str)
                if posted_time.tzinfo is None:
                    posted_time = posted_time.replace(tzinfo=timezone.utc)
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
