import re
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
from handlers.base import BaseHandler, Job

class WeAreDevelopersHandler(BaseHandler):
    """
    Handler for scraping WeAreDevelopers jobs board.
    Fetches job listings from https://www.wearedevelopers.com/en/jobs?q=...
    Public web listings: No API key required.
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
        self.base_url = "https://www.wearedevelopers.com"

    def _parse_relative_time(self, text: str) -> datetime:
        """Converts relative string e.g. '2 hours ago', '3 days ago' to UTC datetime."""
        now = datetime.now(timezone.utc)
        clean = (text or "").lower().strip()
        
        if not clean or "just now" in clean or "second" in clean or "minute" in clean:
            return now
            
        m_hour = re.search(r'(\d+)\s+hour', clean)
        if m_hour:
            return now - timedelta(hours=int(m_hour.group(1)))
            
        if "yesterday" in clean:
            return now - timedelta(days=1)
            
        m_day = re.search(r'(\d+)\s+day', clean)
        if m_day:
            return now - timedelta(days=int(m_day.group(1)))
            
        m_week = re.search(r'(\d+)\s+week', clean)
        if m_week:
            return now - timedelta(weeks=int(m_week.group(1)))
            
        m_month = re.search(r'(\d+)\s+month', clean)
        if m_month:
            return now - timedelta(days=int(m_month.group(1)) * 30)
            
        return now

    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        """Query WeAreDevelopers search pages for key mobile & visa queries."""
        search_terms = ["Android", "Flutter", "Mobile", "visa sponsorship"]
        raw_jobs = []
        seen_urls = set()

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"
        }

        for term in search_terms:
            encoded_q = urllib.parse.quote_plus(term)
            url = f"{self.base_url}/en/jobs?q={encoded_q}"
            try:
                resp = requests.get(url, headers=headers, timeout=15)
                if resp.status_code != 200:
                    continue
                
                soup = BeautifulSoup(resp.text, "html.parser")
                articles = soup.find_all("article")
                
                for art in articles:
                    link_el = art.find("a", href=lambda x: x and "/jobs/" in x)
                    if not link_el:
                        continue
                        
                    rel_url = link_el.get("href", "")
                    full_url = f"{self.base_url}{rel_url}" if rel_url.startswith("/") else rel_url
                    if full_url in seen_urls:
                        continue
                    seen_urls.add(full_url)

                    heading = art.find(["h2", "h3", "h4"])
                    strings = [s.strip() for s in art.stripped_strings]
                    
                    title = heading.get_text(strip=True) if heading else (strings[1] if len(strings) > 1 else "")
                    age_text = strings[0] if strings else ""
                    company = strings[2] if len(strings) > 2 else "Unknown Company"
                    location = strings[3] if len(strings) > 3 else "Remote"
                    tags = strings[4:] if len(strings) > 4 else []

                    raw_jobs.append({
                        "title": title,
                        "url": full_url,
                        "company": company,
                        "location": location,
                        "age_text": age_text,
                        "tags": tags
                    })
            except Exception as e:
                print(f"[WeAreDevelopers] Error querying '{term}': {e}")

        return raw_jobs

    def parse_job(self, raw_job: Dict[str, Any]) -> Optional[Job]:
        title = raw_job.get("title")
        url = raw_job.get("url")
        if not title or not url:
            return None

        company = raw_job.get("company") or "Unknown"
        location = raw_job.get("location") or "Remote"
        tags = raw_job.get("tags") or []
        age_text = raw_job.get("age_text") or ""
        posted_time = self._parse_relative_time(age_text)

        all_text = f"{title} {location} {' '.join(tags)}".lower()
        has_visa = "visa" in all_text or "sponsorship" in all_text
        has_relocation = "relocation" in all_text

        return Job(
            company=company.strip(),
            title=title.strip(),
            location=location.strip(),
            url=url.strip(),
            posted_time=posted_time,
            description=" ".join(tags),
            tags=tags,
            has_visa_sponsorship=has_visa,
            has_relocation=has_relocation
        )
