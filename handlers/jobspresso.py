import re
import requests
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from handlers.base import BaseHandler, Job

class JobspressoHandler(BaseHandler):
    """
    Handler for Jobspresso RSS feed.
    Curated remote careers in Software Development, Mobile, and Tech.
    Public RSS feeds: No API key required.
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
        self.feed_urls = [
            "https://jobspresso.co/category/remote-software-jobs/feed/",
            "https://jobspresso.co/feed/"
        ]

    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        """Fetch remote engineering jobs from Jobspresso public RSS feeds."""
        raw_jobs = []
        seen_links = set()
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        for feed_url in self.feed_urls:
            try:
                resp = requests.get(feed_url, headers=headers, timeout=15)
                if resp.status_code != 200:
                    continue
                root = ET.fromstring(resp.text)
                for item in root.findall("./channel/item"):
                    link_elem = item.find("link")
                    url = link_elem.text if link_elem is not None else ""
                    if not url or url in seen_links:
                        continue
                    seen_links.add(url)

                    title_elem = item.find("title")
                    pub_date_elem = item.find("pubDate")
                    desc_elem = item.find("description")

                    raw_jobs.append({
                        "raw_title": title_elem.text if title_elem is not None else "",
                        "url": url,
                        "pub_date": pub_date_elem.text if pub_date_elem is not None else "",
                        "description": desc_elem.text if desc_elem is not None else ""
                    })
            except Exception as e:
                print(f"[Jobspresso] Error fetching feed {feed_url}: {e}")

        return raw_jobs

    def parse_job(self, raw_job: Dict[str, Any]) -> Optional[Job]:
        raw_title = (raw_job.get("raw_title") or "").strip()
        url = raw_job.get("url")
        if not raw_title or not url:
            return None

        # Jobspresso titles often format as "Job Title at Company" or "Job Title – Company"
        company = "Jobspresso Partner"
        title = raw_title
        if " at " in raw_title:
            parts = raw_title.split(" at ", 1)
            title = parts[0].strip()
            company = parts[1].strip()
        elif " @ " in raw_title:
            parts = raw_title.split(" @ ", 1)
            title = parts[0].strip()
            company = parts[1].strip()
        elif " – " in raw_title:
            parts = raw_title.split(" – ", 1)
            title = parts[0].strip()
            company = parts[1].strip()

        location = "Remote (Worldwide)"
        description = raw_job.get("description") or ""

        # Parse RFC 2822 date
        posted_time = datetime.now(timezone.utc)
        pub_str = raw_job.get("pub_date")
        if pub_str:
            try:
                posted_time = parsedate_to_datetime(pub_str)
                if posted_time.tzinfo is None:
                    posted_time = posted_time.replace(tzinfo=timezone.utc)
            except Exception:
                pass

        return Job(
            company=company,
            title=title,
            location=location,
            url=url,
            posted_time=posted_time,
            description=description,
            tags=["Remote", "Software"]
        )

