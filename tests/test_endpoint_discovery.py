import unittest
from tools.endpoint_discovery import EndpointDiscoverer, CapturedExchange

class TestEndpointDiscovery(unittest.TestCase):
    def test_noise_filtering(self):
        discoverer = EndpointDiscoverer()

        # Static assets
        self.assertTrue(discoverer._is_noise("https://example.com/logo.png"))
        self.assertTrue(discoverer._is_noise("https://example.com/styles.css"))
        self.assertTrue(discoverer._is_noise("https://example.com/font.woff2"))

        # Analytics
        self.assertTrue(discoverer._is_noise("https://www.google-analytics.com/analytics.js"))
        self.assertTrue(discoverer._is_noise("https://o1234.ingest.sentry.io/api/5678/envelope/"))
        self.assertTrue(discoverer._is_noise("https://browser-http-intake.logs.datadoghq.com/v1/input"))

        # Real API endpoints should NOT be noise
        self.assertFalse(discoverer._is_noise("https://wellfound.com/jobs"))
        self.assertFalse(discoverer._is_noise("https://jobs.ashbyhq.com/api/non-user-graphql"))
        self.assertFalse(discoverer._is_noise("https://workday.wd5.myworkdayjobs.com/wday/cxs/ebay/apply/jobs"))

    def test_spec_generation(self):
        discoverer = EndpointDiscoverer()
        ex = CapturedExchange(
            method="POST",
            url="https://jobs.ashbyhq.com/api/non-user-graphql",
            headers={"content-type": "application/json", "user-agent": "test-agent", "cookie": "secret=123"},
            post_data='{"op": "ApiJobBoardWithTeams"}'
        )
        ex.status = 200
        ex.response_json = {"data": {"jobBoard": {"jobPostings": []}}}
        discoverer.captured = [ex]

        spec = discoverer.generate_spec("https://jobs.ashbyhq.com/openai")
        self.assertEqual(spec["name"], "ashbyhq")
        self.assertEqual(len(spec["operations"]), 1)
        op = spec["operations"][0]
        self.assertEqual(op["request"]["method"], "POST")
        self.assertNotIn("cookie", op["request"]["headers"])  # Cookie stripped
        self.assertIn("content-type", op["request"]["headers"])
        self.assertEqual(op["response"]["format"], "json")
        self.assertIn("data", op["response"]["sampleKeys"])

if __name__ == "__main__":
    unittest.main()

