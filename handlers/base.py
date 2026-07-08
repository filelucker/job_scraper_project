import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

class Job:
    """Represents a standardized job posting."""
    def __init__(self, company: str, title: str, location: str, url: str, posted_time: datetime):
        self.company = company
        self.title = title
        self.location = location
        self.url = url
        self.posted_time = posted_time  # Must be timezone-aware datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert job representation to a dictionary for routers."""
        return {
            "Company": self.company,
            "Title": self.title,
            "Location": self.location,
            "URL": self.url,
            "Date Found": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        }

    def __repr__(self) -> str:
        return f"<Job {self.company} - {self.title}>"


class BaseHandler:
    """Abstract base class for all job board handlers."""
    def __init__(self, company_name: str, token: str, keywords: List[str], lookback_hours: int = 24):
        self.company_name = company_name
        self.token = token
        self.keywords = keywords
        self.lookback_hours = lookback_hours

    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        """Fetch raw jobs from the target API. Must be implemented by subclasses."""
        raise NotImplementedError("fetch_raw_jobs must be implemented by subclasses.")

    def parse_job(self, raw_job: Dict[str, Any]) -> Optional[Job]:
        """Parse raw API dictionary into a standardized Job object. Must be implemented by subclasses."""
        raise NotImplementedError("parse_job must be implemented by subclasses.")

    def matches_keywords(self, title: str) -> bool:
        """
        Check if the job title matches any of the target keywords using case-insensitive whole-word matching.
        """
        if not title:
            return False
        
        for keyword in self.keywords:
            # We want case-insensitive, whole-word matching.
            # A boundary character is start/end of string, or any character that is not alphanumeric.
            # This handles special characters in keywords like 'AI/ML' cleanly.
            escaped_keyword = re.escape(keyword)
            pattern = rf"(?:^|[^a-zA-Z0-9]){escaped_keyword}(?:$|[^a-zA-Z0-9])"
            if re.search(pattern, title, re.IGNORECASE):
                return True
        return False

    def is_within_lookback(self, posted_time: datetime) -> bool:
        """Verify if the job posting was created/updated within the lookback window."""
        if not posted_time:
            return False
        
        # Ensure timezone-aware calculation
        now = datetime.now(timezone.utc)
        if posted_time.tzinfo is None:
            # Assume UTC if naive
            posted_time = posted_time.replace(tzinfo=timezone.utc)
            
        delta = now - posted_time
        delta_hours = delta.total_seconds() / 3600.0
        return 0 <= delta_hours <= self.lookback_hours

    def execute(self) -> List[Job]:
        """Orchestrate the fetch, parse, and filter steps."""
        matching_jobs = []
        raw_listings = self.fetch_raw_jobs()
        
        for raw_job in raw_listings:
            try:
                job = self.parse_job(raw_job)
                if not job:
                    continue
                
                # Apply filters: title and posting date
                if self.matches_keywords(job.title) and self.is_within_lookback(job.posted_time):
                    matching_jobs.append(job)
            except Exception as e:
                # Log parsing errors but don't fail the overall run
                print(f"[{self.company_name}] Error parsing job listing: {e}")
                
        return matching_jobs
