import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from handlers.base import BaseHandler, Job

class TheMuseHandler(BaseHandler):
    """
    Handler for The Muse public API.
    A leading global career destination with over 90,000+ verified tech opportunities.
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
        self.api_url = "https://www.themuse.com/api/public/jobs"

    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        """Fetch latest software engineering jobs across the first 2 pages (40 jobs)."""
        raw_jobs = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        for page in range(2):
            try:
                params = {
                    "category": "Software Engineering",
                    "page": page
                }
                resp = requests.get(self.api_url, params=params, headers=headers, timeout=15)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                results = data.get("results", [])
                if not results:
                    break
                raw_jobs.extend(results)
            except Exception as e:
                print(f"[TheMuse] Error fetching page {page}: {e}")
                break
        return raw_jobs

    def parse_job(self, raw_job: Dict[str, Any]) -> Optional[Job]:
        title = raw_job.get("name")
        refs = raw_job.get("refs") or {}
        url = refs.get("landing_page")
        if not title or not url:
            return None

        company_dict = raw_job.get("company") or {}
        company = company_dict.get("name") or "The Muse Partner"

        locs = [loc.get("name") for loc in raw_job.get("locations", []) if loc.get("name")]
        location = ", ".join(locs) if locs else "Flexible / Remote"

        description = raw_job.get("contents") or ""
        tags = []
        for cat in raw_job.get("categories", []):
            if cat.get("name"):
                tags.append(cat["name"])
        for lvl in raw_job.get("levels", []):
            if lvl.get("name"):
                tags.append(lvl["name"])

        # Parse publication date e.g. 2026-10-01T22:29:21Z
        pub_str = raw_job.get("publication_date")
        posted_time = datetime.now(timezone.utc)
        if pub_str:
            try:
                posted_time = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
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
            has_visa_sponsorship=has_visa,
            has_relocation=has_relocation
        )
