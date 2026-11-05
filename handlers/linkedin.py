import os
import re
import time
import urllib.parse
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from handlers.base import BaseHandler, Job

class LinkedInHandler(BaseHandler):
    """
    Handler for scraping LinkedIn jobs with Three-Tier Architecture:
      - Tier 1A: LinkedIn Voyager API using direct session cookies (adapted from api-anything)
      - Tier 1B: LinkedIn Public Guest Search API (Zero credentials / zero cost)
      - Tier 1C: Apify Actor integration (curious_coder/linkedin-jobs-scraper)
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
        location: str = "Remote",
        countries: Optional[List[Dict[str, str]]] = None,
        compound_rules: Optional[List[Dict[str, Any]]] = None,
        li_at: Optional[str] = None,
        jsessionid: Optional[str] = None
    ):
        super().__init__(company_name, token, keywords, lookback_hours, only_remote_or_hybrid, compound_rules=compound_rules)
        self.apify_api_token = apify_api_token if apify_api_token is not None else os.getenv("APIFY_API_TOKEN", "")
        self.actor_name = actor_name
        self.location = location
        self.countries = countries or [{"name": "Default", "linkedin_location": location}]
        self.li_at = li_at if li_at is not None else os.getenv("LINKEDIN_LI_AT", "")
        self.jsessionid = jsessionid if jsessionid is not None else os.getenv("LINKEDIN_JSESSIONID", "")

    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        # 1. Tier 1A: Direct Voyager API with session cookies
        if self.li_at and self.jsessionid:
            print(f"[LinkedIn - Direct Voyager API] Using authenticated session cookies...")
            voyager_jobs = self._fetch_via_voyager()
            if voyager_jobs:
                return voyager_jobs
            print(f"[LinkedIn - Direct Voyager API] No jobs returned, falling back...")

        # 2. Tier 1C: Apify Actor (if API token is explicitly provided)
        if self.apify_api_token:
            return self._fetch_via_apify()

        # 3. Tier 1B: Public Guest Search API fallback (Zero credentials required)
        print(f"[LinkedIn - Guest API] Querying public job search endpoint without credentials...")
        return self._fetch_via_guest_api()

    def _fetch_via_voyager(self) -> List[Dict[str, Any]]:
        """Directly queries LinkedIn's internal Voyager API using session cookies."""
        csrf = self.jsessionid.strip("\"'")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "csrf-token": csrf,
            "x-restli-protocol-version": "2.0.0"
        }
        cookies = {
            "li_at": self.li_at,
            "JSESSIONID": self.jsessionid
        }

        query = " ".join(self.keywords)
        # Avoid characters that break Rest.li syntax
        safe_query = re.sub(r"[(),:]", "", query)
        encoded_query = urllib.parse.quote(safe_query)
        url = f"https://www.linkedin.com/voyager/api/search/dash/clusters?q=all&query=(keywords:{encoded_query},flagshipSearchIntent:SEARCH_SRP,queryParameters:(resultType:List(JOBS)),includeFiltersInResponse:false)&start=0&count=25"

        try:
            resp = requests.get(url, headers=headers, cookies=cookies, timeout=20)
            if resp.status_code != 200:
                print(f"[LinkedIn - Voyager API] Request returned status {resp.status_code}")
                return []

            data = resp.json()
            jobs = []
            elements = data.get("elements", [])
            for elem in elements:
                items = elem.get("items", [])
                for item in items:
                    entity = item.get("itemUnion", {}).get("entityResult")
                    if not entity:
                        continue
                    title = (entity.get("title") or {}).get("text")
                    company = (entity.get("primarySubtitle") or {}).get("text")
                    location = (entity.get("secondarySubtitle") or {}).get("text")
                    nav_url = entity.get("navigationUrl", "")
                    if title and nav_url:
                        jobs.append({
                            "title": title,
                            "companyName": company or "LinkedIn Employer",
                            "link": nav_url,
                            "location": location or "Remote",
                            "postedAt": datetime.now(timezone.utc).isoformat()
                        })
            return jobs
        except Exception as e:
            print(f"[LinkedIn - Voyager API] Error querying Voyager API: {e}")
            return []

    def _fetch_via_guest_api(self) -> List[Dict[str, Any]]:
        """Queries public guest job search endpoint without requiring any credentials."""
        query = " OR ".join([f'"{kw}"' for kw in self.keywords])
        encoded_query = urllib.parse.quote(query)

        # Lookback filter
        if self.lookback_hours <= 24:
            tpr_param = "&f_TPR=r86400"
        elif self.lookback_hours <= 168:
            tpr_param = "&f_TPR=r604800"
        else:
            tpr_param = "&f_TPR=r2592000"

        wt_param = "&f_WT=2%2C3" if self.only_remote_or_hybrid else ""

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"
        }

        all_jobs = []
        for country_cfg in self.countries:
            loc = country_cfg.get("linkedin_location") or self.location
            encoded_loc = urllib.parse.quote(loc)
            url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={encoded_query}&location={encoded_loc}{wt_param}{tpr_param}&start=0"

            try:
                resp = requests.get(url, headers=headers, timeout=20)
                if resp.status_code != 200:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.find_all("div", class_=lambda c: c and "base-card" in c)
                if not cards:
                    cards = soup.find_all("li")

                for card in cards:
                    title_elem = card.find("h3", class_=lambda c: c and "title" in c)
                    company_elem = card.find("h4", class_=lambda c: c and "subtitle" in c)
                    loc_elem = card.find("span", class_=lambda c: c and "location" in c)
                    link_elem = card.find("a", class_=lambda c: c and ("full-link" in c or "title" in c)) or card.find("a", href=lambda h: h and "/jobs/view/" in h)

                    title = title_elem.get_text(strip=True) if title_elem else ""
                    company = company_elem.get_text(strip=True) if company_elem else "LinkedIn Employer"
                    location = loc_elem.get_text(strip=True) if loc_elem else self.location
                    link = link_elem["href"] if link_elem and link_elem.has_attr("href") else ""

                    if title and link:
                        clean_link = link.split("?")[0]
                        all_jobs.append({
                            "title": title,
                            "companyName": company,
                            "link": clean_link,
                            "location": location,
                            "postedAt": datetime.now(timezone.utc).isoformat()
                        })
            except Exception as e:
                print(f"[LinkedIn - Guest API] Error fetching {loc}: {e}")

        print(f"[LinkedIn - Guest API] Discovered {len(all_jobs)} public listings.")
        return all_jobs

    def _fetch_via_apify(self) -> List[Dict[str, Any]]:
        """Legacy Apify Actor execution."""
        actor_id = self.actor_name.replace("/", "~")
        run_url = f"https://api.apify.com/v2/acts/{actor_id}/runs?token={self.apify_api_token}"

        query = " OR ".join([f'"{kw}"' for kw in self.keywords])
        encoded_query = urllib.parse.quote(query)
        
        wt_param = "&f_WT=2%2C3" if self.only_remote_or_hybrid else ""
        if self.lookback_hours <= 24:
            tpr_param = "&f_TPR=r86400"
            date_posted = "r86400"
        elif self.lookback_hours <= 168:
            tpr_param = "&f_TPR=r604800"
            date_posted = "r604800"
        else:
            tpr_param = "&f_TPR=r2592000"
            date_posted = "r2592000"

        search_urls = []
        for country_cfg in self.countries:
            loc = country_cfg.get("linkedin_location") or self.location
            encoded_location = urllib.parse.quote(loc)
            search_url = f"https://www.linkedin.com/jobs/search/?keywords={encoded_query}&location={encoded_location}{wt_param}{tpr_param}&sortBy=DD"
            search_urls.append(search_url)

        if "curious_coder" in self.actor_name:
            payload = {
                "urls": search_urls,
                "maxJobs": 100
            }
        else:
            payload = {
                "title": query,
                "location": self.countries[0].get("linkedin_location") or self.location,
                "datePosted": date_posted,
                "proxy": {
                    "useApifyProxy": True
                }
            }

        print(f"[LinkedIn - Apify] Triggering actor {self.actor_name} with {len(search_urls)} target URLs...")
        try:
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

        status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={self.apify_api_token}"
        start_time = time.time()
        timeout_seconds = 300
        poll_interval = 10

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
        return True

    def parse_job(self, raw_job: Dict[str, Any]) -> Optional[Job]:
        title = raw_job.get("job_title") or raw_job.get("title") or raw_job.get("jobTitle")
        company = raw_job.get("company_name") or raw_job.get("company") or raw_job.get("companyName") or "LinkedIn Posting"
        url = raw_job.get("url") or raw_job.get("link") or raw_job.get("job_url")
        location = raw_job.get("location") or "Remote"

        if not title or not url:
            return None

        title = title.strip()
        company = company.strip()
        url = url.strip()

        posted_time = None
        for key in ["posted_at", "date", "postedAt"]:
            val = raw_job.get(key)
            if val:
                try:
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
