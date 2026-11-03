import re
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from handlers.base import BaseHandler, Job

class LandingJobsHandler(BaseHandler):
    """
    Handler for Landing.jobs public API.
    Premier tech job marketplace for Europe, UK, and global remote developers.
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
        self.api_url = "https://landing.jobs/api/v1/jobs"

    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        """Fetch listings from Landing.jobs public REST API."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            resp = requests.get(self.api_url, headers=headers, timeout=15)
            if resp.status_code == 403:
                print("[LandingJobs] API returned 403 Forbidden (Cloudflare WAF / runner IP block). Skipping.")
                return []
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return [j for j in data if isinstance(j, dict) and j.get("title") and j.get("url")]
            return []
        except Exception as e:
            print(f"[LandingJobs] Error fetching jobs: {e}")
            return []

    def parse_job(self, raw_job: Dict[str, Any]) -> Optional[Job]:
        title = raw_job.get("title")
        url = raw_job.get("url")
        if not title or not url:
            return None

        company = raw_job.get("company_name")
        if not company and url:
            # Extract company from path e.g. https://landing.jobs/at/inscale/...
            m = re.search(r'/at/([^/]+)/', url)
            company = m.group(1).replace('-', ' ').title() if m else "Landing.jobs Partner"
        elif not company:
            company = "Landing.jobs Partner"

        # Determine location
        city = raw_job.get("city") or ""
        country = raw_job.get("country_name") or ""
        is_remote = bool(raw_job.get("remote"))

        if is_remote:
            loc_str = f"{city}, {country}".strip(', ')
            location = f"Remote ({loc_str})" if loc_str else "Remote"
        elif city or country:
            location = f"{city}, {country}".strip(', ')
        else:
            location = "Europe / Remote"

        raw_tags = raw_job.get("tags") or []
        tags = [str(t).strip() for t in raw_tags if t]

        # Parse publication date e.g. 2026-10-31T09:38:38.127Z
        pub_str = raw_job.get("published_at")
        posted_time = datetime.now(timezone.utc)
        if pub_str:
            try:
                # Replace 'Z' with '+00:00' for fromisoformat compatibility
                posted_time = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                if posted_time.tzinfo is None:
                    posted_time = posted_time.replace(tzinfo=timezone.utc)
            except Exception:
                pass

        has_relocation = any("relocat" in t.lower() for t in tags)
        has_visa = any("visa" in t.lower() or "sponsorship" in t.lower() for t in tags)

        return Job(
            company=company,
            title=title,
            location=location,
            url=url,
            posted_time=posted_time,
            description=" ".join(tags),
            tags=tags,
            has_visa_sponsorship=has_visa,
            has_relocation=has_relocation
        )

