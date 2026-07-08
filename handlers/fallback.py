import urllib.parse
import xml.etree.ElementTree as ET
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from handlers.base import BaseHandler, Job

class FallbackHandler(BaseHandler):
    """
    A robust, extensible fallback handler for enterprise and custom platforms.
    By default, includes a lightweight, zero-dependency XML/RSS feed parser
    and structured placeholders for third-party job boards.
    """

    def fetch_raw_jobs(self) -> List[Dict[str, Any]]:
        # In a real-world setting, if a company uses RSS or a custom API,
        # we configure their RSS feed URL. Here we define standard fallback endpoints.
        # Check if the company has a custom config or URL.
        # For demonstration, we construct a mock RSS/JSON response or query standard placeholders.
        
        # Example RSS URL template
        rss_url = f"https://www.google.com/search?q={urllib.parse.quote(self.company_name)}+careers"
        
        # We simulate checking a custom endpoint. Let's return a list with instructions 
        # on how the user can implement custom selectors or fetch standard feeds.
        print(f"[Fallback - {self.company_name}] Running generic fallback handler. Target URL: {rss_url}")
        
        # We can implement a simple RSS checker for actual endpoints here:
        # e.g., if token ends with '.xml' or contains a full URL, we fetch and parse it as XML/RSS.
        if self.token.startswith("http://") or self.token.startswith("https://") or self.token.endswith(".xml"):
            return self._fetch_rss_jobs(self.token)
            
        # Return an empty list for raw jobs since fallback is a stub until customized
        return []

    def _fetch_rss_jobs(self, feed_url: str) -> List[Dict[str, Any]]:
        """Fetch and extract jobs from a generic XML/RSS feed."""
        try:
            response = requests.get(feed_url, timeout=15)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.content)
            items = []
            
            # Find all <item> tags (standard RSS)
            for item in root.findall(".//item"):
                title_el = item.find("title")
                link_el = item.find("link")
                pub_date_el = item.find("pubDate")
                desc_el = item.find("description")
                
                title = title_el.text if title_el is not None else ""
                link = link_el.text if link_el is not None else ""
                pub_date = pub_date_el.text if pub_date_el is not None else ""
                desc = desc_el.text if desc_el is not None else ""
                
                items.append({
                    "title": title,
                    "link": link,
                    "pubDate": pub_date,
                    "description": desc,
                    "source": "rss"
                })
            return items
        except Exception as e:
            print(f"[Fallback RSS - {self.company_name}] Error parsing XML/RSS: {e}")
            return []

    def parse_job(self, raw_job: Dict[str, Any]) -> Optional[Job]:
        # Handle parsed RSS elements
        if raw_job.get("source") == "rss":
            title = raw_job.get("title")
            url = raw_job.get("link")
            pub_date_str = raw_job.get("pubDate")
            
            posted_time = datetime.now(timezone.utc)
            if pub_date_str:
                # Format example: "Wed, 08 Jul 2026 12:00:00 GMT" or "2026-07-08T12:00:00Z"
                try:
                    # Common RSS date formatting parse
                    for fmt in (
                        "%a, %d %b %Y %H:%M:%S %Z",
                        "%a, %d %b %Y %H:%M:%S %z",
                        "%Y-%m-%dT%H:%M:%S%z",
                        "%Y-%m-%d %H:%M:%S"
                    ):
                        try:
                            # Strip out timezone names that python's %z does not understand if they are GMT/UTC
                            clean_date = pub_date_str.strip()
                            if clean_date.endswith("GMT"):
                                clean_date = clean_date[:-3] + "+0000"
                            posted_time = datetime.strptime(clean_date, fmt).replace(tzinfo=timezone.utc)
                            break
                        except ValueError:
                            continue
                except Exception:
                    posted_time = datetime.now(timezone.utc)

            return Job(
                company=self.company_name,
                title=title,
                location="Remote (Fallback)",
                url=url,
                posted_time=posted_time
            )
            
        # Standard fallback placeholder
        return None
