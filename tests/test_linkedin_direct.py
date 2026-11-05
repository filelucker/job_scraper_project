import unittest
from unittest.mock import MagicMock, patch
from handlers.linkedin import LinkedInHandler

class TestLinkedInDirect(unittest.TestCase):
    def test_voyager_api_extraction(self):
        handler = LinkedInHandler(
            company_name="LinkedIn",
            token="*",
            keywords=["Flutter"],
            li_at="test_li_at_token",
            jsessionid='"ajax:98765"'
        )

        mock_voyager_json = {
            "elements": [
                {
                    "items": [
                        {
                            "itemUnion": {
                                "entityResult": {
                                    "title": {"text": "Senior Flutter Architect"},
                                    "primarySubtitle": {"text": "Acme Global"},
                                    "secondarySubtitle": {"text": "Remote / EMEA"},
                                    "navigationUrl": "https://www.linkedin.com/jobs/view/999888777"
                                }
                            }
                        }
                    ]
                }
            ]
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_voyager_json

        with patch("requests.get", return_value=mock_resp) as mock_get:
            raw_jobs = handler.fetch_raw_jobs()
            self.assertEqual(len(raw_jobs), 1)
            self.assertEqual(raw_jobs[0]["title"], "Senior Flutter Architect")
            self.assertEqual(raw_jobs[0]["companyName"], "Acme Global")
            self.assertEqual(raw_jobs[0]["link"], "https://www.linkedin.com/jobs/view/999888777")

            # Verify csrf-token was stripped of quotes
            called_headers = mock_get.call_args[1]["headers"]
            self.assertEqual(called_headers["csrf-token"], "ajax:98765")

    def test_guest_api_extraction(self):
        handler = LinkedInHandler(
            company_name="LinkedIn",
            token="*",
            keywords=["Android"],
            apify_api_token="",  # No Apify token
            li_at="",            # No session cookies
            jsessionid=""
        )

        mock_html = """
        <ul class="jobs-search__results-list">
          <li>
            <div class="base-card">
              <a class="base-card__full-link" href="https://www.linkedin.com/jobs/view/11223344?refId=123">
                <span class="sr-only">Senior Android Engineer</span>
              </a>
              <h3 class="base-search-card__title">Senior Android Engineer</h3>
              <h4 class="base-search-card__subtitle">
                <a class="hidden-nested-link" href="https://www.linkedin.com/company/cooltech">CoolTech</a>
              </h4>
              <div class="base-search-card__metadata">
                <span class="job-search-card__location">San Francisco, CA</span>
              </div>
            </div>
          </li>
        </ul>
        """

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = mock_html

        with patch("requests.get", return_value=mock_resp):
            raw_jobs = handler.fetch_raw_jobs()
            self.assertEqual(len(raw_jobs), 1)
            self.assertEqual(raw_jobs[0]["title"], "Senior Android Engineer")
            self.assertEqual(raw_jobs[0]["companyName"], "CoolTech")
            self.assertEqual(raw_jobs[0]["link"], "https://www.linkedin.com/jobs/view/11223344")
            self.assertEqual(raw_jobs[0]["location"], "San Francisco, CA")

            # Parse job
            job = handler.parse_job(raw_jobs[0])
            self.assertIsNotNone(job)
            self.assertEqual(job.title, "Senior Android Engineer")
            self.assertEqual(job.company, "CoolTech")

if __name__ == "__main__":
    unittest.main()

