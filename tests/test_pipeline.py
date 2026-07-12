import unittest
from datetime import datetime, timezone, timedelta
from handlers import AshbyHandler, GreenhouseHandler, LeverHandler, Job, WorkdayHandler, WorkableHandler, SmartRecruitersHandler
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

    def test_location_filtering(self):
        # 1. Location filtering disabled
        handler_no_filter = DummyHandler("TestCo", "token", [], only_remote_or_hybrid=False)
        self.assertTrue(handler_no_filter.matches_location("New York, NY", "Developer"))
        self.assertTrue(handler_no_filter.matches_location("Remote", "Developer"))

        # 2. Location filtering enabled
        handler_filtered = DummyHandler("TestCo", "token", [], only_remote_or_hybrid=True)
        # Matches 'remote' in location
        self.assertTrue(handler_filtered.matches_location("Remote, USA", "Developer"))
        self.assertTrue(handler_filtered.matches_location("remote", "Developer"))
        # Matches 'hybrid' in location
        self.assertTrue(handler_filtered.matches_location("Hybrid - San Francisco", "Developer"))
        # Matches 'remote' or 'hybrid' in title
        self.assertTrue(handler_filtered.matches_location("New York, NY", "Remote Developer"))
        self.assertTrue(handler_filtered.matches_location("London, UK", "Hybrid Software Engineer"))
        # Does NOT match
        self.assertFalse(handler_filtered.matches_location("New York, NY", "Developer"))
        self.assertFalse(handler_filtered.matches_location("", "Developer"))

    def test_job_to_dict_formatting(self):
        posted_time = datetime(2026, 7, 11, 12, 0, 0, tzinfo=timezone.utc)
        job = Job("TestCo", "Developer", "Remote", "https://example.com", posted_time)
        job_dict = job.to_dict()
        
        self.assertEqual(job_dict["Company"], "TestCo")
        self.assertEqual(job_dict["Title"], "Developer")
        self.assertEqual(job_dict["Location"], "Remote")
        self.assertEqual(job_dict["URL"], "https://example.com")
        self.assertEqual(job_dict["Actual Post Date"], "2026-07-11 18:00:00 BST")
        self.assertTrue(job_dict["Date Found"].endswith("BST"))

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

    def test_workable_handler_parsing(self):
        handler = WorkableHandler("LoopCV", "loopcv", [])
        raw_job = {
            "title": "Flutter Developer",
            "shortlink": "https://apply.workable.com/loopcv/j/123",
            "location": {"city": "Athens", "countryName": "Greece"},
            "published": "2026-07-11T12:00:00.000Z"
        }
        job = handler.parse_job(raw_job)
        self.assertIsNotNone(job)
        self.assertEqual(job.company, "LoopCV")
        self.assertEqual(job.title, "Flutter Developer")
        self.assertEqual(job.location, "Athens, Greece")
        self.assertEqual(job.url, "https://apply.workable.com/loopcv/j/123")

    def test_smartrecruiters_handler_parsing(self):
        handler = SmartRecruitersHandler("Wayfair", "Wayfair", [])
        raw_job = {
            "name": "Backend Developer",
            "id": "106566412",
            "location": {"fullLocation": "Boston, MA, United States"},
            "releasedDate": "2026-07-11T14:30:00.000Z"
        }
        job = handler.parse_job(raw_job)
        self.assertIsNotNone(job)
        self.assertEqual(job.company, "Wayfair")
        self.assertEqual(job.title, "Backend Developer")
        self.assertEqual(job.location, "Boston, MA, United States")
        self.assertEqual(job.url, "https://jobs.smartrecruiters.com/Wayfair/106566412")

    def test_workday_handler_parsing(self):
        handler = WorkdayHandler("eBay", "ebay.wd5.myworkdayjobs.com/wday/cxs/ebay/apply", [])
        
        # Test 1: Posted Today
        raw_job_today = {
            "title": "Android Engineer",
            "externalPath": "/apply/job/123",
            "locationsText": "Remote, US",
            "postedOn": "Posted Today"
        }
        job = handler.parse_job(raw_job_today)
        self.assertIsNotNone(job)
        self.assertEqual(job.title, "Android Engineer")
        self.assertEqual(job.location, "Remote, US")
        self.assertEqual(job.url, "https://ebay.wd5.myworkdayjobs.com/apply/job/123")
        # Ensure timestamp is close to now
        self.assertTrue((datetime.now(timezone.utc) - job.posted_time).total_seconds() < 60)
        
        # Test 2: Posted Yesterday
        raw_job_yesterday = {
            "title": "Backend Engineer",
            "externalPath": "/apply/job/456",
            "postedOn": "Posted Yesterday"
        }
        job_yesterday = handler.parse_job(raw_job_yesterday)
        self.assertIsNotNone(job_yesterday)
        delta = datetime.now(timezone.utc) - job_yesterday.posted_time
        self.assertTrue(23 <= delta.total_seconds() / 3600 <= 25)

        # Test 3: Posted 5 Days Ago
        raw_job_5_days = {
            "title": "Flutter Specialist",
            "externalPath": "/apply/job/789",
            "postedOn": "Posted 5 Days Ago"
        }
        job_5_days = handler.parse_job(raw_job_5_days)
        self.assertIsNotNone(job_5_days)
        delta_5 = datetime.now(timezone.utc) - job_5_days.posted_time
        self.assertTrue(4.9 <= delta_5.total_seconds() / (3600 * 24) <= 5.1)

if __name__ == "__main__":
    unittest.main()
