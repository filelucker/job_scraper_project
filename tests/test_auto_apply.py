import os
import unittest
from handlers.email_extractor import JobEmailExtractor
from ai.tailor import ResumeTailor
from services.compiler import LatexCompiler
from services.profile_loader import get_candidate_profile
from services.apply_greenhouse import GreenhouseApplier
from services.apply_lever import LeverApplier
from services.apply_dispatcher import AutoApplyDispatcher
from routers.email_router import EmailRouter

class TestAutoApplyPipeline(unittest.TestCase):

    def setUp(self):
        import shutil
        self.compiler = LatexCompiler()
        os.makedirs("output_resumes", exist_ok=True)
        self.dummy_pdf = os.path.join("output_resumes", "test_sample_resume.pdf")
        if not os.path.exists(self.dummy_pdf):
            if os.path.exists("master_resume.pdf"):
                shutil.copy2("master_resume.pdf", self.dummy_pdf)
            elif self.compiler.tectonic_bin:
                self.compiler.compile_pdf(self.compiler.render_latex(), self.dummy_pdf)
            else:
                with open(self.dummy_pdf, "wb") as f:
                    f.write(b"%PDF-1.4\n%EOF\n")

    def test_1_candidate_profile(self):
        profile = get_candidate_profile()
        self.assertEqual(profile.get("first_name"), "Md")
        self.assertEqual(profile.get("last_name"), "Moniruzzaman")
        self.assertIn("github.com", profile.get("urls", {}).get("github", ""))

    def test_2_greenhouse_applier_dry_run(self):
        applier = GreenhouseApplier(dry_run=True)
        # Test URL extraction
        url = "https://job-boards.greenhouse.io/monzo/jobs/6635595"
        meta = applier.extract_board_and_job_id(url)
        self.assertIsNotNone(meta)
        self.assertEqual(meta["job_id"], "6635595")

        # Dry run application
        res = applier.apply(
            job_url=url,
            pdf_path=self.dummy_pdf,
            board_token="monzo"
        )
        self.assertTrue(res["success"])
        self.assertTrue(res["dry_run"])
        self.assertEqual(res["board"], "monzo")

    def test_3_lever_applier_dry_run(self):
        applier = LeverApplier(dry_run=True)
        url = "https://jobs.lever.co/examplecorp/12345678-abcd-ef01-2345-6789abcdef01"
        meta = applier.extract_company_and_job_id(url)
        self.assertIsNotNone(meta)
        self.assertEqual(meta["company"], "examplecorp")

        res = applier.apply(
            job_url=url,
            pdf_path=self.dummy_pdf,
            comments="Interested in the Senior Mobile position."
        )
        self.assertTrue(res["success"])
        self.assertTrue(res["dry_run"])

    def test_4_dispatcher_routing_and_dry_run(self):
        dispatcher = AutoApplyDispatcher(mode="dry_run")

        gh_job = {
            "Title": "Backend Engineer",
            "Company": "Monzo",
            "URL": "https://job-boards.greenhouse.io/monzo/jobs/6635595"
        }
        self.assertEqual(dispatcher.detect_channel(gh_job), "GREENHOUSE")

        lever_job = {
            "Title": "Mobile Engineer",
            "Company": "Spotify",
            "URL": "https://jobs.lever.co/spotify/abc-123"
        }
        self.assertEqual(dispatcher.detect_channel(lever_job), "LEVER")

        email_job = {
            "Title": "Founding Mobile Engineer",
            "Company": "SuperKalam",
            "URL": "https://ycombinator.com/superkalam",
            "Contact Email": "join@superkalam.com"
        }
        self.assertEqual(dispatcher.detect_channel(email_job), "EMAIL")

        # Test full end-to-end process_job dry run
        gh_result = dispatcher.process_job(gh_job)
        self.assertTrue(gh_result["success"])
        self.assertEqual(gh_result["channel"], "GREENHOUSE")
        self.assertIn("Greenhouse", gh_result["status"])

    def test_5_tailor_and_compile(self):
        sample_job = {
            "Title": "Staff Mobile Engineer (Flutter)",
            "Company": "HealthTech Global",
            "description": "We are seeking a Flutter and Dart expert to lead our offline-first medical apps."
        }
        tailor = ResumeTailor()
        tailored = tailor.tailor(sample_job)

        self.assertIn("Flutter", tailored["summary"])
        self.assertIn("Staff Mobile Engineer", tailored["email_subject"])
        self.assertIn("HealthTech Global", tailored["email_body_text"])

        rendered_latex = self.compiler.render_latex(
            summary=tailored["summary"],
            competencies=tailored["competencies"],
            skills=tailored["skills"]
        )
        if self.compiler.tectonic_bin:
            test_pdf = os.path.join("output_resumes", "test_tailored_resume.pdf")
            ok = self.compiler.compile_pdf(rendered_latex, test_pdf)
            self.assertTrue(ok)
            self.assertTrue(os.path.exists(test_pdf))
            self.assertTrue(os.path.getsize(test_pdf) > 1000)
        else:
            self.assertIn("Flutter", rendered_latex)

    def test_6_browser_portal_auto_apply_status_and_sheets_timestamp(self):
        from unittest.mock import MagicMock, patch
        from routers import GoogleSheetsRouter

        dispatcher = AutoApplyDispatcher(mode="dry_run")
        web_job = {
            "Title": "Senior Android Engineer",
            "Company": "Instacart",
            "URL": "https://www.ycombinator.com/companies/instacart/jobs/BWkbgeYsk-senior-android-engineer",
            "Location": "Remote"
        }
        self.assertEqual(dispatcher.detect_channel(web_job), "BROWSER")

        # Mock browser applier result
        mock_browser_res = {
            "success": True,
            "channel": "BROWSER",
            "status": "Applied (Web Portal)",
            "filled_fields_count": 5,
            "resume_attached": True
        }
        with patch.object(dispatcher.browser_applier, "apply", return_value=mock_browser_res):
            res = dispatcher.process_job(web_job)
            self.assertEqual(res["status"], "Drafted (Web Form Filled)")
            self.assertTrue(res["success"])

        # Test sheets router records timestamp for applied/drafted jobs
        router = GoogleSheetsRouter('{"type": "service_account"}', "Test Sheet", "Jobs")
        mock_client = MagicMock()
        mock_spreadsheet = MagicMock()
        mock_worksheet = MagicMock()
        mock_client.open.return_value = mock_spreadsheet
        mock_spreadsheet.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_values.return_value = [["Header1"]]

        test_jobs = [{
            "Company": "Instacart",
            "Title": "Senior Android Engineer",
            "Location": "Remote",
            "URL": "https://example.com/job1",
            "Application Status": "Applied (Web Portal)",
            "Actual Post Date": "2026-10-28 10:00:00 BST",
            "Date Found": "2026-10-28 10:00:00 BST"
        }]

        with patch.object(router, '_get_client', return_value=mock_client):
            router.append_jobs(test_jobs)
            args, _ = mock_worksheet.append_rows.call_args
            row = args[0][0]
            # Column 9 is Application Status, Column 10 is Applied At timestamp
            self.assertEqual(row[8], "Applied (Web Portal)")
            self.assertTrue(len(row[9]) > 0)
            self.assertIn("BST", row[9])

    def test_7_auto_apply_escalation_and_radio_answering(self):
        from unittest.mock import MagicMock, patch
        from services.form_agent import FormAgent

        # 1. Test FormAgent radio and required checkbox answers
        agent = FormAgent()
        candidate = {
            "first_name": "Md",
            "last_name": "Moniruzzaman",
            "work_authorization": {"requires_sponsorship": True, "authorized_in_us": False}
        }
        controls = [
            {"kind": "radio", "label": "Do you now or in the future require visa sponsorship?", "value": "Yes", "selector": "#sponsor_yes", "required": True},
            {"kind": "radio", "label": "Do you now or in the future require visa sponsorship?", "value": "No", "selector": "#sponsor_no", "required": True},
            {"kind": "checkbox", "label": "I agree to Candidate Privacy Policy and Terms", "selector": "#privacy_check", "required": True}
        ]
        answers = agent.answer_fields(controls, candidate)
        self.assertTrue(answers.get("#sponsor_yes"))
        self.assertFalse(answers.get("#sponsor_no"))
        self.assertTrue(answers.get("#privacy_check"))

        # 2. Test AutoApplyDispatcher in mode="auto" produces "Applied (Web Portal)"
        dispatcher = AutoApplyDispatcher(mode="auto")
        lever_job = {
            "Title": "Senior Android Engineer",
            "Company": "TestCo",
            "URL": "https://jobs.lever.co/testco/12345678-abcd-1234-abcd-1234567890ab",
            "Location": "Remote"
        }
        # Simulate Lever API failure escalating to successful browser applier
        with patch.object(dispatcher.lever_applier, "apply", return_value={"success": False, "error": "403 Cloudflare"}), \
             patch.object(dispatcher.browser_applier, "apply", return_value={"success": True, "submitted": True, "filled_fields_count": 5}):
            res = dispatcher.process_job(lever_job)
            self.assertEqual(res["status"], "Applied (Web Portal)")
            self.assertTrue(res["success"])

        # 3. Test Greenhouse API failure escalating to browser applier in mode="auto"
        gh_job = {
            "Title": "Android Engineer",
            "Company": "Reddit",
            "URL": "https://job-boards.greenhouse.io/reddit/jobs/8127002",
            "Location": "Remote"
        }
        with patch.object(dispatcher.greenhouse_applier, "apply", return_value={"success": False, "error": "400 Bad Request"}), \
             patch.object(dispatcher.browser_applier, "apply", return_value={"success": True, "submitted": True, "filled_fields_count": 6}):
            gh_res = dispatcher.process_job(gh_job)
            self.assertEqual(gh_res["status"], "Applied (Web Portal)")
            self.assertTrue(gh_res["success"])


    def test_8_aggregator_bypass_and_lever_preservation(self):
        from services.url_resolver import UrlResolver

        # 1. Test direct Lever URL with Arbeitnow UTM preserves the application link
        lever_url = "https://jobs.lever.co/veepee/5ccd15e3-2b03-47dd-abc9-19fd321a2960/apply?utm_source=arbeitnow.fr"
        resolved = UrlResolver.resolve(lever_url)
        self.assertEqual(resolved, lever_url)

        # 2. Test AutoApplyDispatcher handles Indeed/LinkedIn aggregator URLs
        dispatcher = AutoApplyDispatcher(mode="dry_run")
        indeed_job = {
            "Title": "Mobile App Developer",
            "Company": "Dev Idea Studio",
            "URL": "https://www.indeed.com/viewjob?jk=62ecff1bbdc4c42c"
        }
        self.assertEqual(dispatcher.detect_channel(indeed_job), "MANUAL_URL")
        res = dispatcher.process_job(indeed_job)
        self.assertEqual(res["channel"], "MANUAL_URL")
        self.assertEqual(res["status"], "Apply via URL")
        self.assertFalse(res["success"])

        # In auto mode, portal dispatch is completed with Applied status
        dispatcher_auto = AutoApplyDispatcher(mode="auto")
        res_auto = dispatcher_auto.process_job(indeed_job)
        self.assertEqual(res_auto["channel"], "MANUAL_URL")
        self.assertEqual(res_auto["status"], "Applied (Portal Dispatched)")
        self.assertTrue(res_auto["success"])

        # 3. Test get_unapplied_jobs skips finalized/apply-via-url rows and enforces max_jobs
        from routers import GoogleSheetsRouter
        from unittest.mock import MagicMock, patch

        router = GoogleSheetsRouter('{"type": "service_account"}', "Test Sheet", "Jobs")
        mock_client = MagicMock()
        mock_spreadsheet = MagicMock()
        mock_worksheet = MagicMock()
        mock_client.open.return_value = mock_spreadsheet
        mock_spreadsheet.worksheet.return_value = mock_worksheet
        mock_worksheet.get_all_records.return_value = [
            {"Company": "C1", "Title": "T1", "URL": "http://1", "Application Status": "Apply via URL", "Applied At": ""},
            {"Company": "C2", "Title": "T2", "URL": "http://2", "Application Status": "Applied (Web Portal)", "Applied At": "2026-11-01"},
            {"Company": "C3", "Title": "T3", "URL": "http://3", "Application Status": "Pending", "Applied At": ""},
            {"Company": "C4", "Title": "T4", "URL": "http://4", "Application Status": "Drafted", "Applied At": ""},
            {"Company": "C5", "Title": "T5", "URL": "http://5", "Application Status": "Pending", "Applied At": ""}
        ]

        with patch.object(router, '_get_client', return_value=mock_client):
            unapplied = router.get_unapplied_jobs(max_jobs=2)
            self.assertEqual(len(unapplied), 2)
            self.assertEqual(unapplied[0]["Company"], "C3")
            self.assertEqual(unapplied[1]["Company"], "C4")

if __name__ == "__main__":
    unittest.main()
