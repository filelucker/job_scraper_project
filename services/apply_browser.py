import os
import time
import random
from typing import Dict, Any, Optional
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

try:
    from playwright_stealth import stealth_sync
    STEALTH_AVAILABLE = True
except ImportError:
    STEALTH_AVAILABLE = False

from services.profile_loader import get_candidate_profile
from services.url_resolver import UrlResolver
from services.form_agent import FormAgent
from services.captcha_solver import CaptchaSolver

class PlaywrightBrowserApplier:
    """
    Automates job application form filling and submission using Playwright with:
    1. Stealth anti-bot evasion & Cloudflare Turnstile detection/handling
    2. Automated CAPTCHA solving (reCAPTCHA v2/v3, hCaptcha, Turnstile)
    3. URL canonicalization resolving aggregators (Arbeitnow, Jooble, etc.)
    4. AI-powered dynamic form inspection, field filling, and auto-submission
    """

    def __init__(self, dry_run: bool = True, headless: bool = True):
        self.dry_run = dry_run
        self.headless = headless
        self.profile = get_candidate_profile()
        self.form_agent = FormAgent()
        self.captcha_solver = CaptchaSolver()

    def _inject_stealth_scripts(self, page):
        """Injects anti-detection scripts to mask automation flags."""
        if STEALTH_AVAILABLE:
            try:
                stealth_sync(page)
            except Exception as e:
                print(f"[BrowserApplier] Note: stealth_sync init: {e}")

        # Additional stealth overrides to defeat Cloudflare Turnstile & bot detection
        stealth_js = """
        () => {
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.navigator.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Intel Inc.';
                if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                return getParameter.apply(this, arguments);
            };
        }
        """
        try:
            page.add_init_script(stealth_js)
        except Exception:
            pass

    def _handle_cloudflare_turnstile(self, page, max_wait_sec: int = 12):
        """
        Detects Cloudflare Turnstile bot verification challenges and attempts
        to solve/click the checkbox with human-like movement.
        """
        turnstile_detected = False
        try:
            # Check for Cloudflare Turnstile iframe or container
            cf_selectors = [
                'iframe[src*="cloudflare"]',
                'iframe[src*="challenges"]',
                'iframe[title*="Cloudflare"]',
                'iframe[title*="Widget containing a Cloudflare"]',
                '#challenge-stage',
                '.cf-turnstile'
            ]
            for sel in cf_selectors:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    turnstile_detected = True
                    break

            if turnstile_detected:
                print("[BrowserApplier] Cloudflare Turnstile challenge detected. Attempting human-like resolution...")
                # Search across all frames for the checkbox
                for frame in page.frames:
                    try:
                        checkbox = frame.query_selector('input[type="checkbox"], #challenge-stage, .ctp-checkbox-label')
                        if checkbox and checkbox.is_visible():
                            box = checkbox.bounding_box()
                            if box:
                                # Move mouse naturally to the checkbox center with a slight random offset
                                target_x = box["x"] + box["width"] / 2 + random.uniform(-4, 4)
                                target_y = box["y"] + box["height"] / 2 + random.uniform(-4, 4)
                                page.mouse.move(target_x, target_y, steps=random.randint(10, 25))
                                time.sleep(random.uniform(0.2, 0.5))
                                page.mouse.click(target_x, target_y)
                                print("[BrowserApplier] Clicked Cloudflare Turnstile verification checkbox.")
                                break
                    except Exception:
                        pass

                # Wait for verification to resolve and redirect
                page.wait_for_load_state("networkidle", timeout=max_wait_sec * 1000)
                time.sleep(2)
        except Exception as e:
            # Non-blocking if no challenge is present
            pass

    def apply(
        self,
        job_url: str,
        pdf_path: str,
        mode: str = "review",  # "review", "auto", "dry_run"
        screenshot_dir: str = "output_resumes/screenshots"
    ) -> Dict[str, Any]:
        """
        1. Resolves canonical ATS/career URL if aggregator.
        2. Opens browser with anti-detection stealth.
        3. Handles Cloudflare Turnstile if present.
        4. Dynamically inspects form and answers fields using AI + candidate profile.
        5. In 'auto' mode submits; in 'review'/'dry_run' captures preview screenshot.
        """
        if not os.path.exists(pdf_path):
            return {
                "success": False,
                "error": f"Resume PDF not found: {pdf_path}"
            }

        os.makedirs(screenshot_dir, exist_ok=True)
        timestamp = int(time.time())
        screenshot_file = os.path.join(screenshot_dir, f"app_preview_{timestamp}.png")
        candidate = self.profile.data

        # Step 3: Resolve direct canonical URL (unwraps Arbeitnow, Jooble, redirects)
        resolved_url = UrlResolver.resolve(job_url)
        if resolved_url != job_url:
            print(f"[BrowserApplier] Resolved aggregator link: {job_url} -> {resolved_url}")
        target_url = resolved_url

        try:
            with sync_playwright() as p:
                # Launch Chromium with anti-automation flags
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-infobars",
                        "--window-size=1280,800"
                    ]
                )
                context = browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    locale="en-US"
                )
                page = context.new_page()
                page.set_default_timeout(30000)

                # Step 2: Inject Stealth Scripts
                self._inject_stealth_scripts(page)

                print(f"[BrowserApplier] Navigating to target: {target_url}")
                page.goto(target_url, wait_until="domcontentloaded")
                time.sleep(random.uniform(1.5, 3.0))

                # Step 2: Handle Bot Detection & CAPTCHAs (Turnstile, reCAPTCHA, hCaptcha)
                self._handle_cloudflare_turnstile(page)
                self.captcha_solver.solve_if_present(page)

                # Look for an initial 'Apply' / 'Apply Now' trigger button if on a job detail page
                apply_triggers = [
                    'a:has-text("Apply Now")',
                    'button:has-text("Apply Now")',
                    'a:has-text("Apply for this job")',
                    'button:has-text("Apply for this job")',
                    'a:has-text("Apply for this position")',
                    'button:has-text("Apply for this position")',
                    'a:has-text("Apply")',
                    'button:has-text("Apply")'
                ]
                for btn_sel in apply_triggers:
                    try:
                        btn = page.query_selector(btn_sel)
                        if btn and btn.is_visible():
                            # Don't click navigation menus or unrelated buttons
                            btn_text = (btn.inner_text() or "").strip()
                            if len(btn_text) < 30:
                                btn.click()
                                time.sleep(random.uniform(1.5, 2.5))
                                # Re-check for CAPTCHA if clicking Apply loaded a challenge modal
                                self.captcha_solver.solve_if_present(page)
                                break
                    except Exception:
                        pass

                # Step 4: Autonomous Form Inspection & AI Answering
                controls = self.form_agent.inspect_form(page)
                print(f"[BrowserApplier] Found {len(controls)} interactive form control(s) on the page.")

                answers = self.form_agent.answer_fields(controls, candidate)

                # Ensure any CAPTCHA challenge on the form is solved before submission
                self.captcha_solver.solve_if_present(page)

                # Determine if auto submission should occur
                is_simulation = (mode in ("review", "dry_run") or self.dry_run)
                auto_submit = (mode == "auto" and not self.dry_run)

                fill_res = self.form_agent.fill_and_submit(
                    page=page,
                    controls=controls,
                    answers=answers,
                    pdf_path=pdf_path,
                    auto_submit=auto_submit
                )

                time.sleep(1)
                page.screenshot(path=screenshot_file, full_page=True)

                filled_count = fill_res.get("filled_fields_count", 0)
                resume_attached = fill_res.get("resume_attached", False)
                submitted = fill_res.get("submitted", False)

                if is_simulation:
                    submission_result = {
                        "success": (filled_count > 0 or resume_attached),
                        "mode": mode,
                        "dry_run": True,
                        "filled_fields_count": filled_count,
                        "resume_attached": resume_attached,
                        "screenshot_path": screenshot_file,
                        "message": f"Successfully drafted and filled {filled_count} fields. Screenshot saved for review."
                    }
                else:
                    submission_result = {
                        "success": submitted,
                        "mode": "auto",
                        "dry_run": False,
                        "filled_fields_count": filled_count,
                        "resume_attached": resume_attached,
                        "screenshot_path": screenshot_file,
                        "message": "Application submitted successfully." if submitted else "Form filled but submit button requires confirmation."
                    }

                browser.close()
                return submission_result

        except PlaywrightTimeoutError as te:
            return {
                "success": False,
                "error": f"Page load or element interaction timed out: {te}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Browser automation error: {e}"
            }
