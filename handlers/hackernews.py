import re
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from handlers.base import BaseHandler, Job

class HackerNewsHandler(BaseHandler):
    """
    Handler for Hacker News 'Ask HN: Who is Hiring?' monthly direct hiring threads
    powered by the public Algolia Hacker News Search API.
    Direct hiring opportunities directly from founders, CTOs, and tech leads.
    Public API: No API key required.
    """
    def __init__(
        self,
        company_name: str,
        token: str,
        keywords: List[str],
        lookback_hours: int = 6,
        only_remote_or_hybrid: bool = False,
        compound_rules: Optional[List[Dict[str, Any]]] = None
    ):
        super().__init__(
            company_name=company_name,
            token=token,
            keywords=keywords,
            lookback_hours=lookback_hours,
            only_remote_or_hybrid=only_remote_or_hybrid,
            compound_rules=compound_rules
        )
        self.hn_search_url = "https://hn.algolia.com/api/v1/search_by_date"

    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        """Fetch matching hiring comments from the active 'Who is hiring' thread."""
        try:
            # 1. Identify latest 'Ask HN: Who is hiring?' thread
            resp = requests.get(
                self.hn_search_url,
                params={
                    "tags": "story,author_whoishiring",
                    "query": '"Who is hiring"',
                    "hitsPerPage": 1
                },
                headers={"User-Agent": "JobScraperBot/1.0"},
                timeout=12
            )
            resp.raise_for_status()
            stories = resp.json().get("hits", [])
            if not stories:
                return []

            active_story = stories[0]
            story_id = active_story.get("objectID")
            if not story_id:
                return []

            # 2. Query comments matching tech keywords in the thread
            search_terms = ["Mobile", "Android", "Flutter", "iOS", "Kotlin", "Dart", "AI App"]
            raw_jobs = []
            seen_ids = set()

            for term in search_terms:
                try:
                    c_resp = requests.get(
                        "https://hn.algolia.com/api/v1/search",
                        params={
                            "tags": f"comment,story_{story_id}",
                            "query": term,
                            "hitsPerPage": 25
                        },
                        headers={"User-Agent": "JobScraperBot/1.0"},
                        timeout=10
                    )
                    if c_resp.status_code != 200:
                        continue
                    comments = c_resp.json().get("hits", [])
                    for c in comments:
                        cid = c.get("objectID")
                        if cid and cid not in seen_ids:
                            seen_ids.add(cid)
                            raw_jobs.append(c)
                except Exception as term_err:
                    print(f"[HackerNews] Error searching term '{term}': {term_err}")

            return raw_jobs
        except Exception as e:
            print(f"[HackerNews] Error fetching hiring thread: {e}")
            return []

    def parse_job(self, raw_job: Dict[str, Any]) -> Optional[Job]:
        comment_id = raw_job.get("objectID")
        comment_html = raw_job.get("comment_text") or ""
        if not comment_id or not comment_html:
            return None

        import html
        decoded_html = html.unescape(comment_html)

        # Clean HTML to plain text
        clean_text = re.sub(r'<[^>]+>', ' ', decoded_html).strip()
        first_line = clean_text.split('\n')[0].strip()

        # Parse standard HN pipe format: "Company | Title / Role | Location | Remote/Onsite"
        parts = [p.strip() for p in first_line.split('|')]
        company = parts[0] if parts else "Startup"
        title = "Mobile / Software Engineer"
        location = "Remote / Worldwide"

        if len(parts) >= 3:
            p1, p2 = parts[1], parts[2]
            title_keywords = ["engineer", "developer", "lead", "architect", "manager", "designer", "scientist", "specialist", "intern", "tech"]
            p1_is_title = any(k in p1.lower() for k in title_keywords)
            p2_is_title = any(k in p2.lower() for k in title_keywords)
            if p2_is_title and not p1_is_title:
                title = p2
                location = p1
            else:
                title = p1
                location = p2
        elif len(parts) == 2:
            title = parts[1]
            location = "Remote / Worldwide"
        elif len(parts) == 1 and parts[0]:
            company = parts[0][:30]
            title = parts[0]

        # Check for direct external apply/career URL in comment
        hn_url = f"https://news.ycombinator.com/item?id={comment_id}"
        ext_url = None
        urls_found = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', decoded_html)
        for u in urls_found:
            clean_u = u.strip('.,;()[]{}')
            if "ycombinator.com" not in clean_u and "news.ycombinator" not in clean_u:
                ext_url = clean_u
                break
        url = ext_url or hn_url

        # Parse publication date
        date_str = raw_job.get("created_at")
        posted_time = datetime.now(timezone.utc)
        if date_str:
            try:
                posted_time = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                if posted_time.tzinfo is None:
                    posted_time = posted_time.replace(tzinfo=timezone.utc)
            except Exception:
                pass

        desc_lower = clean_text.lower()
        has_relocation = "relocation" in desc_lower
        has_visa = "visa" in desc_lower or "sponsorship" in desc_lower

        tags = ["Hacker News", "Direct Founder / Team Hiring"]
        if "remote" in desc_lower:
            tags.append("Remote")

        return Job(
            company=company,
            title=title,
            location=location,
            url=url,
            posted_time=posted_time,
            description=clean_text[:1000],
            tags=tags,
            has_visa_sponsorship=has_visa,
            has_relocation=has_relocation
        )
