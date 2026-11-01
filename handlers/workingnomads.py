import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from handlers.base import BaseHandler, Job

class WorkingNomadsHandler(BaseHandler):
    """
    Handler for Working Nomads Remote Jobs API.
    Provides curated digital nomad and remote engineering job listings.
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
        self.api_url = "https://www.workingnomads.com/api/exposed_jobs/"

    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        """Fetch remote engineering jobs from Working Nomads public REST API."""
        try:
            resp = requests.get(
                self.api_url,
                headers={"User-Agent": "JobScraperBot/1.0"},
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            # Filter for development category
            return [j for j in data if (j.get("category_name") or "").lower() == "development"]
        except Exception as e:
            print(f"[WorkingNomads] Error fetching jobs: {e}")
            return []

    def parse_job(self, raw_job: Dict[str, Any]) -> Optional[Job]:
        title = raw_job.get("title")
        url = raw_job.get("url")
        if not title or not url:
            return None

        company = raw_job.get("company_name") or "Unknown"
        loc_req = raw_job.get("location_requirement") or "Global"
        location = f"Remote ({loc_req})" if "remote" not in loc_req.lower() else loc_req

        description = raw_job.get("description") or ""
        tags = []
        raw_tags = raw_job.get("tags") or []
        for t in raw_tags:
            if isinstance(t, dict):
                tags.append(t.get("name", ""))
            elif isinstance(t, str):
                tags.append(t)

        pub_str = raw_job.get("pub_date")
        posted_time = datetime.now(timezone.utc)
        if pub_str:
            try:
                posted_time = datetime.fromisoformat(pub_str)
                if posted_time.tzinfo is None:
                    posted_time = posted_time.replace(tzinfo=timezone.utc)
            except Exception:
                pass

        desc_lower = description.lower()
        has_relocation = "relocation" in desc_lower
        has_visa = "visa" in desc_lower or "sponsorship" in desc_lower

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
