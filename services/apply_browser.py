import os
import time
from typing import Dict, Any, Optional
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from services.profile_loader import get_candidate_profile

class PlaywrightBrowserApplier:
    """Automates universal job application form filling and submission using Playwright."""

    def __init__(self, dry_run: bool = True, headless: bool = True):
        self.dry_run = dry_run
        self.headless = headless
        self.profile = get_candidate_profile()

    def apply(
        self,
        job_url: str,
        pdf_path: str,
        mode: str = "review",  # "review", "auto", "dry_run"
        screenshot_dir: str = "output_resumes/screenshots"
    ) -> Dict[str, Any]:
        """
        Open job posting, detect application fields, fill candidate info, attach PDF resume.
        In 'dry_run' or 'review' mode, takes a screenshot and stops before submission.
        In 'auto' mode, clicks submit.
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

        filled_fields = []
        submission_result = {}

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                page.set_default_timeout(25000)

                print(f"[BrowserApplier] Navigating to: {job_url}")
                page.goto(job_url, wait_until="domcontentloaded")
                time.sleep(2)

                # Check if there is an "Apply" button to click first
                apply_button_selectors = [
                    'a:has-text("Apply Now")',
                    'button:has-text("Apply Now")',
                    'a:has-text("Apply for this job")',
                    'button:has-text("Apply for this job")',
                    'a:has-text("Apply")',
                    'button:has-text("Apply")'
                ]
                for btn_sel in apply_button_selectors:
                    try:
                        btn = page.query_selector(btn_sel)
                        if btn and btn.is_visible():
                            btn.click()
                            time.sleep(2)
                            break
                    except Exception:
                        pass

                # 1. First Name
                first_name_sel = page.query_selector('input[name*="first" i], input[id*="first" i], input[autocomplete*="given-name"]')
                if first_name_sel and first_name_sel.is_visible():
                    first_name_sel.fill(candidate.get("first_name", "Md"))
                    filled_fields.append("First Name")

                # 2. Last Name
                last_name_sel = page.query_selector('input[name*="last" i], input[id*="last" i], input[autocomplete*="family-name"]')
                if last_name_sel and last_name_sel.is_visible():
                    last_name_sel.fill(candidate.get("last_name", "Moniruzzaman"))
                    filled_fields.append("Last Name")

                # 3. Full Name fallback (if first/last not present)
                if not first_name_sel and not last_name_sel:
                    name_sel = page.query_selector('input[name*="name" i], input[id*="name" i]')
                    if name_sel and name_sel.is_visible():
                        name_sel.fill(candidate.get("full_name", "Md Moniruzzaman"))
                        filled_fields.append("Full Name")

                # 4. Email
                email_sel = page.query_selector('input[type="email"], input[name*="email" i], input[id*="email" i]')
                if email_sel and email_sel.is_visible():
                    email_sel.fill(candidate.get("email", "contact@moniruz.dev"))
                    filled_fields.append("Email")

                # 5. Phone
                phone_sel = page.query_selector('input[type="tel"], input[name*="phone" i], input[id*="phone" i]')
                if phone_sel and phone_sel.is_visible():
                    phone_sel.fill(candidate.get("phone", "+8801721915013"))
                    filled_fields.append("Phone")

                # 6. LinkedIn
                linkedin_sel = page.query_selector('input[name*="linkedin" i], input[id*="linkedin" i], input[placeholder*="linkedin" i]')
                if linkedin_sel and linkedin_sel.is_visible():
                    linkedin_sel.fill(candidate.get("urls", {}).get("linkedin", ""))
                    filled_fields.append("LinkedIn")

                # 7. GitHub
                github_sel = page.query_selector('input[name*="github" i], input[id*="github" i], input[placeholder*="github" i]')
                if github_sel and github_sel.is_visible():
                    github_sel.fill(candidate.get("urls", {}).get("github", ""))
                    filled_fields.append("GitHub")

                # 8. Resume File Upload
                file_input = page.query_selector('input[type="file"]')
                if file_input:
                    try:
                        abs_pdf = os.path.abspath(pdf_path)
                        file_input.set_input_files(abs_pdf)
                        filled_fields.append("Resume PDF Attached")
                    except Exception as upload_err:
                        print(f"[BrowserApplier] File upload error: {upload_err}")

                # Save screenshot of the filled form
                time.sleep(1)
                page.screenshot(path=screenshot_file, full_page=True)

                is_simulation = (mode in ("review", "dry_run") or self.dry_run)

                if is_simulation:
                    submission_result = {
                        "success": True,
                        "mode": mode,
                        "dry_run": True,
                        "filled_fields": filled_fields,
                        "screenshot_path": screenshot_file,
                        "message": f"Form fields filled ({', '.join(filled_fields)}). Form held before submission for {mode} mode."
                    }
                else:
                    # Auto submission mode: find and click submit button
                    submit_button = page.query_selector(
                        'button[type="submit"], input[type="submit"], button:has-text("Submit Application"), button:has-text("Submit")'
                    )
                    if submit_button and submit_button.is_visible():
                        submit_button.click()
                        time.sleep(4)
                        # Capture post-submission screenshot
                        post_submit_file = os.path.join(screenshot_dir, f"submitted_{timestamp}.png")
                        page.screenshot(path=post_submit_file)
                        submission_result = {
                            "success": True,
                            "mode": "auto",
                            "dry_run": False,
                            "filled_fields": filled_fields,
                            "screenshot_path": post_submit_file,
                            "message": "Form submitted successfully."
                        }
                    else:
                        submission_result = {
                            "success": False,
                            "mode": "auto",
                            "error": "Submit button not found or not visible.",
                            "screenshot_path": screenshot_file
                        }

                browser.close()
                return submission_result

        except PlaywrightTimeoutError as te:
            return {
                "success": False,
                "error": f"Page load or element search timed out: {te}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Browser automation error: {e}"
            }
