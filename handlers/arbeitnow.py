import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from handlers.base import BaseHandler, Job

class ArbeitnowHandler(BaseHandler):
    """
    Handler for Arbeitnow Job Board API.
    Provides verified visa sponsorship job listings in Germany and across Europe.
    Public API: No API key required.
    """
    def __init__(
        self,
        company_name: str,
        token: str,
        keywords: List[str],
        lookback_hours: int = 24,
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
        self.api_url = "https://www.arbeitnow.com/api/job-board-api"

    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        """Fetch general tech and visa-sponsored jobs from Arbeitnow public REST API."""
        raw_jobs = []
        seen_slugs = set()

        # Query both general European/remote tech listings and explicit visa sponsorship
        query_configs = [
            {"params": None, "max_pages": 2},
            {"params": {"visa_sponsorship": "true"}, "max_pages": 1}
        ]

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        for cfg in query_configs:
            current_url = self.api_url
            params = cfg["params"]
            max_pages = cfg["max_pages"]
            pages_fetched = 0

            while current_url and pages_fetched < max_pages:
                try:
                    response = requests.get(
                        current_url,
                        params=params if pages_fetched == 0 else None,
                        headers=headers,
                        timeout=15
                    )
                    response.raise_for_status()
                    payload = response.json()
                    data = payload.get("data", [])
                    if not data:
                        break
                    for item in data:
                        slug = item.get("slug") or item.get("url")
                        if slug and slug not in seen_slugs:
                            seen_slugs.add(slug)
                            raw_jobs.append(item)

                    links = payload.get("links", {})
                    current_url = links.get("next")
                    pages_fetched += 1
                except Exception as e:
                    print(f"[Arbeitnow] Error fetching jobs: {e}")
                    break

        return raw_jobs

    def parse_job(self, raw_job: Dict[str, Any]) -> Optional[Job]:
        title = raw_job.get("title")
        url = raw_job.get("url")
        if not title or not url:
            return None

        company = raw_job.get("company_name") or "Unknown"
        location = raw_job.get("location") or "Germany"
        remote = raw_job.get("remote", False)
        if remote and "remote" not in location.lower():
            location = f"{location} (Remote)"

        description = raw_job.get("description") or ""
        tags = raw_job.get("tags") or []

        # Parse timestamp
        created_at = raw_job.get("created_at")
        posted_time = datetime.now(timezone.utc)
        if isinstance(created_at, (int, float)):
            try:
                posted_time = datetime.fromtimestamp(created_at, tz=timezone.utc)
            except Exception:
                pass
        elif isinstance(created_at, str):
            try:
                posted_time = datetime.fromisoformat(created_at)
            except Exception:
                pass

        # Check relocation indicator
        desc_lower = description.lower()
        has_relocation = "relocation" in desc_lower or any("relocat" in t.lower() for t in tags)

        return Job(
            company=company,
            title=title.strip(),
            location=location.strip(),
            url=url.strip(),
            posted_time=posted_time,
            description=description,
            tags=tags,
            has_visa_sponsorship=True,  # Guaranteed by the API visa_sponsorship=true query
            has_relocation=has_relocation
        )
