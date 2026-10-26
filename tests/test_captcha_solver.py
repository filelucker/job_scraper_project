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

if __name__ == "__main__":
    unittest.main()
