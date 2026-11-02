import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from handlers.base import BaseHandler, Job

class RemoteOKHandler(BaseHandler):
    """
    Handler for RemoteOK public API.
    One of the largest global remote worker and developer job boards.
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
        self.api_url = "https://remoteok.com/api"

    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        """Fetch remote developer listings from RemoteOK public REST API."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            resp = requests.get(self.api_url, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            # First item in RemoteOK is a legal notice dictionary without job keys
            if isinstance(data, list) and len(data) > 1:
                return [j for j in data[1:] if isinstance(j, dict) and j.get("position")]
            return []
        except Exception as e:
            print(f"[RemoteOK] Error fetching jobs: {e}")
            return []

    def parse_job(self, raw_job: Dict[str, Any]) -> Optional[Job]:
        title = raw_job.get("position")
        url = raw_job.get("apply_url") or raw_job.get("url")
        if not title or not url:
            return None

        company = raw_job.get("company") or "RemoteOK Partner"
        raw_loc = raw_job.get("location") or "Worldwide"
        location = f"Remote ({raw_loc})" if "remote" not in raw_loc.lower() else raw_loc

        description = raw_job.get("description") or ""
        tags = [str(t).strip() for t in (raw_job.get("tags") or []) if t]

        # Parse publication date (ISO format with timezone offset)
        date_str = raw_job.get("date")
        posted_time = datetime.now(timezone.utc)
        if date_str:
            try:
                posted_time = datetime.fromisoformat(date_str)
                if posted_time.tzinfo is None:
                    posted_time = posted_time.replace(tzinfo=timezone.utc)
            except Exception:
                pass

        desc_lower = description.lower()
        has_relocation = "relocation" in desc_lower or any("relocat" in t.lower() for t in tags)
        has_visa = "visa" in desc_lower or "sponsorship" in desc_lower or any("visa" in t.lower() for t in tags)

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

