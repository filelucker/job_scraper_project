import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

class Job:
    """Represents a standardized job posting."""
    def __init__(
        self,
        company: str,
        title: str,
        location: str,
        url: str,
        posted_time: datetime,
        description: str = "",
        tags: Optional[List[str]] = None,
        has_visa_sponsorship: bool = False,
        has_relocation: bool = False
    ):
        self.company = company
        self.title = title
        self.location = location
        self.url = self.normalize_url(url)
        self.posted_time = posted_time  # Must be timezone-aware datetime
        self.description = description or ""
        self.tags = tags or []
        self.has_visa_sponsorship = has_visa_sponsorship
        self.has_relocation = has_relocation

    def normalize_url(self, url: str) -> str:
        """Strip tracking parameters and localized subdomains to ensure robust deduplication."""
        if not url:
            return ""
        
        import urllib.parse
        parsed = urllib.parse.urlparse(url.strip())
        
        if "linkedin.com" in parsed.netloc and "/jobs/view/" in parsed.path:
            # Extract the ID from the path (e.g. /jobs/view/title-12345 or /jobs/view/12345)
            match = re.search(r'(\d+)/?$', parsed.path)
            if match:
                job_id = match.group(1)
                return f"https://www.linkedin.com/jobs/view/{job_id}"
                
        elif "indeed.com" in parsed.netloc:
            # Preserve only the 'jk' parameter as that identifies the job ID uniquely
            query_params = urllib.parse.parse_qs(parsed.query)
            jk_val = query_params.get("jk")
            if jk_val:
                return f"https://www.indeed.com/viewjob?jk={jk_val[0]}"
                
        # Fallback: remove query parameters for other websites
        return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))

    def to_dict(self) -> Dict[str, Any]:
        """Convert job representation to a dictionary for routers."""
        bst = timezone(timedelta(hours=6))
        if self.posted_time.tzinfo is None:
            actual_post_bst = self.posted_time.replace(tzinfo=timezone.utc).astimezone(bst)
        else:
            actual_post_bst = self.posted_time.astimezone(bst)
        date_found_bst = datetime.now(timezone.utc).astimezone(bst)
        
        return {
            "Company": self.company,
            "Title": self.title,
            "Location": self.location,
            "URL": self.url,
            "Actual Post Date": actual_post_bst.strftime("%Y-%m-%d %H:%M:%S BST"),
            "Date Found": date_found_bst.strftime("%Y-%m-%d %H:%M:%S BST")
        }

    def __repr__(self) -> str:
        return f"<Job {self.company} - {self.title}>"


class BaseHandler:
    """Abstract base class for all job board handlers."""
    def __init__(
        self,
        company_name: str,
        token: str,
        keywords: List[str],
        lookback_hours: int = 24,
        only_remote_or_hybrid: bool = False,
        compound_rules: Optional[List[Dict[str, Any]]] = None
    ):
        self.company_name = company_name
        self.token = token
        self.keywords = keywords
        self.lookback_hours = lookback_hours
        self.only_remote_or_hybrid = only_remote_or_hybrid
        self.compound_rules = compound_rules or []

    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        """Fetch raw jobs from the target API. Must be implemented by subclasses."""
        raise NotImplementedError("fetch_raw_jobs must be implemented by subclasses.")

    def parse_job(self, raw_job: Dict[str, Any]) -> Optional[Job]:
        """Parse raw API dictionary into a standardized Job object. Must be implemented by subclasses."""
        raise NotImplementedError("parse_job must be implemented by subclasses.")

    def matches_phrase(self, pattern_text: str, target_text: str) -> bool:
        """Helper to match a phrase or word using whole-word boundary matching."""
        if not pattern_text or not target_text:
            return False
        escaped = re.escape(pattern_text)
        pattern = rf"(?:^|[^a-zA-Z0-9]){escaped}(?:$|[^a-zA-Z0-9])"
        return bool(re.search(pattern, target_text, re.IGNORECASE))

    def matches_keywords(self, title: str) -> bool:
        """
        Check if the job title matches any of the target keywords using case-insensitive whole-word matching.
        """
        if not title:
            return False
        
        for keyword in self.keywords:
            if self.matches_phrase(keyword, title):
                return True
        return False

    def matches_compound(self, job: Job) -> bool:
        """
        Check if the job matches any compound boolean rules (e.g. title_keywords AND context_keywords).
        """
        if not self.compound_rules:
            return False

        combined_context = f"{job.title} {job.description} {' '.join(job.tags)}".lower()

        for rule in self.compound_rules:
            title_kws = rule.get("title_keywords", [])
            context_kws = rule.get("context_keywords", [])

            # Check title criteria
            title_match = any(self.matches_phrase(kw, job.title) for kw in title_kws)
            if not title_match:
                continue

            # Check context criteria
            context_match = False
            if any(kw.lower() in combined_context for kw in context_kws):
                context_match = True
            elif any("visa" in kw.lower() for kw in context_kws) and job.has_visa_sponsorship:
                context_match = True
            elif any("relocat" in kw.lower() for kw in context_kws) and job.has_relocation:
                context_match = True

            if context_match:
                return True

        return False

    def matches_location(self, location: str, title: str, job: Optional[Job] = None) -> bool:
        """
        Check if the job matches location filters (Remote / Hybrid / EU / Germany / UAE) if enabled.
        Jobs that explicitly provide visa sponsorship or relocation are also permitted.
        """
        if not self.only_remote_or_hybrid:
            return True

        # If job verified to offer visa sponsorship or relocation assistance, pass location filter
        if job and (job.has_visa_sponsorship or job.has_relocation):
            return True

        loc_lower = (location or "").lower()
        title_lower = (title or "").lower()
        text = f"{loc_lower} {title_lower}"
        
        target_keywords = [
            "remote", "hybrid", "eu", "europe", "european union", "uae", "united arab emirates", "dubai", "abu dhabi",
            "germany", "deutschland", "berlin", "munich", "münchen", "hamburg", "frankfurt", "cologne", "köln", "stuttgart", "düsseldorf"
        ]
        return any(kw in text for kw in target_keywords)

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
                
                # Apply filters: title/compound match, posting date, and location
                has_keyword_match = self.matches_keywords(job.title) or self.matches_compound(job)
                if (has_keyword_match and 
                    self.is_within_lookback(job.posted_time) and 
                    self.matches_location(job.location, job.title, job)):
                    matching_jobs.append(job)
            except Exception as e:
                # Log parsing errors but don't fail the overall run
                print(f"[{self.company_name}] Error parsing job listing: {e}")
                
        return matching_jobs
