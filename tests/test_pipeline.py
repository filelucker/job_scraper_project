import unittest
from datetime import datetime, timezone, timedelta
from handlers import AshbyHandler, GreenhouseHandler, LeverHandler, Job, WorkdayHandler, WorkableHandler, SmartRecruitersHandler, AdzunaHandler, JoobleHandler, FlexjobsHandler
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

    def test_google_sheets_router_worldwide_column(self):
        from unittest.mock import MagicMock, patch
        from routers import GoogleSheetsRouter
        
        # Instantiate with valid looking mock JSON creds
        router = GoogleSheetsRouter('{"type": "service_account"}', "Test Sheet", "Jobs")
        
        mock_client = MagicMock()
        mock_spreadsheet = MagicMock()
        mock_worksheet = MagicMock()
        
        mock_client.open.return_value = mock_spreadsheet
        mock_spreadsheet.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_values.return_value = [] # brand new worksheet
        
        jobs_payload = [
            {"Company": "TestCo1", "Title": "Eng", "Location": "Worldwide Remote", "URL": "http://1", "Actual Post Date": "2026-07-12 21:33:01 BST", "Date Found": "2026-07-12 21:33:01 BST"},
            {"Company": "TestCo2", "Title": "Eng", "Location": "New York, NY", "URL": "http://2", "Actual Post Date": "2026-07-12", "Date Found": "2026-07-12"}
        ]
        
        with patch.object(router, '_get_client', return_value=mock_client):
            success = router.append_jobs(jobs_payload)
            self.assertTrue(success)
            
            # Check headers written
            expected_headers = ["Company", "Title", "Location", "URL", "Actual Post Date", "Date Found", "this job accepts candidate worldwide or not"]
            mock_worksheet.append_row.assert_called_once_with(expected_headers)
            
            # Check values appended
            args, kwargs = mock_worksheet.append_rows.call_args
            appended_rows = args[0]
            self.assertEqual(len(appended_rows), 2)
            # Check date conversion to AM/PM format
            self.assertEqual(appended_rows[0][4], "2026-07-12 09:33:01 PM BST")
            self.assertEqual(appended_rows[0][5], "2026-07-12 09:33:01 PM BST")
            # Check graceful fallback on invalid/non-standard format
            self.assertEqual(appended_rows[1][4], "2026-07-12")
            self.assertEqual(appended_rows[1][5], "2026-07-12")
            
            self.assertEqual(appended_rows[0][6], "Yes") # Worldwide Remote
            self.assertEqual(appended_rows[1][6], "No")  # New York, NY

    def test_telegram_router_send_document(self):
        from unittest.mock import patch, MagicMock
        from routers import TelegramRouter
        
        router = TelegramRouter("mock_token", "mock_chat_id")
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch("requests.post", return_value=mock_response) as mock_post:
            # We can write a dummy file to test
            dummy_file = "dummy_run.log"
            with open(dummy_file, "w") as f:
                f.write("test log")
                
            try:
                success = router.send_document(dummy_file, caption="Test log file")
                self.assertTrue(success)
                
                # Verify requests.post was called with the correct URL
                expected_url = "https://api.telegram.org/botmock_token/sendDocument"
                mock_post.assert_called_once()
                args, kwargs = mock_post.call_args
                self.assertEqual(args[0], expected_url)
                self.assertEqual(kwargs["data"]["chat_id"], "mock_chat_id")
                self.assertEqual(kwargs["data"]["caption"], "Test log file")
                self.assertIn("document", kwargs["files"])
            finally:
                import os
                if os.path.exists(dummy_file):
                    os.remove(dummy_file)

    def test_telegram_router_format_run_summary(self):
        from routers import TelegramRouter
        router = TelegramRouter("mock_token", "mock_chat_id")
        
        # Test summary format without failures
        summary = router.format_run_summary(
            duration_seconds=75.5,
            total_configured=10,
            scanned_count=8,
            skipped_count=2,
            failed_boards=[],
            total_found=5,
            total_new=2
        )
        
        self.assertIn("Job Scraper Run Summary", summary)
        self.assertIn("1m 15s", summary)
        self.assertIn("*Total Boards*: 10", summary)
        self.assertIn("*Scanned*: 8", summary)
        self.assertIn("*Skipped*: 2", summary)
        self.assertIn("*Jobs Matched*: 5", summary)
        self.assertIn("*New Jobs Added*: 2", summary)
        self.assertNotIn("Failed Boards:", summary)

        # Test summary format with failures (no truncation)
        summary_with_fail = router.format_run_summary(
            duration_seconds=30.0,
            total_configured=5,
            scanned_count=3,
            skipped_count=1,
            failed_boards=[("ErrorCo", "HTTP Connection Timeout to endpoint 500")],
            total_found=0,
            total_new=0
        )
        self.assertIn("Failed Boards:", summary_with_fail)
        self.assertIn("ErrorCo", summary_with_fail)
        self.assertIn("HTTP Connection Timeout to endpoint 500", summary_with_fail)

        # Test summary format with failures (with truncation)
        summary_with_trunc = router.format_run_summary(
            duration_seconds=30.0,
            total_configured=5,
            scanned_count=3,
            skipped_count=1,
            failed_boards=[("ErrorCo", "A very long error message that exceeds sixty characters to test the truncation logic in our router")],
            total_found=0,
            total_new=0
        )
        self.assertIn("A very long error message that exceeds", summary_with_trunc)
        self.assertTrue(summary_with_trunc.endswith("..."))

    def test_adzuna_handler_parsing(self):
        handler = AdzunaHandler("Adzuna", "*", ["Flutter"], app_id="test_id", app_key="test_key")
        raw_job = {
            "title": "<strong>Flutter</strong> Developer",
            "company": {"display_name": "Test Company"},
            "redirect_url": "https://example.com/job",
            "location": {"display_name": "Remote, USA"},
            "created": "2026-07-14T08:00:00Z"
        }
        job = handler.parse_job(raw_job)
        self.assertIsNotNone(job)
        self.assertEqual(job.company, "Test Company")
        self.assertEqual(job.title, "Flutter Developer")
        self.assertEqual(job.location, "Remote, USA")
        self.assertEqual(job.url, "https://example.com/job")

    def test_jooble_handler_parsing(self):
        handler = JoobleHandler("Jooble", "*", ["Flutter"], api_key="test_key")
        raw_job = {
            "title": "<b>Flutter</b> Engineer",
            "company": "Test Company",
            "link": "https://example.com/job",
            "location": "Remote",
            "updated": "2026-07-14T08:00:00.0000000+03:00"
        }
        job = handler.parse_job(raw_job)
        self.assertIsNotNone(job)
        self.assertEqual(job.company, "Test Company")
        self.assertEqual(job.title, "Flutter Engineer")
        self.assertEqual(job.location, "Remote")
        self.assertEqual(job.url, "https://example.com/job")

    def test_flexjobs_handler_parsing(self):
        handler = FlexjobsHandler("FlexJobs", "*", ["Flutter", "Flutter Developer"])
        
        # Test keyword optimization (minimal keywords)
        min_kws = handler._get_minimal_keywords()
        self.assertEqual(min_kws, ["Flutter"]) # "Flutter Developer" is redundant
        
        # Test date parsing
        now = datetime.now(timezone.utc)
        self.assertAlmostEqual(handler._parse_date("Today").day, now.day)
        self.assertAlmostEqual(handler._parse_date("Yesterday").day, (now - timedelta(days=1)).day)
        self.assertAlmostEqual(handler._parse_date("2 days ago").day, (now - timedelta(days=2)).day)
        
        # Absolute date format parsing
        parsed_abs = handler._parse_date("July 15, 2026")
        self.assertEqual(parsed_abs.year, 2026)
        self.assertEqual(parsed_abs.month, 7)
        self.assertEqual(parsed_abs.day, 15)
        
        # Test job parsing
        raw_job = {
            "title": "Senior Flutter Developer — TechCorp",
            "url": "https://www.flexjobs.com/publicjobs/techcorp-1",
            "posted_str": "July 15, 2026",
            "location_and_type": "Full-Time, Remote (USA)"
        }
        job = handler.parse_job(raw_job)
        self.assertIsNotNone(job)
        self.assertEqual(job.company, "TechCorp")
        self.assertEqual(job.title, "Senior Flutter Developer")
        self.assertEqual(job.location, "Full-Time, Remote (USA)")
        self.assertEqual(job.url, "https://www.flexjobs.com/publicjobs/techcorp-1")
        self.assertEqual(job.posted_time.day, 15)

if __name__ == "__main__":
    unittest.main()
