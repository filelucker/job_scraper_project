import time
import urllib.parse
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from handlers.base import BaseHandler, Job

class LinkedInHandler(BaseHandler):
    """
    Handler for scraping LinkedIn jobs using Apify.
    Uses curious_coder/linkedin-jobs-scraper by default.
    """
    def __init__(
        self,
        company_name: str,
        token: str,
        keywords: List[str],
        lookback_hours: int = 24,
        only_remote_or_hybrid: bool = False,
        apify_api_token: str = "",
        actor_name: str = "curious_coder/linkedin-jobs-scraper",
        location: str = "Remote"
    ):
        super().__init__(company_name, token, keywords, lookback_hours, only_remote_or_hybrid)
        self.apify_api_token = apify_api_token
        self.actor_name = actor_name
        self.location = location

    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        if not self.apify_api_token:
            print(f"[LinkedIn - Apify] Info: APIFY_API_TOKEN is not set. Skipping LinkedIn.")
            return []

        # Replace slash with tilde for Apify API URL path
        actor_id = self.actor_name.replace("/", "~")
        run_url = f"https://api.apify.com/v2/acts/{actor_id}/runs?token={self.apify_api_token}"

        # Combine keywords using OR. Joins them as: ("Flutter" OR "Android" ...)
        query = " OR ".join([f'"{kw}"' for kw in self.keywords])
        
        # Build URL-encoded search link for cookieless scrapers (like curious_coder)
        encoded_query = urllib.parse.quote(query)
        encoded_location = urllib.parse.quote(self.location)
        
        # Determine Work Type parameter f_WT: 2 = Remote, 3 = Hybrid
        wt_param = ""
        if self.only_remote_or_hybrid:
            wt_param = "&f_WT=2%2C3"
            
        # Determine Time Posted parameter f_TPR
        if self.lookback_hours <= 24:
            tpr_param = "&f_TPR=r86400"
        elif self.lookback_hours <= 168:
            tpr_param = "&f_TPR=r604800"
        else:
            tpr_param = "&f_TPR=r2592000"

        search_url = f"https://www.linkedin.com/jobs/search/?keywords={encoded_query}&location={encoded_location}{wt_param}{tpr_param}&sortBy=DD"

        # Map lookback hours to datePosted filter (for actors that support it)
        if self.lookback_hours <= 24:
            date_posted = "r86400"
        elif self.lookback_hours <= 168:
            date_posted = "r604800"
        else:
            date_posted = "r2592000"

        # Determine payload structure depending on the actor
        if "curious_coder" in self.actor_name:
            payload = {
                "urls": [search_url],
                "maxJobs": 100
            }
        else:
            # Fallback format for bebity or other actors
            payload = {
                "title": query,
                "location": self.location,
                "datePosted": date_posted,
                "proxy": {
                    "useApifyProxy": True
                }
            }

        print(f"[LinkedIn - Apify] Triggering actor {self.actor_name} with target URL: {search_url[:100]}...")
        try:
            # We explicitly pass timeout to override the monkeypatched 30s session timeout
            response = requests.post(run_url, json=payload, timeout=60)
            response.raise_for_status()
            run_data = response.json().get("data", {})
            run_id = run_data.get("id")
            dataset_id = run_data.get("defaultDatasetId")
        except Exception as e:
            print(f"[LinkedIn - Apify] Error starting Actor run: {e}")
            return []

        if not run_id or not dataset_id:
            print(f"[LinkedIn - Apify] Error: Actor did not return run_id or dataset_id.")
            return []

        # Poll for completion
        status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={self.apify_api_token}"
        start_time = time.time()
        timeout_seconds = 300  # 5 minutes max timeout
        poll_interval = 10     # Poll every 10 seconds

        print(f"[LinkedIn - Apify] Actor run {run_id} started. Polling status...")
        while time.time() - start_time < timeout_seconds:
            try:
                status_resp = requests.get(status_url, timeout=30)
                status_resp.raise_for_status()
                status_data = status_resp.json().get("data", {})
                status = status_data.get("status")
                
                elapsed = int(time.time() - start_time)
                print(f"[LinkedIn - Apify] Run status: {status} (elapsed: {elapsed}s)")
                
                if status == "SUCCEEDED":
                    break
                elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                    print(f"[LinkedIn - Apify] Actor run ended with status: {status}")
                    return []
            except Exception as e:
                print(f"[LinkedIn - Apify] Warning: Polling error: {e}")
            
            time.sleep(poll_interval)
        else:
            print(f"[LinkedIn - Apify] Polling timed out after {timeout_seconds} seconds. Aborting.")
            try:
                abort_url = f"https://api.apify.com/v2/actor-runs/{run_id}/abort?token={self.apify_api_token}"
                requests.post(abort_url, timeout=10)
            except Exception:
                pass
            return []

        # Fetch items from dataset
        items_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={self.apify_api_token}"
        print(f"[LinkedIn - Apify] Fetching dataset items...")
        try:
            items_resp = requests.get(items_url, timeout=60)
            items_resp.raise_for_status()
            return items_resp.json()
        except Exception as e:
            print(f"[LinkedIn - Apify] Error fetching dataset items: {e}")
            return []

    def matches_location(self, location: str, title: str) -> bool:
        # LinkedIn search query parameters (f_WT=2%2C3) strictly filter for remote/hybrid jobs,
        # so we bypass local text-based geographical location validation to prevent false negatives.
        return True

    def parse_job(self, raw_job: Dict[str, Any]) -> Optional[Job]:
        # Handle variations in Apify scraper schemas
        title = raw_job.get("job_title") or raw_job.get("title") or raw_job.get("jobTitle")
        company = raw_job.get("company_name") or raw_job.get("company") or raw_job.get("companyName") or "LinkedIn Posting"
        url = raw_job.get("url") or raw_job.get("link") or raw_job.get("job_url")
        location = raw_job.get("location") or "Remote"

        if not title or not url:
            return None

        title = title.strip()
        company = company.strip()
        url = url.strip()

        # Parse publication date
        posted_time = None
        for key in ["posted_at", "date", "postedAt"]:
            val = raw_job.get(key)
            if val:
                try:
                    # Replace Zulu timezone 'Z' to '+00:00' for fromisoformat compatibility in older Pythons
                    if isinstance(val, str) and val.endswith("Z"):
                        val = val[:-1] + "+00:00"
                    posted_time = datetime.fromisoformat(val)
                    break
                except Exception:
                    pass

        if not posted_time:
            posted_time = datetime.now(timezone.utc)

        return Job(
            company=company,
            title=title,
            location=location,
            url=url,
            posted_time=posted_time
        )
