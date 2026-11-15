import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from handlers.base import BaseHandler, Job

class JobicyHandler(BaseHandler):
    """
    Handler for Jobicy Remote Jobs API.
    Provides verified remote engineering listings worldwide.
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
        self.api_url = "https://jobicy.com/api/v2/remote-jobs"

    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        """Fetch remote engineering, dev, and data-science jobs from Jobicy public REST API."""
        industries = ["engineering", "dev", "data-science"]
        all_jobs = []
        seen_ids = set()

        for ind in industries:
            try:
                params = {"count": 100, "industry": ind}
                resp = requests.get(
                    self.api_url,
                    params=params,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                    timeout=15
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for job in data.get("jobs", []):
                        jid = job.get("id") or job.get("url")
                        if jid and jid not in seen_ids:
                            seen_ids.add(jid)
                            all_jobs.append(job)
            except Exception as e:
                print(f"[Jobicy] Error fetching jobs for {ind}: {e}")

        return all_jobs

    def parse_job(self, raw_job: Dict[str, Any]) -> Optional[Job]:
        title = raw_job.get("jobTitle")
        url = raw_job.get("url")
        if not title or not url:
            return None

        company = raw_job.get("companyName") or "Unknown"
        geo = raw_job.get("jobGeo") or "Anywhere"
        location = f"Remote ({geo})" if "remote" not in geo.lower() else geo

        description = raw_job.get("jobDescription") or ""
        tags = []
        for field in ("jobIndustry", "jobType"):
            val = raw_job.get(field)
            if isinstance(val, list):
                tags.extend([str(v).strip() for v in val if v])
            elif isinstance(val, str) and val.strip():
                tags.append(val.strip())

        # Parse publication date
        pub_date_str = raw_job.get("pubDate")
        posted_time = datetime.now(timezone.utc)
        if pub_date_str:
            try:
                posted_time = datetime.fromisoformat(pub_date_str)
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

