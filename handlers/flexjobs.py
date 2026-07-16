import re
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from handlers.base import BaseHandler, Job

class FlexjobsHandler(BaseHandler):
    """
    Handler for scraping job listings from FlexJobs public search.
    Since FlexJobs doesn't offer a public API or RSS feed, we construct search pages
    for target keywords, fetch them, and parse the jobs from the HTML results.
    """
    def __init__(self, company_name: str, token: str, keywords: List[str], lookback_hours: int = 24, only_remote_or_hybrid: bool = False):
        super().__init__(company_name, token, keywords, lookback_hours, only_remote_or_hybrid)
        
    def _get_minimal_keywords(self) -> List[str]:
        """
        Optimize search queries by removing redundant keywords (subsets).
        For example, if we search "Flutter", it will return "Flutter Developer" jobs,
        so we do not need to perform a separate query for "Flutter Developer".
        """
        # Sort keywords by length so shorter (broader) terms are evaluated first
        sorted_kws = sorted(self.keywords, key=len)
        minimal_kws = []
        for kw in sorted_kws:
            kw_lower = kw.lower()
            if not any(min_kw.lower() in kw_lower for min_kw in minimal_kws):
                minimal_kws.append(kw)
        return minimal_kws

    def _parse_date(self, date_str: str) -> datetime:
        """
        Parse date strings like 'July 15, 2026' or relative strings like
        'Today', 'Yesterday', or 'X days ago' into a timezone-aware datetime.
        """
        date_str = date_str.strip().lower()
        now = datetime.now(timezone.utc)
        if not date_str:
            return now
            
        if "today" in date_str:
            return now
        if "yesterday" in date_str:
            return now - timedelta(days=1)
            
        match = re.search(r"(\d+)\s+days?\s+ago", date_str)
        if match:
            days = int(match.group(1))
            return now - timedelta(days=days)
            
        for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"):
            try:
                parsed_dt = datetime.strptime(date_str, fmt)
                return parsed_dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
                
        # Fallback if no patterns match
        return now

    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        minimal_kws = self._get_minimal_keywords()
        print(f"[FlexJobs] Optimized target keywords: {minimal_kws}")
        
        raw_listings = []
        seen_ids = set()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        for kw in minimal_kws:
            # Respect rate limits and avoid aggressive requests
            time.sleep(3.0)
            url = f"https://www.flexjobs.com/search?search={requests.utils.quote(kw)}"
            print(f"[FlexJobs] Fetching results for keyword '{kw}'...")
            
            response = None
            retries = 3
            backoff = 2.0
            for attempt in range(retries):
                try:
                    response = requests.get(url, headers=headers, timeout=30)
                    break
                except Exception as e:
                    if attempt == retries - 1:
                        print(f"[FlexJobs] Error: Failed to fetch search results for '{kw}' after {retries} attempts: {e}")
                    else:
                        sleep_time = backoff * (2 ** attempt)
                        print(f"[FlexJobs] Request failed or timed out. Retrying in {sleep_time:.1f}s... ({e})")
                        time.sleep(sleep_time)
                        
            if response is None or response.status_code != 200:
                if response:
                    print(f"[FlexJobs] Warning: Failed to fetch search results for '{kw}' (HTTP {response.status_code})")
                continue
                
            try:
                soup = BeautifulSoup(response.text, "html.parser")
                job_items = soup.find_all("li", class_="job-search-item")
                
                for item in job_items:
                    job_id = item.get("data-id")
                    if not job_id:
                        link_tag = item.find("a", class_="job-link")
                        if link_tag:
                            job_id = link_tag.get("id", "").replace("job-name-", "")
                    
                    if not job_id or job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)
                    
                    link_tag = item.find("a", class_="job-link")
                    if not link_tag:
                        continue
                        
                    title = link_tag.get_text(strip=True)
                    href = link_tag.get("href")
                    job_url = f"https://www.flexjobs.com{href}" if href else ""
                    
                    posted_tag = item.find("span", class_="job-posted")
                    posted_str = posted_tag.get_text(strip=True) if posted_tag else ""
                    
                    type_loc_tag = item.find("span", class_="job-type-and-location")
                    type_loc_str = type_loc_tag.get_text(strip=True) if type_loc_tag else ""
                    
                    raw_listings.append({
                        "id": job_id,
                        "title": title,
                        "url": job_url,
                        "posted_str": posted_str,
                        "location_and_type": type_loc_str
                    })
            except Exception as e:
                print(f"[FlexJobs] Error fetching search results for '{kw}': {e}")
                
        return raw_listings

    def parse_job(self, raw_job: Dict[str, Any]) -> Optional[Job]:
        title = raw_job.get("title", "").strip()
        url = raw_job.get("url", "").strip()
        posted_str = raw_job.get("posted_str", "")
        location_and_type = raw_job.get("location_and_type", "").strip()
        
        if not title or not url:
            return None
            
        # Clean double spaces or linebreaks in title
        title = re.sub(r"\s+", " ", title).strip()
            
        # Parse the company name out of the title if a separator is present
        company = "FlexJobs Employer"
        for sep in (" — ", " - "):
            if sep in title:
                parts = title.split(sep)
                company = parts[-1].strip()
                title = sep.join(parts[:-1]).strip()
                break
                
        # Standardize location
        location = "Remote"
        if location_and_type:
            # E.g., "Full-Time, Remote (Colombia)" or just "Remote"
            location = re.sub(r"\s+", " ", location_and_type).strip()
            
        posted_time = self._parse_date(posted_str)
        
        return Job(
            company=company,
            title=title,
            location=location,
            url=url,
            posted_time=posted_time
        )
