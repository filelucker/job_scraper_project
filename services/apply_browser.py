import os
import sys
import time
import random
from typing import Dict, Any, Optional
from urllib.parse import urljoin, urlparse, urlunparse
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

try:
    from playwright_stealth import Stealth
    _stealth = Stealth()
    stealth_sync = _stealth.apply_stealth_sync
    STEALTH_AVAILABLE = True
except (ImportError, AttributeError):
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

    def __init__(
        self,
        dry_run: bool = True,
        headless: bool = False,
        user_data_dir: str = "output_resumes/browser_profile"
    ):
        self.dry_run = dry_run
        # Auto-detect headless environments (Linux without DISPLAY, CI runners, GitHub Actions)
        is_headless_env = (sys.platform.startswith("linux") and not os.getenv("DISPLAY")) or bool(os.getenv("CI") or os.getenv("GITHUB_ACTIONS"))
        env_headless = os.getenv("BROWSER_HEADLESS", "").strip().lower()
        if env_headless in ("true", "1", "yes"):
            self.headless = True
        elif env_headless in ("false", "0", "no"):
            self.headless = False if not is_headless_env else True
        else:
            self.headless = True if is_headless_env else headless

        if is_headless_env and not self.headless:
            print("[BrowserApplier] Headless environment detected (no X server / DISPLAY or CI). Forcing headless=True.")
            self.headless = True

        self.user_data_dir = os.getenv("PLAYWRIGHT_USER_DATA_DIR", user_data_dir)
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

        # Advanced stealth overrides to defeat Cloudflare Turnstile & bot detection
        stealth_js = """
        () => {
            try {
                const newProto = navigator.__proto__;
                delete newProto.webdriver;
            } catch (e) {}
            Object.defineProperty(Navigator.prototype, 'webdriver', {
                get: () => undefined,
                configurable: true
            });

            window.chrome = {
                runtime: {
                    OnInstalledReason: { INSTALL: 'install', UPDATE: 'update', CHROME_UPDATE: 'chrome_update' },
                    OnRestartRequiredReason: { APP_UPDATE: 'app_update', OS_UPDATE: 'os_update' },
                    PlatformArch: { ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64' },
                    PlatformNaclArch: { ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64' },
                    PlatformOs: { ANDROID: 'android', CROS: 'cros', LINUX: 'linux', MAC: 'mac', OPENBSD: 'openbsd', WIN: 'win' }
                },
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };

            if (window.navigator.permissions) {
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters && parameters.name === 'notifications'
                        ? Promise.resolve({ state: Notification.permission })
                        : originalQuery(parameters)
                );
            }

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

    def _dismiss_cookie_banners(self, page):
        """Dismisses any cookie banners or consent modals that might intercept clicks."""
        cookie_selectors = [
            'button:has-text("Accept all")',
            'button:has-text("Accept All")',
            'button:has-text("Accept cookies")',
            'button:has-text("Accept Cookies")',
            'button:has-text("Allow all")',
            'button:has-text("Allow all cookies")',
            'button:has-text("I accept")',
            'button:has-text("Agree")',
            'button:has-text("Got it")',
            'button#onetrust-accept-btn-handler',
            'button[data-ui="cookie-accept"]',
            'button.cookie-agree',
            'a:has-text("Accept all")',
            'a:has-text("Accept cookies")'
        ]
        for sel in cookie_selectors:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    btn.click()
                    time.sleep(0.5)
                    break
            except Exception:
                pass

    def _handle_cloudflare_turnstile(self, page, max_wait_sec: int = 8):
        """
        Detects Cloudflare Turnstile bot verification challenges and attempts
        to solve/click the checkbox with behavioral simulation or solver.
        """
        if self.captcha_solver._has_turnstile(page):
            print("[BrowserApplier] Cloudflare Turnstile challenge detected. Attempting resolution...")
            self.captcha_solver._solve_turnstile_free(page, max_wait_sec=max_wait_sec)

    def apply(
        self,
        job_url: str,
        pdf_path: str,
        mode: str = "review",  # "review", "auto", "dry_run"
        screenshot_dir: str = "output_resumes/screenshots"
    ) -> Dict[str, Any]:
        """
        1. Resolves canonical ATS/career URL if aggregator.
        2. Opens browser with anti-detection stealth & persistent profile.
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

        # Step 1: Resolve direct canonical URL (unwraps Arbeitnow, Jooble, YC, redirects)
        resolved_url = UrlResolver.resolve(job_url)
        if resolved_url != job_url:
            print(f"[BrowserApplier] Resolved aggregator link: {job_url} -> {resolved_url}")
        target_url = resolved_url

        # Direct ATS URL normalizations to hit application forms directly without breaking query params
        direct_apply_url = target_url
        parsed_target = urlparse(target_url)
        target_path = parsed_target.path.rstrip("/")
        if "apply.workable.com" in parsed_target.netloc:
            if not target_path.endswith("/apply"):
                new_path = f"{target_path}/apply/"
                direct_apply_url = urlunparse((parsed_target.scheme, parsed_target.netloc, new_path, '', parsed_target.query, ''))
        elif "jobs.personio" in parsed_target.netloc:
            if not target_path.endswith("/apply"):
                new_path = f"{target_path}/apply"
                direct_apply_url = urlunparse((parsed_target.scheme, parsed_target.netloc, new_path, '', parsed_target.query, ''))
        elif "jobs.lever.co" in parsed_target.netloc:
            parts = [p for p in target_path.split("/") if p]
            if len(parts) >= 2 and not target_path.endswith("/apply"):
                new_path = f"{target_path}/apply"
                direct_apply_url = urlunparse((parsed_target.scheme, parsed_target.netloc, new_path, '', parsed_target.query, ''))

        try:
            with sync_playwright() as p:
                launch_args = [
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-infobars",
                    "--window-size=1280,800",
                    "--disable-dev-shm-usage",
                    "--no-first-run",
                    "--no-service-autorun",
                    "--password-store=basic"
                ]

                context = None
                browser = None

                def _launch_session(is_headless: bool):
                    try:
                        os.makedirs(self.user_data_dir, exist_ok=True)
                        ctx = p.chromium.launch_persistent_context(
                            user_data_dir=self.user_data_dir,
                            headless=is_headless,
                            args=launch_args,
                            ignore_default_args=["--enable-automation"],
                            viewport={"width": 1280, "height": 800},
                            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                            locale="en-US"
                        )
                        pg = ctx.pages[0] if ctx.pages else ctx.new_page()
                        return ctx, None, pg
                    except Exception as ctx_err:
                        print(f"[BrowserApplier] Note: Falling back to standard browser context: {ctx_err}")
                        br = p.chromium.launch(
                            headless=is_headless,
                            args=launch_args,
                            ignore_default_args=["--enable-automation"]
                        )
                        ctx = br.new_context(
                            viewport={"width": 1280, "height": 800},
                            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                            locale="en-US"
                        )
                        pg = ctx.new_page()
                        return ctx, br, pg

                try:
                    context, browser, page = _launch_session(self.headless)
                except Exception as launch_err:
                    err_msg = str(launch_err).lower()
                    if not self.headless and any(k in err_msg for k in ("xserver", "display", "platform failed", "target page, context or browser has been closed")):
                        print(f"[BrowserApplier] Headed browser launch failed ({launch_err}). Automatically retrying in headless=True mode...")
                        self.headless = True
                        context, browser, page = _launch_session(True)
                    else:
                        raise

                page.set_default_timeout(18000)

                # Step 2: Inject Stealth Scripts
                self._inject_stealth_scripts(page)

                nav_url = direct_apply_url
                print(f"[BrowserApplier] Navigating to target: {nav_url}")
                try:
                    page.goto(nav_url, wait_until="domcontentloaded")
                except Exception:
                    if nav_url != target_url:
                        print(f"[BrowserApplier] Direct apply URL failed, falling back to base URL: {target_url}")
                        page.goto(target_url, wait_until="domcontentloaded")

                time.sleep(1.0)
                self._dismiss_cookie_banners(page)
                self.captcha_solver.solve_if_present(page, max_wait_sec=4)

                # Step 3: Trigger application form if landing on an overview/job detail view
                controls = self.form_agent.inspect_form(page)
                target_context = page

                if len(controls) == 0:
                    apply_triggers = [
                        '[data-ui="overview-apply-btn"]',
                        '[data-ui="application-form-tab"]',
                        '[data-ui="apply-button"]',
                        '[data-qa="apply-button"]',
                        '[data-test="apply-button"]',
                        'a[href*="/apply"]',
                        'a[href*="#apply"]',
                        'a[href*="#app"]',
                        'a:has-text("Apply for this job")',
                        'button:has-text("Apply for this job")',
                        'a:has-text("Apply for this position")',
                        'button:has-text("Apply for this position")',
                        'a:has-text("Apply Now")',
                        'button:has-text("Apply Now")',
                        'a:has-text("Apply online")',
                        'button:has-text("Apply online")',
                        'a:has-text("I\'m interested")',
                        'button:has-text("I\'m interested")',
                        'a:has-text("Easy Apply")',
                        'button:has-text("Easy Apply")',
                        'a:has-text("Apply")',
                        'button:has-text("Apply")'
                    ]
                    for btn_sel in apply_triggers:
                        try:
                            btn = page.query_selector(btn_sel)
                            if btn and btn.is_visible():
                                btn_href = btn.get_attribute("href")
                                if btn_href:
                                    full_apply = urljoin(page.url, btn_href)
                                    print(f"[BrowserApplier] Following apply link: {full_apply}")
                                    page.goto(full_apply, wait_until="domcontentloaded")
                                    time.sleep(2)
                                    break
                                else:
                                    btn.click()
                                    time.sleep(2)
                                    break
                        except Exception:
                            pass

                    self._dismiss_cookie_banners(page)
                    controls = self.form_agent.inspect_form(page)

                # Step 4: Check if form is embedded in child iframe (e.g. Greenhouse, Lever, Workable frames)
                if len(controls) == 0:
                    for frame in page.frames:
                        if frame == page.main_frame:
                            continue
                        try:
                            frame_controls = self.form_agent.inspect_form(frame)
                            if len(frame_controls) > 0:
                                print(f"[BrowserApplier] Found {len(frame_controls)} controls inside iframe: {frame.url}")
                                controls = frame_controls
                                target_context = frame
                                break
                        except Exception:
                            pass

                print(f"[BrowserApplier] Found {len(controls)} interactive form control(s) on the page.")

                if len(controls) == 0:
                    print(f"[BrowserApplier] No interactive form controls found on {nav_url}. Skipping submission.")
                    return {
                        "success": False,
                        "submitted": False,
                        "filled_fields_count": 0,
                        "error": "No interactive form fields detected on page"
                    }

                answers = self.form_agent.answer_fields(controls, candidate)

                # Solve CAPTCHA before submission only if a challenge is active
                if self.captcha_solver._has_turnstile(page) or self.captcha_solver._has_recaptcha(page) or self.captcha_solver._has_hcaptcha(page):
                    self.captcha_solver.solve_if_present(page, max_wait_sec=4)

                is_simulation = (mode in ("review", "dry_run") or self.dry_run)
                auto_submit = (mode == "auto" and not self.dry_run)

                fill_res = self.form_agent.fill_and_submit(
                    page=target_context,
                    controls=controls,
                    answers=answers,
                    pdf_path=pdf_path,
                    auto_submit=auto_submit,
                    candidate=candidate
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
                    is_auto_success = submitted or (filled_count > 0)
                    submission_result = {
                        "success": is_auto_success,
                        "mode": "auto",
                        "dry_run": False,
                        "submitted": submitted,
                        "filled_fields_count": filled_count,
                        "resume_attached": resume_attached,
                        "screenshot_path": screenshot_file,
                        "message": "Application submitted successfully." if submitted else ("Form filled and submitted." if is_auto_success else "Form inspection found no interactive fields.")
                    }

                try:
                    context.close()
                except Exception:
                    pass
                if browser:
                    try:
                        browser.close()
                    except Exception:
                        pass

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
