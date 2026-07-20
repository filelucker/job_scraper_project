import time
import re
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from handlers.base import BaseHandler, Job

class IndeedHandler(BaseHandler):
    """
    Handler for scraping Indeed jobs using Apify.
    Uses misceres/indeed-scraper by default.
    """
    def __init__(
        self,
        company_name: str,
        token: str,
        keywords: List[str],
        lookback_hours: int = 24,
        only_remote_or_hybrid: bool = False,
        apify_api_token: str = "",
        actor_name: str = "misceres/indeed-scraper",
        location: str = "Remote",
        country: str = "us"
    ):
        super().__init__(company_name, token, keywords, lookback_hours, only_remote_or_hybrid)
        self.apify_api_token = apify_api_token
        self.actor_name = actor_name
        self.location = location
        self.country = country.upper()

    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        if not self.apify_api_token:
            print(f"[Indeed - Apify] Info: APIFY_API_TOKEN is not set. Skipping Indeed.")
            return []

        # Replace slash with tilde for Apify API URL path
        actor_id = self.actor_name.replace("/", "~")
        run_url = f"https://api.apify.com/v2/acts/{actor_id}/runs?token={self.apify_api_token}"

        # Combine keywords using OR
        query = " OR ".join([f'"{kw}"' for kw in self.keywords])

        payload = {
            "position": query,
            "location": self.location,
            "country": self.country,
            "maxItemsPerSearch": 100
        }

        print(f"[Indeed - Apify] Triggering actor {self.actor_name} for query: {query[:100]}...")
        try:
            # We explicitly pass timeout to override the monkeypatched 30s session timeout
            response = requests.post(run_url, json=payload, timeout=60)
            response.raise_for_status()
            run_data = response.json().get("data", {})
            run_id = run_data.get("id")
            dataset_id = run_data.get("defaultDatasetId")
        except Exception as e:
            print(f"[Indeed - Apify] Error starting Actor run: {e}")
            return []

        if not run_id or not dataset_id:
            print(f"[Indeed - Apify] Error: Actor did not return run_id or dataset_id.")
            return []

        # Poll for completion
        status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={self.apify_api_token}"
        start_time = time.time()
        timeout_seconds = 300  # 5 minutes max timeout
        poll_interval = 10     # Poll every 10 seconds

        print(f"[Indeed - Apify] Actor run {run_id} started. Polling status...")
        while time.time() - start_time < timeout_seconds:
            try:
                status_resp = requests.get(status_url, timeout=30)
                status_resp.raise_for_status()
                status_data = status_resp.json().get("data", {})
                status = status_data.get("status")
                
                elapsed = int(time.time() - start_time)
                print(f"[Indeed - Apify] Run status: {status} (elapsed: {elapsed}s)")
                
                if status == "SUCCEEDED":
                    break
                elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                    print(f"[Indeed - Apify] Actor run ended with status: {status}")
                    return []
            except Exception as e:
                print(f"[Indeed - Apify] Warning: Polling error: {e}")
            
            time.sleep(poll_interval)
        else:
            print(f"[Indeed - Apify] Polling timed out after {timeout_seconds} seconds. Aborting.")
            try:
                abort_url = f"https://api.apify.com/v2/actor-runs/{run_id}/abort?token={self.apify_api_token}"
                requests.post(abort_url, timeout=10)
            except Exception:
                pass
            return []

        # Fetch items from dataset
        items_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={self.apify_api_token}"
        print(f"[Indeed - Apify] Fetching dataset items...")
        try:
            items_resp = requests.get(items_url, timeout=60)
            items_resp.raise_for_status()
            return items_resp.json()
        except Exception as e:
            print(f"[Indeed - Apify] Error fetching dataset items: {e}")
            return []

    def _parse_indeed_date(self, date_str: str) -> datetime:
        now = datetime.now(timezone.utc)
        if not date_str:
            return now
        
        date_str = date_str.lower().strip()
        if "just" in date_str or "today" in date_str or "now" in date_str or "active" in date_str:
            return now

        match = re.search(r'(\d+)\s+(day|hour|minute|week|month)s?', date_str)
        if match:
            val = int(match.group(1))
            unit = match.group(2)
            if unit == "day":
                return now - timedelta(days=val)
            elif unit == "hour":
                return now - timedelta(hours=val)
            elif unit == "minute":
                return now - timedelta(minutes=val)
            elif unit == "week":
                return now - timedelta(weeks=val)
            elif unit == "month":
                return now - timedelta(days=val * 30)

        # ISO format fallback
        try:
            if date_str.endswith("z"):
                date_str = date_str[:-1] + "+00:00"
            return datetime.fromisoformat(date_str)
        except Exception:
            pass

        return now

    def parse_job(self, raw_job: Dict[str, Any]) -> Optional[Job]:
        title = raw_job.get("positionName") or raw_job.get("job_title") or raw_job.get("title") or raw_job.get("jobTitle")
        company = raw_job.get("company") or raw_job.get("company_name") or raw_job.get("companyName") or "Indeed Posting"
        url = raw_job.get("url") or raw_job.get("externalApplyLink") or raw_job.get("link") or raw_job.get("job_url")
        location = raw_job.get("location") or "Remote"

        if not title or not url:
            return None

        title = title.strip()
        company = company.strip()
        url = url.strip()

        # Parse relative or absolute date
        date_val = raw_job.get("postedAt") or raw_job.get("postingDateParsed") or raw_job.get("date") or raw_job.get("posted_at")
        posted_time = self._parse_indeed_date(date_val)

        return Job(
            company=company,
            title=title,
            location=location,
            url=url,
            posted_time=posted_time
        )
