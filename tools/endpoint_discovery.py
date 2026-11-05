"""
Endpoint Discovery & Reverse-Engineering Tool.
Inspired by goodnight000/api-anything.

Intercepts background network traffic (XHR / Fetch / GraphQL) on dynamic career
sites using Playwright and generates clean, parameterizable JSON specs compatible
with api-anything and Python direct HTTP execution.
"""

import os
import re
import sys
import json
import time
import argparse
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

# Exclude third-party analytics and tracking domains
TRACKING_PATTERNS = [
    r"google-analytics\.com",
    r"googletagmanager\.com",
    r"doubleclick\.net",
    r"sentry\.io",
    r"datadoghq\.com",
    r"segment\.io",
    r"segment\.com",
    r"hotjar\.com",
    r"facebook\.net",
    r"clarity\.ms",
    r"mixpanel\.com",
    r"amplitude\.com",
    r"intercom\.io",
    r"fullstory\.com",
    r"heap\.io",
    r"logrocket\.io",
    r"newrelic\.com",
    r"scorecardresearch\.com",
    r"optimizely\.com",
]

STATIC_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico",
    ".css", ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".map"
)


class CapturedExchange:
    def __init__(self, method: str, url: str, headers: Dict[str, str], post_data: Optional[str] = None):
        self.method = method
        self.url = url
        self.headers = headers
        self.post_data = post_data
        self.status: Optional[int] = None
        self.response_headers: Dict[str, str] = {}
        self.response_body: Optional[str] = None
        self.response_json: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "url": self.url,
            "headers": self.headers,
            "post_data": self.post_data,
            "status": self.status,
            "response_json": self.response_json
        }


