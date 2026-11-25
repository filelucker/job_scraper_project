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
    Resolves job aggregator URLs (e.g. Arbeitnow, Jooble, Indeed, LinkedIn, Y Combinator)
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
        if not url:
            return url

        # Direct ATS URLs (Greenhouse, Lever, Ashby, Workable, etc.) should not be unwrapped as aggregators
        if cls.is_direct_ats(url):
            return url

        parsed = urlparse(url)
        netloc = (parsed.netloc or "").lower()

        resolved_url = url
        try:
            # Check aggregator-specific extraction first by domain, not query parameters
            if "arbeitnow" in netloc:
                extracted = cls._extract_from_arbeitnow(url, timeout)
                if extracted:
                    return extracted

            if "jooble.org" in netloc:
                extracted = cls._extract_from_jooble(url, timeout)
                if extracted:
                    return extracted

            if "ycombinator.com" in netloc:
                extracted = cls._extract_from_ycombinator(url, timeout)
                if extracted:
                    return extracted

            if "indeed" in netloc:
                extracted = cls._extract_from_indeed(url, timeout)
                if extracted:
                    return extracted

            if "linkedin.com" in netloc:
                extracted = cls._extract_from_linkedin(url, timeout)
                if extracted:
                    return extracted

            if "glassdoor" in netloc:
                extracted = cls._extract_from_glassdoor(url, timeout)
                if extracted:
                    return extracted

            if "builtin.com" in netloc:
                extracted = cls._extract_from_builtin(url, timeout)
                if extracted:
                    return extracted

            if "jobicy.com" in netloc:
                extracted = cls._extract_from_jobicy(url, timeout)
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
    def _extract_from_ycombinator(cls, url: str, timeout: int = 15) -> Optional[str]:
        """Resolves YC job links to the company's canonical ATS posting."""
        try:
            m = re.search(r'ycombinator\.com/companies/([^/]+)/jobs/([^/]+)', url)
            if not m:
                return None
            company_slug = m.group(1).lower().strip()

            session = requests.Session()
            session.headers.update(DEFAULT_HEADERS)
            resp = session.get(url, timeout=timeout)
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, "html.parser")
            job_title = ""
            company_website = ""

            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(s.string or "")
                    if isinstance(data, dict) and data.get("@type") == "JobPosting":
                        job_title = (data.get("title") or "").strip().lower()
                        org = data.get("hiringOrganization") or {}
                        company_website = org.get("sameAs") or ""
                        break
                except Exception:
                    pass

            title_words = [w for w in re.split(r'\W+', job_title) if len(w) > 3]

            # 1. Direct ATS endpoints for the company slug
            candidate_ats_roots = [
                (f"https://jobs.ashbyhq.com/{company_slug}", "ashby"),
                (f"https://job-boards.greenhouse.io/{company_slug}", "greenhouse"),
                (f"https://jobs.lever.co/{company_slug}", "lever"),
                (f"https://apply.workable.com/{company_slug}", "workable")
            ]

            for ats_url, ats_name in candidate_ats_roots:
                try:
                    ats_resp = session.get(ats_url, timeout=5)
                    if ats_resp.status_code == 200:
                        ats_soup = BeautifulSoup(ats_resp.text, "html.parser")
                        for a in ats_soup.find_all("a", href=True):
                            href = a["href"]
                            link_text = (a.get_text() or "").strip().lower()
                            if title_words and any(w in link_text for w in title_words):
                                return urljoin(ats_url, href)
                except Exception:
                    pass

            # 2. Inspect company website /careers or /jobs
            if company_website:
                for path in ["/careers", "/careers/", "/jobs", "/jobs/"]:
                    careers_url = urljoin(company_website, path)
                    try:
                        c_resp = session.get(careers_url, timeout=5)
                        if c_resp.status_code == 200:
                            c_soup = BeautifulSoup(c_resp.text, "html.parser")
                            for a in c_soup.find_all("a", href=True):
                                href = a["href"]
                                if any(d in href.lower() for d in KNOWN_ATS_DOMAINS):
                                    if title_words and any(w in (a.get_text() or "").lower() for w in title_words):
                                        return href
                            # Return any direct ATS link on careers page if found
                            for a in c_soup.find_all("a", href=True):
                                href = a["href"]
                                if any(d in href.lower() for d in KNOWN_ATS_DOMAINS):
                                    return href
                    except Exception:
                        pass
        except Exception as e:
            print(f"[UrlResolver] YC extraction notice: {e}")
        return None

    @classmethod
    def _extract_from_indeed(cls, url: str, timeout: int = 12) -> Optional[str]:
        """Resolves Indeed job URLs to direct canonical ATS or employer application links."""
        try:
            session = requests.Session()
            session.headers.update(DEFAULT_HEADERS)
            
            # 1. Check for 'jk' job key to follow standard Indeed applystart redirect
            m = re.search(r'[?&]jk=([a-zA-Z0-9]+)', url)
            jk = m.group(1) if m else None
            if jk:
                applystart_url = f"https://www.indeed.com/applystart?jk={jk}"
                try:
                    followed = cls._follow_redirects(applystart_url, timeout=timeout)
                    if followed and "indeed.com" not in (urlparse(followed).netloc or "").lower():
                        return followed
                except Exception:
                    pass

            # 2. Fetch Indeed job page and inspect DOM / JSON-LD / descriptions
            resp = session.get(url, timeout=timeout)
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, "html.parser")

            # Check JSON-LD schema
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string or "")
                    if isinstance(data, dict) and data.get("@type") == "JobPosting":
                        apply_url = data.get("directApply") or data.get("url")
                        if apply_url and cls.is_direct_ats(str(apply_url)):
                            return str(apply_url)
                except Exception:
                    pass

            # Check outbound apply links
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                for domain in KNOWN_ATS_DOMAINS:
                    if domain in href.lower():
                        return href
                if "applystart" in href:
                    full_target = urljoin("https://www.indeed.com", href)
                    followed = cls._follow_redirects(full_target, timeout=timeout)
                    if followed and "indeed.com" not in (urlparse(followed).netloc or "").lower():
                        return followed

            # Check job description text for direct ATS links (e.g. Greenhouse/Lever/Workday links pasted in text)
            desc_elem = soup.find(id=re.compile(r'jobDescriptionText|job_summary', re.I))
            if desc_elem:
                desc_text = desc_elem.get_text()
                for domain in KNOWN_ATS_DOMAINS:
                    url_match = re.search(rf'https?://[^\s<>"]*{re.escape(domain)}[^\s<>"]*', desc_text)
                    if url_match:
                        return url_match.group(0).rstrip('.,;()[]')

        except Exception as e:
            print(f"[UrlResolver] Indeed extraction notice: {e}")
        return None

    @classmethod
    def _extract_from_linkedin(cls, url: str, timeout: int = 12) -> Optional[str]:
        """Resolves public LinkedIn job postings to direct employer or ATS URLs."""
        try:
            session = requests.Session()
            session.headers.update(DEFAULT_HEADERS)

            # Extract job ID
            m = re.search(r'/(?:jobs/view|currentJobId=)/?(\d+)', url)
            job_id = m.group(1) if m else None

            target_fetch_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}" if job_id else url
            resp = session.get(target_fetch_url, timeout=timeout)
            if resp.status_code != 200:
                resp = session.get(url, timeout=timeout)
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, "html.parser")

            # 1. Search for external apply links with encoded or redirected target URL
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if "externalApply" in href or "apply-link-offsite" in str(a.get("data-tracking-control-name", "")):
                    url_param = re.search(r'[?&]url=([^&]+)', href)
                    if url_param:
                        from urllib.parse import unquote
                        decoded = unquote(url_param.group(1))
                        if decoded and "linkedin.com" not in (urlparse(decoded).netloc or "").lower():
                            return decoded
                    followed = cls._follow_redirects(urljoin("https://www.linkedin.com", href), timeout=timeout)
                    if followed and "linkedin.com" not in (urlparse(followed).netloc or "").lower():
                        return followed

                for domain in KNOWN_ATS_DOMAINS:
                    if domain in href.lower():
                        return href

            # 2. Check JSON-LD
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string or "")
                    if isinstance(data, dict) and data.get("@type") == "JobPosting":
                        apply_url = data.get("url") or data.get("sameAs")
                        if apply_url and cls.is_direct_ats(str(apply_url)):
                            return str(apply_url)
                except Exception:
                    pass

            # 3. Check job description for ATS link
            desc = soup.find(class_=re.compile(r'description|show-more-less-html', re.I))
            if desc:
                desc_text = desc.get_text()
                for domain in KNOWN_ATS_DOMAINS:
                    url_match = re.search(rf'https?://[^\s<>"]*{re.escape(domain)}[^\s<>"]*', desc_text)
                    if url_match:
                        return url_match.group(0).rstrip('.,;()[]')

        except Exception as e:
            print(f"[UrlResolver] LinkedIn extraction notice: {e}")
        return None

    @classmethod
    def _extract_from_glassdoor(cls, url: str, timeout: int = 12) -> Optional[str]:
        """Resolves Glassdoor job URLs to direct canonical ATS application links."""
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

            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string or "")
                    if isinstance(data, dict) and data.get("@type") == "JobPosting":
                        apply_url = data.get("url")
                        if apply_url and cls.is_direct_ats(str(apply_url)):
                            return str(apply_url)
                except Exception:
                    pass
        except Exception as e:
            print(f"[UrlResolver] Glassdoor extraction notice: {e}")
        return None

    @classmethod
    def _extract_from_builtin(cls, url: str, timeout: int = 8) -> Optional[str]:
        """Extracts direct ATS or external employer URL from BuiltIn job pages."""
        return cls._extract_external_apply_link(url, aggregator_domain="builtin.com", timeout=timeout)

    @classmethod
    def _extract_from_jobicy(cls, url: str, timeout: int = 8) -> Optional[str]:
        """Extracts direct ATS or external employer URL from Jobicy job pages."""
        return cls._extract_external_apply_link(url, aggregator_domain="jobicy.com", timeout=timeout)

    @classmethod
    def _extract_external_apply_link(cls, url: str, aggregator_domain: str, timeout: int = 8) -> Optional[str]:
        """Shared helper to unwrap aggregator pages (BuiltIn, Jobicy) to direct ATS or employer URLs."""
        try:
            session = requests.Session()
            session.headers.update(DEFAULT_HEADERS)
            resp = session.get(url, timeout=timeout)
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if cls.is_direct_ats(href):
                    return href

            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string or "")
                    if isinstance(data, dict) and data.get("@type") == "JobPosting":
                        direct = data.get("directApply") or data.get("url")
                        if isinstance(direct, str) and direct.startswith("http") and aggregator_domain not in direct.lower():
                            return direct
                except Exception:
                    pass
        except Exception as e:
            print(f"[UrlResolver] {aggregator_domain} extraction notice: {e}")
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
