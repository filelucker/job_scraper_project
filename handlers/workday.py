import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from handlers.base import BaseHandler, Job

class WorkdayHandler(BaseHandler):
    """Handler for companies using the Workday Recruiting portal Candidate Experience (CXS) API."""

    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        # Token is assumed to be host + path, e.g. "ebay.wd5.myworkdayjobs.com/wday/cxs/ebay/apply"
        # We need to construct:
        # - Landing page URL: https://{host}/{site}/
        # - API URL: https://{token}/jobs
        parts = self.token.split('/')
        host = parts[0]
        
        if len(parts) >= 5:
            site = parts[4]
            landing_url = f"https://{host}/{site}/"
        else:
            landing_url = f"https://{host}/apply/"
            
        api_url = f"https://{self.token}/jobs"
        
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        
        try:
            # 1. Initialize session and fetch CSRF token from the landing page
            r_landing = session.get(landing_url, timeout=15)
            r_landing.raise_for_status()
            
            csrf_token = session.cookies.get("CALYPSO_CSRF_TOKEN")
            
            # 2. Setup POST headers
            post_headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Referer": landing_url,
                "Origin": f"https://{host}"
            }
            if csrf_token:
                post_headers["X-Calypso-Csrf-Token"] = csrf_token
                
            payload = {
                "appliedFacets": {},
                "limit": 20,
                "offset": 0,
                "searchText": ""
            }
            
            # 3. Query the job board API
            response = session.post(api_url, json=payload, headers=post_headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data.get("jobPostings", [])
        except requests.RequestException as e:
            # Check for bot detection or network issues (like DNS resolution errors)
            # Since Workday frequently blocks automated clients, log gracefully as a warning
            print(f"[Workday - {self.company_name}] Failed to scan board: {e}")
            return []
        except ValueError as e:
            print(f"[Workday - {self.company_name}] JSON decoding error: {e}")
            return []

    def parse_job(self, raw_job: Dict[str, Any]) -> Optional[Job]:
        title = raw_job.get("title")
        external_path = raw_job.get("externalPath")
        location = raw_job.get("locationsText", "Remote / Not Specified")
        
        parts = self.token.split('/')
        host = parts[0]
        job_url = f"https://{host}{external_path}" if external_path else None
        
        # Workday dates are relative strings like "Posted Today", "Posted Yesterday", "Posted 2 Days Ago"
        posted_on = raw_job.get("postedOn", "")
        posted_time = datetime.now(timezone.utc)
        
        if posted_on:
            posted_on_clean = posted_on.lower()
            if "today" in posted_on_clean:
                posted_time = datetime.now(timezone.utc)
            elif "yesterday" in posted_on_clean:
                posted_time = datetime.now(timezone.utc) - timedelta(days=1)
            elif "days ago" in posted_on_clean:
                try:
                    days = int(''.join(filter(str.isdigit, posted_on_clean)))
                    posted_time = datetime.now(timezone.utc) - timedelta(days=days)
                except ValueError:
                    pass
            elif "30+" in posted_on_clean or "month" in posted_on_clean:
                # Force to be outside lookback window (e.g. 40 days ago)
                posted_time = datetime.now(timezone.utc) - timedelta(days=40)
                
        if not title or not job_url:
            return None

        return Job(
            company=self.company_name,
            title=title.strip(),
            location=location.strip(),
            url=job_url,
            posted_time=posted_time
        )
