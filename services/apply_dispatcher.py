import os
import re
from typing import Dict, Any, Optional
from config import BROWSER_HEADLESS, AUTO_APPLY_MODE
from ai.tailor import ResumeTailor
from services.compiler import LatexCompiler
from services.apply_greenhouse import GreenhouseApplier
from services.apply_lever import LeverApplier
from services.apply_browser import PlaywrightBrowserApplier
from services.url_resolver import UrlResolver
from routers.email_router import EmailRouter

class AutoApplyDispatcher:
    """Unified application manager routing jobs to the most effective application channel."""

    def __init__(
        self,
        mode: Optional[str] = None,  # "auto", "review", "dry_run"
        gemini_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        smtp_config: Optional[Dict[str, Any]] = None
    ):
        self.mode = mode or AUTO_APPLY_MODE
        self.dry_run = (self.mode in ("dry_run", "review"))
        self.tailor = ResumeTailor(gemini_api_key=gemini_api_key, openai_api_key=openai_api_key)
        self.compiler = LatexCompiler()
        self.greenhouse_applier = GreenhouseApplier(dry_run=self.dry_run)
        self.lever_applier = LeverApplier(dry_run=self.dry_run)
        self.browser_applier = PlaywrightBrowserApplier(
            dry_run=self.dry_run,
            headless=BROWSER_HEADLESS,
            user_data_dir="output_resumes/browser_profile"
        )
        if hasattr(self.browser_applier, "form_agent") and self.browser_applier.form_agent:
            self.browser_applier.form_agent.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
            self.browser_applier.form_agent.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")

        smtp = smtp_config or {}
        self.email_router = EmailRouter(
            smtp_host=smtp.get("host", "smtp.gmail.com"),
            smtp_port=smtp.get("port", 587),
            smtp_user=smtp.get("user", ""),
            smtp_password=smtp.get("password", ""),
            sender_name=smtp.get("sender_name", "Md Moniruzzaman"),
            dry_run=self.dry_run
        )

    def detect_channel(self, job: Dict[str, Any], target_url: Optional[str] = None) -> str:
        """Identify the best application channel for a job."""
        url = (target_url or job.get("URL") or "").lower()

        if job.get("Contact Email"):
            return "EMAIL"
        if "greenhouse.io" in url or "gh_jid" in url:
            return "GREENHOUSE"
        if "jobs.lever.co" in url:
            return "LEVER"
        return "BROWSER"

    def process_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tailors CV, compiles PDF, and applies via the appropriate channel.
        """
        company = job.get("Company", "Company")
        title = job.get("Title", "Position")
        raw_url = job.get("URL", "")

        # Resolve aggregator URLs to canonical ATS / direct career links
        target_url = UrlResolver.resolve(raw_url)
        job["Resolved_URL"] = target_url
        channel = self.detect_channel(job, target_url=target_url)

        print(f"\n[AutoApplyDispatcher] Processing application for: {company} - {title}")
        print(f"  • Raw URL: {raw_url}")
        if target_url != raw_url:
            print(f"  • Canonical Resolved URL: {target_url}")
        print(f"  • Channel: {channel} | Mode: {self.mode}")

        # 1. AI Tailoring
        tailored = self.tailor.tailor(job)

        # 2. LaTeX Rendering & PDF Compilation
        safe_company = "".join(c for c in company if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
        os.makedirs("output_resumes", exist_ok=True)
        pdf_path = os.path.join("output_resumes", f"Resume_Moniruzzaman_{safe_company}.pdf")

        rendered_latex = self.compiler.render_latex(
            summary=tailored.get("summary"),
            competencies=tailored.get("competencies"),
            skills=tailored.get("skills")
        )
        compile_ok = self.compiler.compile_pdf(rendered_latex, pdf_path)
        if not compile_ok or not os.path.exists(pdf_path):
            print(f"[AutoApplyDispatcher] Custom PDF compilation unavailable or failed for {company}. Falling back to master resume.")
            master_pdf = os.path.abspath("master_resume.pdf")
            if os.path.exists(master_pdf):
                pdf_path = master_pdf
            elif self.compiler.tectonic_bin:
                self.compiler.compile_pdf(self.compiler.render_latex(), pdf_path)

        # 3. Route to specific channel
        result = {}
        if channel == "GREENHOUSE":
            res = self.greenhouse_applier.apply(
                job_url=target_url,
                pdf_path=pdf_path,
                cover_letter=tailored.get("email_body_text")
            )
            result = {
                "channel": channel,
                "success": res.get("success", False),
                "pdf_path": pdf_path,
                "status": "Applied (Greenhouse API)" if (res.get("success") and not self.dry_run) else "Drafted (Greenhouse Ready)",
                "details": res
            }

        elif channel == "LEVER":
            res = self.lever_applier.apply(
                job_url=target_url,
                pdf_path=pdf_path,
                comments=tailored.get("email_body_text")
            )
            result = {
                "channel": channel,
                "success": res.get("success", False),
                "pdf_path": pdf_path,
                "status": "Applied (Lever API)" if (res.get("success") and not self.dry_run) else "Drafted (Lever Ready)",
                "details": res
            }

        elif channel == "EMAIL":
            contact_email = job.get("Contact Email")
            res = self.email_router.send_application(
                recipient_email=contact_email,
                subject=tailored["email_subject"],
                body_text=tailored["email_body_text"],
                body_html=tailored["email_body_html"],
                pdf_path=pdf_path,
                attachment_filename=f"Md_Moniruzzaman_Resume_{safe_company}.pdf"
            )
            result = {
                "channel": channel,
                "success": res.get("success", False),
                "pdf_path": pdf_path,
                "status": "Applied (Direct Email)" if (res.get("success") and not self.dry_run) else "Drafted (Email Ready)",
                "details": res
            }

        else:  # BROWSER / WEB_PORTAL
            res = self.browser_applier.apply(
                job_url=target_url,
                pdf_path=pdf_path,
                mode=self.mode
            )
            is_success = res.get("success", False)
            if is_success and self.mode == "auto":
                status = "Applied (Web Portal)"
            elif is_success or res.get("filled_fields_count", 0) > 0:
                status = "Drafted (Web Form Filled)"
            else:
                err = res.get("error")
                status = f"Apply via URL ({err})" if err else "Apply via URL"

            result = {
                "channel": channel,
                "success": is_success,
                "pdf_path": pdf_path,
                "status": status,
                "screenshot_path": res.get("screenshot_path"),
                "details": res
            }

        return result
