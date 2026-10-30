import unittest
from services.captcha_solver import CaptchaSolver

class TestCaptchaSolver(unittest.TestCase):
    def setUp(self):
        self.solver = CaptchaSolver(gemini_api_key="test_gemini")

    def test_init(self):
        self.assertEqual(self.solver.gemini_api_key, "test_gemini")

    def test_no_captcha_present(self):
        class DummyPage:
            url = "https://example.com"
            frames = []
            def query_selector(self, selector):
                return None

        dummy_page = DummyPage()
        result = self.solver.solve_if_present(dummy_page)
        self.assertFalse(result)

    def test_has_turnstile_detection(self):
        class DummyElement:
            def is_visible(self):
                return True

        class DummyPageWithTurnstile:
            url = "https://example.com"
            frames = []
            def query_selector(self, selector):
                if "turnstile" in selector:
                    return DummyElement()
                return None

        dummy_page = DummyPageWithTurnstile()
        self.assertTrue(self.solver._has_turnstile(dummy_page))

    def test_extract_turnstile_sitekey(self):
        class DummyPage:
            def evaluate(self, script):
                return "0x4AAAAAAtestSiteKey"

        self.assertEqual(self.solver._extract_turnstile_sitekey(DummyPage()), "0x4AAAAAAtestSiteKey")

    def test_inject_turnstile_token(self):
        class DummyPage:
            executed = False
            def evaluate(self, script, arg):
                self.executed = True
                self.arg = arg

        page = DummyPage()
        self.solver._inject_turnstile_token(page, "sample_token_123")
        self.assertTrue(page.executed)
        self.assertEqual(page.arg, "sample_token_123")

if __name__ == "__main__":
    unittest.main()
