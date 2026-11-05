import json
import unittest
from unittest.mock import MagicMock, patch
from handlers.wellfound import WellfoundHandler

class TestWellfoundFallback(unittest.TestCase):
    def setUp(self):
        self.sample_apollo = {
            "JobListing:12345": {
                "id": "12345",
                "slug": "senior-flutter-developer",
                "title": "Senior Flutter Developer",
                "startup": {"__ref": "Startup:999"},
                "locationNames": ["Remote", "Europe"],
                "acceptedRemoteLocationNames": ["Worldwide"],
                "remote": True,
                "liveStartAt": 1720000000
            },
            "Startup:999": {
                "name": "SuperApp Inc",
                "slug": "superapp"
            }
        }

    def test_tier1_http_success(self):
        handler = WellfoundHandler("Wellfound", "*", ["Flutter"])

        # Mock requests.get returning valid __NEXT_DATA__ HTML
        payload_data = {
            "props": {
                "pageProps": {
                    "apolloState": {
                        "data": {
                            "JobListing:12345": {
                                "id": "12345",
                                "slug": "flutter-dev",
                                "title": "Flutter Developer",
                                "startup": {"__ref": "Startup:999"}
                            },
                            "Startup:999": {
                                "name": "FastCo"
                            }
                        }
                    }
                }
            }
        }
        html_payload = f'<html><head><script id="__NEXT_DATA__" type="application/json">{json.dumps(payload_data)}</script></head></html>'
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html_payload

        with patch("requests.get", return_value=mock_resp):
            apollo_data = handler._fetch_tier1_http("https://wellfound.com/jobs")
            self.assertIsNotNone(apollo_data)
            listings = handler._extract_from_apollo_data(apollo_data, set())
            self.assertEqual(len(listings), 1)
            self.assertEqual(listings[0]["title"], "Flutter Developer")
            self.assertEqual(listings[0]["startup_name"], "FastCo")

    def test_tier1_failure_escalates_to_tier2(self):
        handler = WellfoundHandler("Wellfound", "*", ["Flutter"])

        # Patch _fetch_tier1_http to simulate HTTP block (None)
        with patch.object(handler, "_fetch_tier1_http", return_value=None):
            # Patch sync_playwright to simulate successful Tier 2 extraction
            with patch("playwright.sync_api.sync_playwright") as mock_pw:
                mock_context = MagicMock()
                mock_page = MagicMock()
                mock_resp = MagicMock()
                mock_resp.status = 200
                mock_page.goto.return_value = mock_resp
                mock_page.evaluate.return_value = {
                    "props": {
                        "pageProps": {
                            "apolloState": {
                                "data": self.sample_apollo
                            }
                        }
                    }
                }
                mock_context.new_page.return_value = mock_page

                mock_browser = MagicMock()
                mock_browser.new_context.return_value = mock_context

                mock_p = MagicMock()
                mock_p.chromium.launch.return_value = mock_browser
                mock_pw.return_value.__enter__.return_value = mock_p

                listings = handler.fetch_raw_jobs()
                self.assertGreaterEqual(len(listings), 1)
                self.assertEqual(listings[0]["title"], "Senior Flutter Developer")
                self.assertEqual(listings[0]["startup_name"], "SuperApp Inc")

if __name__ == "__main__":
    unittest.main()
