import unittest
from datetime import datetime, timezone, timedelta
from handlers import AshbyHandler, GreenhouseHandler, LeverHandler, Job
from handlers.base import BaseHandler

class DummyHandler(BaseHandler):
    def fetch_raw_jobs(self):
        return []
    def parse_job(self, raw_job):
        return None

class TestPipeline(unittest.TestCase):
    
    def test_keyword_matching(self):
        handler = DummyHandler("TestCo", "token", ["Flutter", "AI/ML", "Reactjs", "Backend"])
        
        # Exact Match
        self.assertTrue(handler.matches_keywords("Flutter Developer"))
        # Case Insensitive Match
        self.assertTrue(handler.matches_keywords("reactjs developer"))
        # Special Characters Whole Word Match
        self.assertTrue(handler.matches_keywords("Engineer - AI/ML"))
        
        # Substring/Boundary checks (should NOT match)
        self.assertFalse(handler.matches_keywords("Fluttering around")) # "Flutter" in "Fluttering"
        self.assertFalse(handler.matches_keywords("Reactjsguy")) # "Reactjs" in "Reactjsguy"
        
        # Empty string
        self.assertFalse(handler.matches_keywords(""))
        self.assertFalse(handler.matches_keywords(None))

    def test_lookback_verification(self):
        handler = DummyHandler("TestCo", "token", [], lookback_hours=24)
        
        # Within lookback (UTC)
        now_utc = datetime.now(timezone.utc)
        self.assertTrue(handler.is_within_lookback(now_utc - timedelta(hours=5)))
        self.assertTrue(handler.is_within_lookback(now_utc - timedelta(hours=23)))
        
        # Outside lookback
        self.assertFalse(handler.is_within_lookback(now_utc - timedelta(hours=25)))
        self.assertFalse(handler.is_within_lookback(now_utc + timedelta(hours=2))) # future date
        
        # Naive datetime assume UTC
        naive_time = (datetime.now(timezone.utc) - timedelta(hours=2)).replace(tzinfo=None)
        self.assertTrue(handler.is_within_lookback(naive_time))

    def test_ashby_handler_parsing(self):
        handler = AshbyHandler("Zapier", "zapier", ["AI/ML"])
        
        raw_job = {
            "title": "Staff AI/ML Engineer",
            "jobUrl": "https://jobs.ashbyhq.com/zapier/123",
            "location": "Remote",
            "publishedAt": "2026-07-11T12:00:00.000+00:00"
        }
        
        job = handler.parse_job(raw_job)
        self.assertIsNotNone(job)
        self.assertEqual(job.company, "Zapier")
        self.assertEqual(job.title, "Staff AI/ML Engineer")
        self.assertEqual(job.location, "Remote")
        self.assertEqual(job.url, "https://jobs.ashbyhq.com/zapier/123")
        self.assertEqual(job.posted_time.hour, 12)
        
        # Test invalid fields
        self.assertIsNone(handler.parse_job({"title": "No URL"}))

    def test_greenhouse_handler_parsing(self):
        handler = GreenhouseHandler("Hubspot", "hubspot", [])
        
        raw_job = {
            "title": "Backend Engineer",
            "absolute_url": "https://boards.greenhouse.io/hubspot/jobs/456",
            "location": {"name": "Boston, MA"},
            "updated_at": "2026-07-11T14:30:00Z"
        }
        
        job = handler.parse_job(raw_job)
        self.assertIsNotNone(job)
        self.assertEqual(job.company, "Hubspot")
        self.assertEqual(job.title, "Backend Engineer")
        self.assertEqual(job.location, "Boston, MA")
        self.assertEqual(job.url, "https://boards.greenhouse.io/hubspot/jobs/456")

    def test_lever_handler_parsing(self):
        handler = LeverHandler("Lever", "lever", [])
        
        raw_job = {
            "title": "Flutter Engineer",
            "hostedUrl": "https://jobs.lever.co/lever/789",
            "categories": {"location": "San Francisco, CA"},
            "createdAt": 1783857600000 # Epoch milliseconds corresponding to 2026-07-11 UTC approx
        }
        
        job = handler.parse_job(raw_job)
        self.assertIsNotNone(job)
        self.assertEqual(job.company, "Lever")
        self.assertEqual(job.title, "Flutter Engineer")
        self.assertEqual(job.location, "San Francisco, CA")
        self.assertEqual(job.url, "https://jobs.lever.co/lever/789")

if __name__ == "__main__":
    unittest.main()
