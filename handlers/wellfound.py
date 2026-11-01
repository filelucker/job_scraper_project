import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from handlers.base import BaseHandler, Job

class WellfoundHandler(BaseHandler):
    """
    Handler for scraping Wellfound (formerly AngelList Talent) startup jobs
    using direct browser automation (Playwright) with zero API keys or credit limits.
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
        super().__init__(company_name, token, keywords, lookback_hours, only_remote_or_hybrid, compound_rules=compound_rules)

    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        from playwright.sync_api import sync_playwright

        all_listings = []
        target_urls = [
            "https://wellfound.com/jobs",
            "https://wellfound.com/role/software-engineer",
            "https://wellfound.com/role/ios-developer",
            "https://wellfound.com/role/android-developer",
            "https://wellfound.com/role/mobile-engineer",
            "https://wellfound.com/role/full-stack-engineer",
            "https://wellfound.com/role/flutter-developer"
        ]
        
        print(f"[Wellfound - Direct] Scanning {len(target_urls)} startup portals via Playwright (zero-cost, no limit)...")
        seen_job_ids = set()
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                )
                
                for url in target_urls:
                    try:
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
                            
                        data = next_data.get("props", {}).get("pageProps", {}).get("apolloState", {}).get("data", {})
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
                            
                            all_listings.append({
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
                    except Exception as role_err:
                        print(f"[Wellfound - Direct] Error fetching {url}: {role_err}")
                        
                browser.close()
        except Exception as e:
            print(f"[Wellfound - Direct] Playwright browser error: {e}")
            
        print(f"[Wellfound - Direct] Extracted {len(all_listings)} unique startup job listing(s).")
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

