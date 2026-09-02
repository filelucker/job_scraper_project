import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from handlers.base import BaseHandler, Job

class GermanTechJobsHandler(BaseHandler):
    """
    Handler for GermanTechJobs (DevITJobs / JobCopilot network).
    Requires a free registered account session cookie or auth token.
    """
    def __init__(
        self,
        company_name: str,
        token: str,
        keywords: List[str],
        lookback_hours: int = 24,
        only_remote_or_hybrid: bool = False,
        session_cookie: str = "",
        auth_token: str = "",
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
        self.session_cookie = session_cookie
        self.auth_token = auth_token

    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        """Fetch jobs using session cookie or auth token."""
        if not self.session_cookie and not self.auth_token:
            return []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/html, */*",
        }
        if self.session_cookie:
            headers["Cookie"] = self.session_cookie
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}" if not self.auth_token.startswith("Bearer ") else self.auth_token

        target_urls = [
            "https://devitjobs.jobcopilot.com/api/jobs?country=de&visa=true",
            "https://devitjobs.jobcopilot.com/jobs?country=de&visa=true",
            "https://germantechjobs.de/jobs/all/Germany/visa-sponsorship"
        ]

        raw_jobs = []
        for url in target_urls:
            try:
                resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
                if resp.status_code != 200:
                    continue

                content_type = resp.headers.get("content-type", "")
                if "json" in content_type:
                    data = resp.json()
                    jobs_list = data if isinstance(data, list) else data.get("jobs", data.get("data", []))
                    for item in jobs_list:
                        raw_jobs.append(item)
                    if raw_jobs:
                        break
                else:
                    # HTML fallback parsing
                    soup = BeautifulSoup(resp.text, "html.parser")
                    job_cards = soup.find_all(["div", "article"], class_=lambda c: c and ("job" in c.lower() or "card" in c.lower()))
                    for card in job_cards:
                        link = card.find("a", href=True)
                        heading = card.find(["h2", "h3", "h4"])
                        if link and heading:
                            raw_jobs.append({
                                "title": heading.get_text(strip=True),
                                "url": link["href"],
                                "company": "GermanTechJobs Employer",
                                "location": "Germany",
                                "tags": [t.get_text(strip=True) for t in card.find_all("span")]
                            })
                    if raw_jobs:
                        break
            except Exception as e:
                print(f"[GermanTechJobs] Error requesting {url}: {e}")

        return raw_jobs

    def parse_job(self, raw_job: Dict[str, Any]) -> Optional[Job]:
        title = raw_job.get("title") or raw_job.get("name")
        url = raw_job.get("url") or raw_job.get("link") or raw_job.get("applyUrl")
        if not title or not url:
            return None

        if url.startswith("/"):
            url = f"https://germantechjobs.de{url}"

        company = raw_job.get("company") or raw_job.get("companyName") or "Unknown"
        location = raw_job.get("location") or raw_job.get("city") or "Germany"
        tags = raw_job.get("tags") or raw_job.get("technologies") or []
        description = raw_job.get("description") or ""

        return Job(
            company=str(company).strip(),
            title=str(title).strip(),
            location=str(location).strip(),
            url=str(url).strip(),
            posted_time=datetime.now(timezone.utc),
            description=str(description),
            tags=[str(t) for t in tags],
            has_visa_sponsorship=True,
            has_relocation=True
        )
