import unittest
from services.url_resolver import UrlResolver
from services.form_agent import FormAgent
from services.profile_loader import get_candidate_profile

class TestAutomationServices(unittest.TestCase):

    def setUp(self):
        self.profile = get_candidate_profile().data
        self.form_agent = FormAgent()

    def test_direct_ats_detection(self):
        self.assertTrue(UrlResolver.is_direct_ats("https://boards.greenhouse.io/moniruz/jobs/123"))
        self.assertTrue(UrlResolver.is_direct_ats("https://jobs.lever.co/company/abc-123"))
        self.assertTrue(UrlResolver.is_direct_ats("https://jobs.ashbyhq.com/company/456"))
        self.assertFalse(UrlResolver.is_direct_ats("https://www.arbeitnow.com/jobs/dev-123"))

    def test_form_agent_answer_matching(self):
        controls = [
            {"kind": "text", "label": "First Name", "selector": "#fn"},
            {"kind": "text", "label": "Last Name", "selector": "#ln"},
            {"kind": "text", "label": "Email", "selector": "#em"},
            {"kind": "text", "label": "Contact Phone Number", "selector": "#ph"},
            {"kind": "select", "label": "Years of experience in Android / Kotlin", "selector": "#exp", "options": [{"value": "1-3", "text": "1-3 years"}, {"value": "4-6", "text": "4-6 years"}, {"value": "7+", "text": "7+ years"}]},
            {"kind": "select", "label": "Will you require visa sponsorship?", "selector": "#sponsor", "options": [{"value": "yes", "text": "Yes"}, {"value": "no", "text": "No"}]},
            {"kind": "checkbox", "label": "I agree to the privacy policy", "selector": "#consent"}
        ]
        answers = self.form_agent.answer_fields(controls, self.profile)
        self.assertEqual(answers["#fn"], "Md")
        self.assertEqual(answers["#ln"], "Moniruzzaman")
        self.assertEqual(answers["#em"], "contact@moniruz.dev")
        self.assertEqual(answers["#ph"], "+8801721915013")
        self.assertEqual(answers["#exp"], "7+")
        self.assertEqual(answers["#sponsor"], "yes")
        self.assertTrue(answers["#consent"])

    def test_headless_detection(self):
        import os
        from unittest.mock import patch
        from services.apply_browser import PlaywrightBrowserApplier

        # Case 1: In CI environment without DISPLAY, force headless
        with patch.dict(os.environ, {"CI": "true", "DISPLAY": "", "BROWSER_HEADLESS": "false"}):
            applier = PlaywrightBrowserApplier(headless=False)
            self.assertTrue(applier.headless)

        # Case 2: Explicit BROWSER_HEADLESS=true
        with patch.dict(os.environ, {"BROWSER_HEADLESS": "true"}):
            applier = PlaywrightBrowserApplier(headless=False)
            self.assertTrue(applier.headless)

if __name__ == "__main__":
    unittest.main()
