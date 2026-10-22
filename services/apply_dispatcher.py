import os
import re
from typing import Dict, Any, Optional
from ai.tailor import ResumeTailor
from services.compiler import LatexCompiler
from services.apply_greenhouse import GreenhouseApplier
from services.apply_lever import LeverApplier
from services.apply_browser import PlaywrightBrowserApplier
from routers.email_router import EmailRouter

class AutoApplyDispatcher:
    """Unified application manager routing jobs to the most effective application channel."""

    def __init__(
        self,
        mode: str = "review",  # "review", "auto", "dry_run"
        gemini_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        smtp_config: Optional[Dict[str, Any]] = None
    ):
        self.mode = mode
        self.dry_run = (mode == "dry_run")
        self.tailor = ResumeTailor(gemini_api_key=gemini_api_key, openai_api_key=openai_api_key)
        self.compiler = LatexCompiler()
        self.greenhouse_applier = GreenhouseApplier(dry_run=self.dry_run)
        self.lever_applier = LeverApplier(dry_run=self.dry_run)
        self.browser_applier = PlaywrightBrowserApplier(dry_run=self.dry_run)

        smtp = smtp_config or {}
        self.email_router = EmailRouter(
            smtp_host=smtp.get("host", "smtp.gmail.com"),
            smtp_port=smtp.get("port", 587),
            smtp_user=smtp.get("user", ""),
            smtp_password=smtp.get("password", ""),
            sender_name=smtp.get("sender_name", "Md Moniruzzaman"),
            dry_run=self.dry_run
        )

    def detect_channel(self, job: Dict[str, Any]) -> str:
        """Identify the best application channel for a job."""
        url = (job.get("URL") or "").lower()

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
        url = job.get("URL", "")
        channel = self.detect_channel(job)

        print(f"\n[AutoApplyDispatcher] Processing application for: {company} - {title}")
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
            print(f"[AutoApplyDispatcher] PDF compilation failed for {company}. Falling back to master resume.")
            pdf_path = "master_resume.pdf"
            if not os.path.exists(pdf_path):
                self.compiler.compile_pdf(self.compiler.render_latex(), pdf_path)

        # 3. Route to specific channel
        result = {}
        if channel == "GREENHOUSE":
            res = self.greenhouse_applier.apply(
                job_url=url,
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
                job_url=url,
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
                job_url=url,
                pdf_path=pdf_path,
                mode=self.mode
            )
            result = {
                "channel": channel,
                "success": res.get("success", False),
                "pdf_path": pdf_path,
                "status": "Applied (Web Portal)" if (res.get("success") and self.mode == "auto") else "Drafted (Web Form Filled)",
                "screenshot_path": res.get("screenshot_path"),
                "details": res
            }

        return result
