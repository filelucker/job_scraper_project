import re
import json
import requests
from typing import Optional, Dict, Any
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup

KNOWN_ATS_DOMAINS = [
    "greenhouse.io",
    "jobs.lever.co",
    "jobs.ashbyhq.com",
    "ashbyhq.com",
    "apply.workable.com",
    "workable.com",
    "jobs.smartrecruiters.com",
    "smartrecruiters.com",
    "myworkdayjobs.com",
    "jobs.personio.com",
    "jobs.personio.de",
    "breezy.hr",
    "bamboohr.com",
    "teamtailor.com",
    "recruitee.com"
]

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

class UrlResolver:
    """
    Resolves job aggregator URLs (e.g. Arbeitnow, Jooble, Indeed, LinkedIn)
    into direct, canonical employer application and ATS URLs.
    """

    @staticmethod
    def is_direct_ats(url: str) -> bool:
        if not url:
            return False
        url_lower = url.lower()
        return any(domain in url_lower for domain in KNOWN_ATS_DOMAINS)

    @classmethod
    def resolve(cls, url: str, timeout: int = 15) -> str:
        """
        Takes a job URL and attempts to extract the underlying direct ATS or career URL.
        Falls back to the original URL if no external redirect is detected.
        """
        if not url or cls.is_direct_ats(url):
            return url

        resolved_url = url
        try:
            # Check aggregator-specific extraction first
            if "arbeitnow" in url.lower():
                extracted = cls._extract_from_arbeitnow(url, timeout)
                if extracted:
                    return extracted

            if "jooble.org" in url.lower():
                extracted = cls._extract_from_jooble(url, timeout)
                if extracted:
                    return extracted

            # General redirect resolver
            resolved_url = cls._follow_redirects(url, timeout)
            if cls.is_direct_ats(resolved_url):
                return resolved_url

            # If the resolved landing page is an aggregator or landing page, inspect HTML for ATS links
            extracted = cls._extract_ats_from_page(resolved_url, timeout)
            if extracted:
                return extracted

        except Exception as e:
            # Fall back to original url on any resolution exception
            print(f"[UrlResolver] Notice: redirect resolution for {url[:50]}... returned: {e}")

        return resolved_url

    @classmethod
    def _follow_redirects(cls, url: str, timeout: int = 15) -> str:
        """Follow standard HTTP redirects with a browser User-Agent."""
        try:
            session = requests.Session()
            session.headers.update(DEFAULT_HEADERS)
            resp = session.get(url, allow_redirects=True, timeout=timeout, stream=True)
            final_url = resp.url
            resp.close()
            return final_url
        except Exception:
            return url

    @classmethod
    def _extract_from_arbeitnow(cls, url: str, timeout: int = 15) -> Optional[str]:
        """Inspects Arbeitnow job postings for direct external employer/ATS application links."""
        try:
            session = requests.Session()
            session.headers.update(DEFAULT_HEADERS)
            resp = session.get(url, timeout=timeout)
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, "html.parser")

            # 1. First priority: Check if URL or links end with /apply or are explicit apply buttons
            apply_targets = []
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                text = (a.get_text() or "").strip().lower()

                # Check for direct ATS links in href immediately
                if any(domain in href.lower() for domain in KNOWN_ATS_DOMAINS):
                    return href

                # If link is specifically an 'Apply' or 'Apply now' CTA
                if text in ["apply now", "apply", "apply for this job", "apply online"] or href.endswith("/apply"):
                    target = urljoin(url, href)
                    apply_targets.append(target)

            for target in apply_targets:
                followed = cls._follow_redirects(target, timeout=timeout)
                followed_domain = (urlparse(followed).netloc or "").lower()
                if "arbeitnow" not in followed_domain:
                    return followed

            # 2. Check schema.org JobPosting in JSON-LD
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string or "")
                    if isinstance(data, dict) and data.get("@type") == "JobPosting":
                        direct_apply = data.get("directApply") or data.get("url")
                        if direct_apply and direct_apply.startswith("http"):
                            direct_domain = (urlparse(direct_apply).netloc or "").lower()
                            if "arbeitnow" not in direct_domain:
                                return direct_apply
                except Exception:
                    pass

        except Exception as e:
            print(f"[UrlResolver] Arbeitnow parse error: {e}")
        return None

    @classmethod
    def _extract_from_jooble(cls, url: str, timeout: int = 8) -> Optional[str]:
        """Extracts outbound destination from Jooble descriptor page if available."""
        try:
            session = requests.Session()
            session.headers.update(DEFAULT_HEADERS)
            resp = session.get(url, timeout=timeout)
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if any(domain in href.lower() for domain in KNOWN_ATS_DOMAINS):
                    return href
        except Exception:
            pass
        return None

    @classmethod
    def _extract_ats_from_page(cls, url: str, timeout: int = 8) -> Optional[str]:
        """Scans page HTML for outbound ATS links if available."""
        try:
            session = requests.Session()
            session.headers.update(DEFAULT_HEADERS)
            resp = session.get(url, timeout=timeout)
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                for domain in KNOWN_ATS_DOMAINS:
                    if domain in href.lower():
                        return href
        except Exception:
            pass
        return None