class EndpointDiscoverer:
    """Interprets and records network calls made by a web application."""

    def __init__(self, headless: bool = True, timeout_sec: int = 25):
        self.headless = headless
        self.timeout_sec = timeout_sec
        self.captured: List[CapturedExchange] = []

    def _is_noise(self, url: str) -> bool:
        parsed = urlparse(url)
        path_lower = parsed.path.lower()
        if any(path_lower.endswith(ext) for ext in STATIC_EXTENSIONS):
            return True
        for pattern in TRACKING_PATTERNS:
            if re.search(pattern, parsed.netloc, re.IGNORECASE):
                return True
        return False

    def capture(self, target_url: str, interactive: bool = False, wait_sec: int = 5) -> List[CapturedExchange]:
        """Loads target_url and intercepts network calls."""
        from playwright.sync_api import sync_playwright

        try:
            from playwright_stealth import Stealth
            stealth = Stealth()
        except Exception:
            stealth = None

        self.captured = []
        pending_requests: Dict[Any, CapturedExchange] = {}

        print(f"[EndpointDiscoverer] Navigating to: {target_url} (headless={self.headless})")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            if stealth:
                try:
                    stealth.apply_stealth_sync(page)
                except Exception:
                    pass

            def on_request(req):
                url = req.url
                if self._is_noise(url):
                    return
                # Only interest in fetch / xhr / document
                if req.resource_type in ("fetch", "xhr", "document"):
                    exchange = CapturedExchange(
                        method=req.method,
                        url=url,
                        headers=dict(req.headers),
                        post_data=req.post_data
                    )
                    pending_requests[req] = exchange

            def on_response(resp):
                req = resp.request
                if req in pending_requests:
                    exchange = pending_requests[req]
                    exchange.status = resp.status
                    exchange.response_headers = dict(resp.headers)
                    try:
                        ct = resp.headers.get("content-type", "")
                        if "application/json" in ct or "text/x-json" in ct:
                            exchange.response_json = resp.json()
                        elif "text/html" in ct and resp.status == 200:
                            # Check if HTML contains embedded Next.js or Nuxt data
                            text = resp.text()
                            if "__NEXT_DATA__" in text:
                                exchange.response_body = "__NEXT_DATA__ detected"
                    except Exception:
                        pass
                    if exchange.response_json is not None or exchange.response_body:
                        self.captured.append(exchange)

            page.on("request", on_request)
            page.on("response", on_response)

            try:
                page.goto(target_url, timeout=self.timeout_sec * 1000)
            except Exception as e:
                print(f"[EndpointDiscoverer] Page navigation notice: {e}")

            if interactive:
                print("\n[EndpointDiscoverer] Interactive mode: interact with the page in browser.")
                print("Press ENTER in this console when finished capturing...")
                try:
                    input()
                except (EOFError, KeyboardInterrupt):
                    pass
            else:
                print(f"[EndpointDiscoverer] Waiting {wait_sec}s for async API requests...")
                time.sleep(wait_sec)

            browser.close()

        print(f"[EndpointDiscoverer] Intercepted {len(self.captured)} candidate API request(s).")
        return self.captured

    def generate_spec(self, target_url: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        """Builds an api-anything compatible JSON specification from captured traffic."""
        parsed = urlparse(target_url)
        parts = parsed.netloc.replace("www.", "").split(".")
        site_name = parts[-2] if len(parts) >= 2 else parts[0]
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        operations = []
        for idx, ex in enumerate(self.captured):
            ex_parsed = urlparse(ex.url)
            op_name = f"op_{idx}_{ex_parsed.path.strip('/').replace('/', '_') or 'root'}"
            if len(op_name) > 40:
                op_name = op_name[:40]

            # Clean headers: remove ephemeral/cookie headers for template sharing
            clean_headers = {}
            for k, v in ex.headers.items():
                if k.lower() not in ("cookie", "content-length", "host", "connection"):
                    clean_headers[k.lower()] = v

            # Sample response keys
            picked_keys = []
            if isinstance(ex.response_json, dict):
                picked_keys = list(ex.response_json.keys())[:10]
            elif isinstance(ex.response_json, list) and ex.response_json:
                if isinstance(ex.response_json[0], dict):
                    picked_keys = list(ex.response_json[0].keys())[:10]

            op = {
                "name": op_name,
                "description": f"Captured {ex.method} request to {ex_parsed.path}",
                "request": {
                    "method": ex.method,
                    "url": ex.url,
                    "headers": clean_headers
                },
                "match": {
                    "method": ex.method,
                    "host": ex_parsed.netloc,
                    "path": ex_parsed.path
                },
                "response": {
                    "format": "json" if ex.response_json is not None else "html",
                    "sampleKeys": picked_keys
                },
                "minTier": 1
            }
            if ex.post_data:
                op["request"]["body"] = ex.post_data

            operations.append(op)

        spec = {
            "name": site_name,
            "displayName": site_name.capitalize(),
            "baseUrl": base_url,
            "description": f"Auto-discovered API specification for {parsed.netloc}",
            "operations": operations
        }

        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(spec, f, indent=2)
            print(f"[EndpointDiscoverer] Spec written to: {output_path}")

        return spec

    def test_tier1_replay(self, exchange: CapturedExchange) -> bool:
        """Tests whether a captured request can be replayed in Tier 1 (plain HTTP requests)."""
        import requests
        print(f"\n[EndpointDiscoverer - Tier 1 Test] Testing direct HTTP replay for: {exchange.url}")
        try:
            resp = requests.request(
                method=exchange.method,
                url=exchange.url,
                headers=exchange.headers,
                data=exchange.post_data,
                timeout=10
            )
            print(f"[EndpointDiscoverer - Tier 1 Test] Status: {resp.status_code}")
            if resp.status_code in (200, 201):
                print("  => SUCCESS: Can run as Tier 1 direct API! (No browser required)")
                return True
            else:
                print(f"  => Requires Tier 2 (Status {resp.status_code})")
                return False
        except Exception as e:
            print(f"  => Tier 1 test failed: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="Discover and reverse-engineer API endpoints for career portals.")
    parser.add_argument("--url", required=True, help="Target portal URL to inspect.")
    parser.add_argument("--output", default=None, help="Path to write JSON spec file (e.g. tools/specs/target.json)")
    parser.add_argument("--interactive", action="store_true", help="Launch interactive browser window.")
    parser.add_argument("--wait", type=int, default=5, help="Seconds to wait after loading.")
    parser.add_argument("--test-http", action="store_true", help="Test replayability via Python requests.")
    args = parser.parse_args()

    discoverer = EndpointDiscoverer(headless=not args.interactive)
    captured = discoverer.capture(args.url, interactive=args.interactive, wait_sec=args.wait)

    if not captured:
        print("[EndpointDiscoverer] No API calls intercepted.")
        return

    spec = discoverer.generate_spec(args.url, output_path=args.output)
    print(f"[EndpointDiscoverer] Generated spec with {len(spec.get('operations', []))} operations.")

    if args.test_http:
        for ex in captured[:3]:
            discoverer.test_tier1_replay(ex)


if __name__ == "__main__":
    main()
