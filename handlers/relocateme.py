import re
import urllib.parse
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from email.utils import parsedate_to_datetime
from handlers.base import BaseHandler, Job

class RelocateMeHandler(BaseHandler):
    """
    Handler for Relocate.me international relocation & visa sponsorship job board.
    Supports:
    1. Direct search scraping from https://relocate.me/international-jobs?query=...
    2. Private Substack / The Global Move RSS feed link (with personal token)
    3. Logged-in session cookie on relocate.me (optional)
    """
    def __init__(
        self,
        company_name: str,
        token: str,
        keywords: List[str],
        lookback_hours: int = 24,
        only_remote_or_hybrid: bool = False,
        session_cookie: str = "",
        feed_url: str = "",
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
        self.feed_url = feed_url
        self.base_url = "https://relocate.me"

    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        raw_jobs = []
        seen_urls = set()

        # 1. If user provided a private RSS feed link (e.g. Substack / The Global Move)
        if self.feed_url:
            try:
                resp = requests.get(self.feed_url, headers={"User-Agent": "JobScraper/1.0"}, timeout=15)
                if resp.status_code == 200:
                    root = ET.fromstring(resp.content)
                    for item in root.findall(".//item"):
                        title = item.findtext("title", "")
                        link = item.findtext("link", "")
                        pub_date_str = item.findtext("pubDate", "")
                        desc = item.findtext("description", "")
                        if link not in seen_urls:
                            seen_urls.add(link)
                            raw_jobs.append({
                                "title": title,
                                "url": link,
                                "pubDate": pub_date_str,
                                "description": desc,
                                "company": "Relocate.me Verified Employer",
                                "location": "Europe / Germany",
                                "source": "rss"
                            })
            except Exception as e:
                print(f"[Relocate.me] Error fetching feed: {e}")

        # 2. Query Relocate.me search pages directly
        search_terms = ["Android", "Mobile", "Developer", "Engineer"]
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        if self.session_cookie:
            headers["Cookie"] = self.session_cookie

        for term in search_terms:
            encoded_q = urllib.parse.quote_plus(term)
            url = f"{self.base_url}/international-jobs?query={encoded_q}"
            try:
                resp = requests.get(url, headers=headers, timeout=15)
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                titles = soup.find_all(class_=lambda c: c and "job__title" in c)
                
                for t in titles:
                    a = t.find("a")
                    if not a or not a.get("href"):
                        continue
                    
                    href = a["href"]
                    # Skip promotional / non-job cards
                    if "/the-global-move/" in href or "1000-curated" in href:
                        continue

                    full_url = f"{self.base_url}{href}" if href.startswith("/") else href
                    if full_url in seen_urls:
                        continue
                    seen_urls.add(full_url)

                    parent = t.parent
                    strings = [s.strip() for s in parent.stripped_strings] if parent else []

                    country = strings[0] if len(strings) > 0 else "Europe"
                    company = strings[1] if len(strings) > 1 else "Unknown"
                    title = strings[2] if len(strings) > 2 else a.get_text(strip=True)
                    city_text = strings[3] if len(strings) > 3 else ""
                    city = re.sub(r'^in\s+', '', city_text, flags=re.IGNORECASE).strip()
                    location = f"{city}, {country}" if city and country else (city or country or "Germany")
                    description = strings[4] if len(strings) > 4 else ""

                    raw_jobs.append({
                        "title": title,
                        "url": full_url,
                        "company": company,
                        "location": location,
                        "description": description,
                        "source": "web"
                    })
            except Exception as e:
                print(f"[Relocate.me] Error fetching query '{term}': {e}")

        return raw_jobs

    def parse_job(self, raw_job: Dict[str, Any]) -> Optional[Job]:
        title = raw_job.get("title")
        url = raw_job.get("url")
        if not title or not url:
            return None

        posted_time = datetime.now(timezone.utc)
        pub_date = raw_job.get("pubDate")
        if pub_date:
            try:
                posted_time = parsedate_to_datetime(pub_date)
            except Exception:
                pass

        company = raw_job.get("company", "Relocate.me Partner")
        location = raw_job.get("location", "Germany")
        description = raw_job.get("description", "")

        return Job(
            company=company.strip(),
            title=title.strip(),
            location=location.strip(),
            url=url.strip(),
            posted_time=posted_time,
            description=description,
            has_visa_sponsorship=True,
            has_relocation=True
        )
