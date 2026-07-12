import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from handlers.base import BaseHandler, Job
from jobhive.scrapers.base import get_scraper
from jobhive.models import ATSType

class JobhiveAdapterHandler(BaseHandler):
    """Handler that wraps jobhive-py scrapers to support Greenhouse, Lever, Ashby, SmartRecruiters, Workable, Workday, etc."""
    
    def __init__(self, company_name: str, token: str, keywords: List[str], lookback_hours: int = 24, ats_type: str = "", only_remote_or_hybrid: bool = False):
        super().__init__(company_name, token, keywords, lookback_hours, only_remote_or_hybrid)
        self.ats_type = ats_type

    def execute(self) -> List[Job]:
        matching_jobs = []
        try:
            # For workday, convert our internal API token to the full URL expected by jobhive's WorkdayScraper
            scraper_token = self.token
            if self.ats_type == "workday":
                parts = self.token.split("/")
                if len(parts) >= 5:
                    host = parts[0]
                    site = parts[4]
                    scraper_token = f"https://{host}/{site}"
                elif not self.token.startswith("https://") and not self.token.startswith("http://"):
                    scraper_token = f"https://{self.token}"

            # Instantiate the correct jobhive scraper using its registration name/enum.
            # We set a shorter 15.0s timeout to prevent individual slow boards from dragging down the pipeline.
            scraper = get_scraper(self.ats_type, scraper_token, timeout=15.0)
            # Disable descriptions retrieval to optimize network latency & speed up queries
            scraper.include_descriptions = False
            
            # Fetch the parsed Pydantic job models
            raw_jobs = scraper.fetch()
        except Exception as e:
            print(f"[{self.ats_type.upper()} - {self.company_name}] Failed to scan/fetch: {e}")
            return []
            
        for jobhive_job in raw_jobs:
            try:
                title = jobhive_job.title
                url = str(jobhive_job.url)
                location = jobhive_job.location or "Remote / Not Specified"
                posted_at = jobhive_job.posted_at
                
                if not title or not url:
                    continue
                    
                # Apply target tracking keyword matching
                if not self.matches_keywords(title):
                    continue
                    
                # Apply location filtering if enabled
                if not self.matches_location(location, title):
                    continue
                    
                # Handle posting date / timezone alignment
                if posted_at:
                    if posted_at.tzinfo is None:
                        posted_time = posted_at.replace(tzinfo=timezone.utc)
                    else:
                        posted_time = posted_at
                else:
                    posted_time = datetime.now(timezone.utc)
                    
                # Verify lookback timeframe
                if not self.is_within_lookback(posted_time):
                    continue
                    
                matching_jobs.append(Job(
                    company=self.company_name,
                    title=title.strip(),
                    location=location.strip(),
                    url=url.strip(),
                    posted_time=posted_time
                ))
            except Exception as e:
                print(f"[{self.ats_type.upper()} - {self.company_name}] Error parsing job: {e}")
                
        return matching_jobs
