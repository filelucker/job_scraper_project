import os
import re
import requests
from typing import Dict, Any, Optional
from services.profile_loader import get_candidate_profile

class LeverApplier:
    """Handles automated application submissions to Lever Job Boards."""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.profile = get_candidate_profile()

    @staticmethod
    def extract_company_and_job_id(url: str) -> Optional[Dict[str, str]]:
        """Extract company name and job ID from standard Lever URLs."""
        if not url:
            return None
        m = re.search(r'jobs\.lever\.co/([^/]+)/([a-f0-9\-]+)', url)
        if m:
            return {"company": m.group(1), "job_id": m.group(2)}
        return None

    def apply(
        self,
        job_url: str,
        pdf_path: str,
        comments: Optional[str] = None,
        custom_answers: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Apply to a Lever job.
        If dry_run is True, validates fields and schema without dispatching real data.
        """
        meta = self.extract_company_and_job_id(job_url)
        if not meta:
            return {
                "success": False,
                "error": f"Could not parse Lever company and job ID from URL: {job_url}"
            }

        company = meta["company"]
        job_id = meta["job_id"]

        if not os.path.exists(pdf_path):
            return {
                "success": False,
                "error": f"Resume PDF file not found at: {pdf_path}"
            }

        candidate_data = self.profile.data
        post_url = f"https://jobs.lever.co/{company}/{job_id}/apply"

        payload = {
            "name": candidate_data.get("full_name", "Md Moniruzzaman"),
            "email": candidate_data.get("email", "contact@moniruz.dev"),
            "phone": candidate_data.get("phone", "+8801721915013"),
            "org": "Self / Previous",
            "urls[LinkedIn]": candidate_data.get("urls", {}).get("linkedin", ""),
            "urls[GitHub]": candidate_data.get("urls", {}).get("github", ""),
            "urls[Portfolio]": candidate_data.get("urls", {}).get("portfolio", ""),
            "comments": comments or candidate_data.get("summary", "")
        }

        if custom_answers:
            payload.update(custom_answers)

        if self.dry_run:
            print(f"[LeverApplier - DRY RUN] Simulated application to Lever job at '{company}' (ID: {job_id})")
            print(f"  • Candidate: {payload['name']} ({payload['email']})")
            print(f"  • PDF Resume: {pdf_path} (size: {os.path.getsize(pdf_path)} bytes)")
            print(f"  • Target Endpoint: {post_url}")
            return {
                "success": True,
                "dry_run": True,
                "company": company,
                "job_id": job_id,
                "message": "Dry run validated successfully. No external request sent."
            }

        # Live Submission
        try:
            with open(pdf_path, "rb") as resume_file:
                files = {
                    "resume": (os.path.basename(pdf_path), resume_file, "application/pdf")
                }
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": f"https://jobs.lever.co/{company}/{job_id}"
                }
                response = requests.post(post_url, data=payload, files=files, headers=headers, timeout=25)

                if response.status_code in (200, 201, 302):
                    return {
                        "success": True,
                        "dry_run": False,
                        "company": company,
                        "job_id": job_id,
                        "status_code": response.status_code,
                        "response": response.text
                    }
                else:
                    return {
                        "success": False,
                        "dry_run": False,
                        "status_code": response.status_code,
                        "error": f"Lever submission failed with status {response.status_code}: {response.text}"
                    }
        except Exception as e:
            return {
                "success": False,
                "dry_run": False,
                "error": f"Exception during Lever submission: {str(e)}"
            }
