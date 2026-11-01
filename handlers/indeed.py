import time
import re
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from handlers.base import BaseHandler, Job

class IndeedHandler(BaseHandler):
    """
    Handler for scraping Indeed jobs.
    Uses direct browser automation (Playwright) by default with zero API fees or limits,
    with an optional fallback to Apify actor if explicitly configured.
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
        country: str = "us",
        countries: Optional[List[Dict[str, str]]] = None,
        compound_rules: Optional[List[Dict[str, Any]]] = None
    ):
        super().__init__(company_name, token, keywords, lookback_hours, only_remote_or_hybrid, compound_rules=compound_rules)
        self.apify_api_token = apify_api_token
        self.actor_name = actor_name
        self.location = location
        self.country = country.upper()
        self.countries = countries or [{"name": "Default", "indeed_domain": f"www.indeed.com" if country.lower() == "us" else f"{country.lower()}.indeed.com"}]

    def _fetch_via_playwright(self) -> List[Dict[str, Any]]:
        """Fetch jobs directly from Indeed via Playwright with no API tokens, fees, or quota limits."""
        import urllib.parse
        from playwright.sync_api import sync_playwright

        all_results = []
        query = " OR ".join([f'"{kw}"' for kw in self.keywords])
        fromage = 1 if self.lookback_hours <= 24 else (3 if self.lookback_hours <= 72 else 7)
        
        print(f"[Indeed - Direct] Initiating direct browser scrape for {len(self.countries)} domain(s) without API limits...")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                )
                
                for country_cfg in self.countries:
                    domain = country_cfg.get("indeed_domain") or "www.indeed.com"
                    encoded_query = urllib.parse.quote(query)
                    encoded_location = urllib.parse.quote(self.location)
                    search_url = f"https://{domain}/jobs?q={encoded_query}&l={encoded_location}&fromage={fromage}&sort=date"
                    
                    print(f"[Indeed - Direct] Scraping {domain}...")
                    try:
                        resp = page.goto(search_url, timeout=30000)
                        if not resp or resp.status != 200:
                            print(f"[Indeed - Direct] {domain} returned status {resp.status if resp else 'None'}. Skipping.")
                            continue
                        page.wait_for_timeout(2000)
                        
                        # Extract structured jobs from window.mosaic
                        mosaic_jobs = page.evaluate("""() => {
                            const m = window.mosaic;
                            if (!m || !m.providerData) return [];
                            const jc = m.providerData['mosaic-provider-jobcards'];
                            if (!jc || !jc.metaData) return [];
                            const model = jc.metaData.mosaicProviderJobCardsModel;
                            return (model && model.results) ? model.results : [];
                        }""")
                        
                        if mosaic_jobs:
                            for mj in mosaic_jobs:
                                jk = mj.get("jobkey")
                                if not jk:
                                    continue
                                all_results.append({
                                    "title": mj.get("displayTitle") or mj.get("title"),
                                    "company": mj.get("company") or mj.get("companyName"),
                                    "location": mj.get("formattedLocation") or self.location,
                                    "url": f"https://{domain}/viewjob?jk={jk}",
                                    "pubDate": mj.get("pubDate")
                                })
                        else:
                            # Fallback DOM card scraping
                            dom_cards = page.evaluate("""(domain) => {
                                const cards = document.querySelectorAll('.job_seen_beacon, div[data-jk]');
                                const out = [];
                                for (const c of cards) {
                                    const titleEl = c.querySelector('h2.jobTitle, a[data-jk]');
                                    const compEl = c.querySelector('[data-testid="company-name"], .companyName');
                                    const locEl = c.querySelector('[data-testid="text-location"], .companyLocation');
                                    const jk = c.getAttribute('data-jk') || (titleEl ? titleEl.getAttribute('data-jk') : '');
                                    if (titleEl && jk) {
                                        out.push({
                                            title: titleEl.innerText.trim(),
                                            company: compEl ? compEl.innerText.trim() : 'Indeed Employer',
                                            location: locEl ? locEl.innerText.trim() : 'Remote',
                                            url: `https://${domain}/viewjob?jk=${jk}`
                                        });
                                    }
                                }
                                return out;
                            }""", domain)
                            all_results.extend(dom_cards)
                            
                    except Exception as domain_err:
                        print(f"[Indeed - Direct] Error fetching {domain}: {domain_err}")
                
                browser.close()
        except Exception as e:
            print(f"[Indeed - Direct] Playwright browser error: {e}")
            
        print(f"[Indeed - Direct] Successfully fetched {len(all_results)} job posting(s).")
        return all_results

    def _fetch_via_apify(self) -> List[Dict[str, Any]]:
        """Fallback to Apify actor if configured."""
        if not self.apify_api_token or self.apify_api_token.startswith("your_apify_"):
            return []

        actor_id = self.actor_name.replace("/", "~")
        run_url = f"https://api.apify.com/v2/acts/{actor_id}/runs?token={self.apify_api_token}"

        query = " OR ".join([f'"{kw}"' for kw in self.keywords])

        import urllib.parse
        start_urls = []
        for country_cfg in self.countries:
            domain = country_cfg.get("indeed_domain") or "www.indeed.com"
            fromage = 1 if self.lookback_hours <= 24 else (3 if self.lookback_hours <= 72 else 7)
            
            encoded_query = urllib.parse.quote(query)
            encoded_location = urllib.parse.quote(self.location)
            url = f"https://{domain}/jobs?q={encoded_query}&l={encoded_location}&fromage={fromage}&sort=date"
            start_urls.append({"url": url})

        payload = {
            "startUrls": start_urls,
            "maxItemsPerSearch": 100
        }

        print(f"[Indeed - Apify] Triggering actor {self.actor_name} with {len(start_urls)} target startUrls...")
        try:
            response = requests.post(run_url, json=payload, timeout=60)
            response.raise_for_status()
            run_data = response.json().get("data", {})
            run_id = run_data.get("id")
            dataset_id = run_data.get("defaultDatasetId")
        except Exception as e:
            print(f"[Indeed - Apify] Error starting Actor run: {e}")
            return []

        if not run_id or not dataset_id:
            return []

        status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={self.apify_api_token}"
        start_time = time.time()
        timeout_seconds = 300
        poll_interval = 10

        while time.time() - start_time < timeout_seconds:
            try:
                status_resp = requests.get(status_url, timeout=30)
                status_resp.raise_for_status()
                status = status_resp.json().get("data", {}).get("status")
                
                if status == "SUCCEEDED":
                    break
                elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                    return []
            except Exception:
                pass
            time.sleep(poll_interval)
        else:
            return []

        items_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={self.apify_api_token}"
        try:
            items_resp = requests.get(items_url, timeout=60)
            items_resp.raise_for_status()
            return items_resp.json()
        except Exception:
            return []

    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        # 1. Prefer unlimited, zero-cost direct Playwright scraping
        try:
            jobs = self._fetch_via_playwright()
            if jobs:
                return jobs
        except Exception as e:
            print(f"[Indeed] Direct scrape encountered error: {e}")

        # 2. Fallback to Apify only if direct returned nothing AND an active token is configured
        if self.apify_api_token and not self.apify_api_token.startswith("your_apify_"):
            return self._fetch_via_apify()

        return []

    def _parse_indeed_date(self, date_val: Any) -> datetime:
        now = datetime.now(timezone.utc)
        if not date_val:
            return now

        # Handle numeric epoch timestamps (milliseconds or seconds)
        if isinstance(date_val, (int, float)):
            try:
                if date_val > 1e11:
                    return datetime.fromtimestamp(date_val / 1000.0, tz=timezone.utc)
                return datetime.fromtimestamp(date_val, tz=timezone.utc)
            except Exception:
                return now

        date_str = str(date_val).lower().strip()
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
        title = raw_job.get("positionName") or raw_job.get("job_title") or raw_job.get("title") or raw_job.get("jobTitle") or raw_job.get("displayTitle")
        company = raw_job.get("company") or raw_job.get("company_name") or raw_job.get("companyName") or "Indeed Posting"
        url = raw_job.get("url") or raw_job.get("externalApplyLink") or raw_job.get("link") or raw_job.get("job_url")
        location = raw_job.get("location") or raw_job.get("formattedLocation") or "Remote"

        if not title or not url:
            return None

        title = title.strip()
        company = company.strip()
        url = url.strip()

        date_val = raw_job.get("postedAt") or raw_job.get("postingDateParsed") or raw_job.get("date") or raw_job.get("posted_at") or raw_job.get("pubDate")
        posted_time = self._parse_indeed_date(date_val)

        return Job(
            company=company,
            title=title,
            location=location,
            url=url,
            posted_time=posted_time
        )
