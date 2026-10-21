import re
from typing import Optional, Dict, Any, List

# Common ATS domain signatures
ATS_DOMAINS = {
    "greenhouse.io": "Greenhouse",
    "boards.greenhouse.io": "Greenhouse",
    "job-boards.greenhouse.io": "Greenhouse",
    "lever.co": "Lever",
    "jobs.lever.co": "Lever",
    "ashbyhq.com": "Ashby",
    "myworkdayjobs.com": "Workday",
    "smartrecruiters.com": "SmartRecruiters",
    "workable.com": "Workable",
    "bamboohr.com": "BambooHR",
    "recruitee.com": "Recruitee",
    "rippling.com": "Rippling",
    "linkedin.com": "LinkedIn",
    "indeed.com": "Indeed"
}

# Generic/spam emails to deprioritize
EXCLUDED_PREFIXES = {
    "privacy", "abuse", "noreply", "no-reply", "donotreply",
    "legal", "security", "terms", "compliance", "copyright"
}

PREFERRED_PREFIXES = {
    "careers", "jobs", "recruiting", "recruitment", "talent",
    "hiring", "apply", "join", "team", "founder", "founders", "ceo", "cto"
}

EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b')

class JobEmailExtractor:
    """Extracts application emails and detects ATS portals from job data."""

    @staticmethod
    def detect_ats_portal(url: str) -> Optional[str]:
        """Check if URL points to a known ATS portal."""
        if not url:
            return None
        url_lower = url.lower()
        for domain, name in ATS_DOMAINS.items():
            if domain in url_lower:
                return name
        return None

    @classmethod
    def extract_emails_from_text(cls, text: str) -> List[str]:
        """Find valid email addresses within arbitrary text."""
        if not text:
            return []
        
        matches = EMAIL_REGEX.findall(text)
        cleaned = []
        for m in matches:
            email = m.strip().lower()
            prefix = email.split('@')[0]
            if any(prefix.startswith(ex) for ex in EXCLUDED_PREFIXES):
                continue
            # Filter out common file extension false positives (e.g. name@2x.png)
            if email.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp')):
                continue
            if email not in cleaned:
                cleaned.append(email)
        return cleaned

    @classmethod
    def select_best_email(cls, emails: List[str]) -> Optional[str]:
        """Pick the most relevant application email from candidates."""
        if not emails:
            return None
        
        # 1. Prefer hiring/career-specific emails
        for email in emails:
            prefix = email.split('@')[0]
            if any(prefix.startswith(pref) for pref in PREFERRED_PREFIXES):
                return email

        # 2. Return first non-excluded email
        return emails[0]

    @classmethod
    def analyze_job(cls, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a scraped job dictionary for application methods.
        Returns application metadata including email and portal details.
        """
        url = job.get("URL", "")
        description = job.get("description", "") or ""
        
        # Check for ATS portal
        portal_name = cls.detect_ats_portal(url)
        
        # Search for email in description, title, or tags
        search_corpus = f"{job.get('Title', '')} {description} {' '.join(job.get('tags', []))}"
        emails = cls.extract_emails_from_text(search_corpus)
        best_email = cls.select_best_email(emails)
        
        # Determine application method
        if best_email:
            apply_method = "EMAIL"
            status = "Ready to Apply (Email)"
        elif portal_name:
            apply_method = "WEB_PORTAL"
            status = f"Apply via {portal_name}"
        else:
            apply_method = "WEB_PORTAL"
            status = "Apply via URL"

        return {
            "has_email": bool(best_email),
            "email": best_email,
            "all_emails": emails,
            "is_ats_portal": bool(portal_name),
            "portal_name": portal_name,
            "apply_method": apply_method,
            "initial_status": status
        }
