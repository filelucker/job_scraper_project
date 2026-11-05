import re
import json
import time
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from handlers.base import BaseHandler, Job

class WellfoundHandler(BaseHandler):
    """
    Handler for scraping Wellfound (formerly AngelList Talent) startup jobs
    using a Three-Tier Fallback Strategy (inspired by api-anything):
      - Tier 1: Ultra-fast plain HTTP requests extracting embedded __NEXT_DATA__ Apollo state.
      - Tier 2: Playwright + Stealth browser execution if Tier 1 is challenged or blocked.
    Zero third-party API keys or credit limits required.
    """
    
    TARGET_URLS = [
        "https://wellfound.com/jobs",
        "https://wellfound.com/role/software-engineer",
        "https://wellfound.com/role/ios-developer",
        "https://wellfound.com/role/android-developer",
        "https://wellfound.com/role/mobile-engineer",
        "https://wellfound.com/role/full-stack-engineer",
        "https://wellfound.com/role/flutter-developer"
    ]

    HTTP_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "sec-ch-ua": "\"Chromium\";v=\"128\", \"Google Chrome\";v=\"128\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    }

    def __init__(
        self,
        company_name: str,
        token: str,
        keywords: List[str],
        lookback_hours: int = 24,
        only_remote_or_hybrid: bool = False,
        compound_rules: Optional[List[Dict[str, Any]]] = None
    ):
        super().__init__(company_name, token, keywords, lookback_hours, only_remote_or_hybrid, compound_rules=compound_rules)

    def _extract_from_apollo_data(self, data: Dict[str, Any], seen_job_ids: set) -> List[Dict[str, Any]]:
        """Extracts job listing dictionaries from an Apollo GraphQL state cache."""
        listings = []
        startups = {k: v for k, v in data.items() if k.startswith("Startup:")}

        for k, v in data.items():
            if not k.startswith("JobListing:"):
                continue
            jid = v.get("id")
            if not jid or jid in seen_job_ids:
                continue
            seen_job_ids.add(jid)

            startup_ref = (v.get("startup") or {}).get("__ref")
            startup = startups.get(startup_ref, {})

            listings.append({
                "id": jid,
                "slug": v.get("slug"),
                "title": v.get("title"),
                "startup_name": startup.get("name", "Startup"),
                "startup_slug": startup.get("slug"),
                "location_names": v.get("locationNames", []),
                "accepted_remote": v.get("acceptedRemoteLocationNames", []),
                "remote": v.get("remote", False),
                "liveStartAt": v.get("liveStartAt")
            })
        return listings

    def _fetch_tier1_http(self, url: str) -> Optional[Dict[str, Any]]:
        """Tier 1: Direct HTTP request fetching embedded __NEXT_DATA__ Apollo cache."""
        try:
            resp = requests.get(url, headers=self.HTTP_HEADERS, timeout=12)
            if resp.status_code != 200:
                return None
            
            # Extract __NEXT_DATA__ script block
            match = re.search(r'<script\s+id="__NEXT_DATA__"\s+type="application/json">(.*?)</script>', resp.text, re.DOTALL)
            if not match:
                return None
            
            next_data = json.loads(match.group(1))
            return next_data.get("props", {}).get("pageProps", {}).get("apolloState", {}).get("data")
        except Exception:
            return None

    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        all_listings = []
        seen_job_ids = set()
        unresolved_urls = []

        print(f"[Wellfound - Tier 1 HTTP] Attempting direct HTTP extraction for {len(self.TARGET_URLS)} portals...")
        for url in self.TARGET_URLS:
            apollo_data = self._fetch_tier1_http(url)
            if apollo_data:
                extracted = self._extract_from_apollo_data(apollo_data, seen_job_ids)
                all_listings.extend(extracted)
            else:
                unresolved_urls.append(url)

        if not unresolved_urls:
            print(f"[Wellfound - Tier 1 HTTP] Successfully resolved all portals via direct HTTP! ({len(all_listings)} listings)")
            return all_listings

        # Tier 2 Fallback: Playwright Browser for challenged / unresolved URLs
        print(f"[Wellfound - Tier 2 Fallback] Escalating {len(unresolved_urls)} blocked/unresolved portal(s) to Playwright...")
        from playwright.sync_api import sync_playwright

        try:
            from playwright_stealth import Stealth
            stealth = Stealth()
        except Exception:
            stealth = None

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                for url in unresolved_urls:
                    context = None
                    try:
                        context = browser.new_context(
                            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                        )
                        page = context.new_page()
                        if stealth:
                            stealth.apply_stealth_sync(page)

                        resp = page.goto(url, timeout=25000)
                        if not resp or resp.status != 200:
                            continue
                        page.wait_for_timeout(1500)

                        next_data = page.evaluate("""() => {
                            const el = document.getElementById('__NEXT_DATA__');
                            return el ? JSON.parse(el.textContent) : null;
                        }""")

                        if not next_data:
                            continue

                        apollo_data = next_data.get("props", {}).get("pageProps", {}).get("apolloState", {}).get("data", {})
                        extracted = self._extract_from_apollo_data(apollo_data, seen_job_ids)
                        all_listings.extend(extracted)
                    except Exception as role_err:
                        print(f"[Wellfound - Tier 2 Fallback] Error fetching {url}: {role_err}")
                    finally:
                        if context:
                            try:
                                context.close()
                            except Exception:
                                pass
                browser.close()
        except Exception as e:
            print(f"[Wellfound - Tier 2 Fallback] Playwright browser error: {e}")

        print(f"[Wellfound] Extracted {len(all_listings)} total unique startup job listing(s).")
        return all_listings

    def parse_job(self, raw_job: Dict[str, Any]) -> Optional[Job]:
        title = raw_job.get("title")
        company = raw_job.get("startup_name") or "Startup"
        jid = raw_job.get("id")
        slug = raw_job.get("slug")
        
        if not title or not jid:
            return None
            
        url = f"https://wellfound.com/jobs/{jid}-{slug}" if slug else f"https://wellfound.com/jobs/{jid}"
        
        loc_list = raw_job.get("location_names", []) + raw_job.get("accepted_remote", [])
        location = ", ".join(loc_list) if loc_list else ""
        if raw_job.get("remote"):
            location = f"Remote / {location}" if location else "Remote"
        if not location:
            location = "Remote / United States"
            
        epoch = raw_job.get("liveStartAt")
        if epoch:
            try:
                posted_time = datetime.fromtimestamp(epoch, tz=timezone.utc)
            except Exception:
                posted_time = datetime.now(timezone.utc)
        else:
            posted_time = datetime.now(timezone.utc)
            
        return Job(
            company=company,
            title=title.strip(),
            location=location.strip(),
            url=url.strip(),
            posted_time=posted_time
        )
