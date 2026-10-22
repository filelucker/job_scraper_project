import os
import re
import requests
from typing import Dict, Any, Optional
from services.profile_loader import get_candidate_profile

class GreenhouseApplier:
    """Handles automated application submissions to Greenhouse Job Boards via their public API."""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.profile = get_candidate_profile()

    @staticmethod
    def extract_board_and_job_id(url: str) -> Optional[Dict[str, str]]:
        """Extract board token and job ID from standard Greenhouse URLs."""
        if not url:
            return None

        # Pattern 1: https://(job-)boards.greenhouse.io/{board}/jobs/{job_id}
        m1 = re.search(r'greenhouse\.io/(?:embed/job_app\?for=)?([^/]+)/jobs/(\d+)', url)
        if m1:
            return {"board_token": m1.group(1), "job_id": m1.group(2)}

        # Pattern 2: gh_jid parameter e.g. https://.../job?gh_jid=8593713002
        m2 = re.search(r'gh_jid=(\d+)', url)
        if m2:
            # Domain or path might hold the board name
            return {"board_token": None, "job_id": m2.group(1)}

        return None

    def get_job_questions(self, board_token: str, job_id: str) -> Optional[Dict[str, Any]]:
        """Fetch available question schemas for the target Greenhouse position."""
        url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}?questions=true"
        try:
            resp = requests.get(url, timeout=12)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"[GreenhouseApplier] Failed to fetch questions for {board_token}/{job_id}: {e}")
        return None

    def apply(
        self,
        job_url: str,
        pdf_path: str,
        custom_answers: Optional[Dict[str, Any]] = None,
        cover_letter: Optional[str] = None,
        board_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Apply to a Greenhouse job.
        If dry_run is True, validates fields and schema without dispatching real data.
        """
        meta = self.extract_board_and_job_id(job_url)
        if not meta or not meta.get("job_id"):
            return {
                "success": False,
                "error": f"Could not parse Greenhouse board token and job ID from URL: {job_url}"
            }

        resolved_board = board_token or meta.get("board_token")
        job_id = meta["job_id"]

        if not resolved_board:
            return {
                "success": False,
                "error": f"Greenhouse board token missing for job ID {job_id}"
            }

        if not os.path.exists(pdf_path):
            return {
                "success": False,
                "error": f"Resume PDF file not found at: {pdf_path}"
            }

        questions_data = self.get_job_questions(resolved_board, job_id)
        job_title = questions_data.get("title", "Position") if questions_data else "Position"

        candidate_data = self.profile.data
        post_url = f"https://boards-api.greenhouse.io/v1/boards/{resolved_board}/jobs/{job_id}"

        # Standard Greenhouse application fields
        payload = {
            "first_name": candidate_data.get("first_name", "Md"),
            "last_name": candidate_data.get("last_name", "Moniruzzaman"),
            "email": candidate_data.get("email", "contact@moniruz.dev"),
            "phone": candidate_data.get("phone", "+8801721915013"),
            "urls[LinkedIn]": candidate_data.get("urls", {}).get("linkedin", ""),
            "urls[GitHub]": candidate_data.get("urls", {}).get("github", ""),
            "urls[Portfolio]": candidate_data.get("urls", {}).get("portfolio", "")
        }

        if cover_letter:
            payload["cover_letter_text"] = cover_letter

        if custom_answers:
            payload.update(custom_answers)

        if self.dry_run:
            print(f"[GreenhouseApplier - DRY RUN] Simulated application to '{job_title}' at '{resolved_board}'")
            print(f"  • Candidate: {payload['first_name']} {payload['last_name']} ({payload['email']})")
            print(f"  • PDF Resume: {pdf_path} (size: {os.path.getsize(pdf_path)} bytes)")
            print(f"  • Target Endpoint: {post_url}")
            return {
                "success": True,
                "dry_run": True,
                "job_title": job_title,
                "board": resolved_board,
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
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                response = requests.post(post_url, data=payload, files=files, headers=headers, timeout=25)

                if response.status_code in (200, 201):
                    return {
                        "success": True,
                        "dry_run": False,
                        "job_title": job_title,
                        "status_code": response.status_code,
                        "response": response.text
                    }
                else:
                    return {
                        "success": False,
                        "dry_run": False,
                        "status_code": response.status_code,
                        "error": f"Greenhouse submission failed with status {response.status_code}: {response.text}"
                    }
        except Exception as e:
            return {
                "success": False,
                "dry_run": False,
                "error": f"Exception during Greenhouse submission: {str(e)}"
            }
