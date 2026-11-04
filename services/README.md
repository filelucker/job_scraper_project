# services

## Overview
The `services` component package provides application execution, document generation, anti-bot evasion, and browser automation capabilities. It houses the unified `AutoApplyDispatcher` which coordinates AI resume tailoring, headless LaTeX compilation, and automated dispatch across multiple channels: direct REST APIs (Greenhouse, Lever), SMTP email, and a headless Playwright browser agent capable of dynamic form inspection, profile-based question answering, and CAPTCHA solving.

## Interface
- `class AutoApplyDispatcher`: Central routing and application manager (`apply_dispatcher.py`).
  - `detect_channel(job: Dict[str, Any], target_url: Optional[str] = None) -> str`: Identifies channel (`EMAIL`, `GREENHOUSE`, `LEVER`, `MANUAL_URL`, `BROWSER`).
  - `process_job(job: Dict[str, Any]) -> Dict[str, Any]`: Tailors resume, compiles PDF, executes application attempt, and returns verified status dictionary (`success`, `channel`, `pdf_path`, `status`, `screenshot_path`, `details`).
- `class GreenhouseApplier`: Headless Greenhouse candidate submission engine (`apply_greenhouse.py`).
  - `apply(job_url: str, pdf_path: str, custom_answers: Optional[Dict[str, Any]] = None, cover_letter: Optional[str] = None, board_token: Optional[str] = None) -> Dict[str, Any]`: Dispatches multipart POST request with candidate profile and resume.
- `class LeverApplier`: Headless Lever candidate submission engine (`apply_lever.py`).
  - `apply(job_url: str, pdf_path: str, comments: Optional[str] = None) -> Dict[str, Any]`: Dispatches multipart POST request with candidate profile and resume.
- `class PlaywrightBrowserApplier`: Web automation applier (`apply_browser.py`).
  - `apply(job_url: str, pdf_path: str, mode: str = "review", screenshot_dir: str = "output_resumes/screenshots") -> Dict[str, Any]`: Automates browser navigation, stealth script injection, form inspection, field filling, screenshot capture, and auto-submission.
- `class FormAgent`: Dynamic form inspection and field filling agent (`form_agent.py`).
  - `inspect_form(page) -> List[Dict[str, Any]]`: Scans DOM for interactive input controls.
  - `answer_fields(controls: List[Dict[str, Any]], candidate: Dict[str, Any]) -> Dict[str, Any]`: Maps candidate profile answers to detected fields.
  - `fill_and_submit(page, controls: List[Dict[str, Any]], answers: Dict[str, Any], pdf_path: str, auto_submit: bool = False, candidate: Optional[Dict[str, Any]] = None) -> Dict[str, Any]`: Types answers, attaches PDF resume, steps through multi-page wizards, and clicks submit.
- `class CaptchaSolver`: Multi-provider CAPTCHA resolver (`captcha_solver.py`).
  - `solve_if_present(page, max_wait_sec: int = 4) -> bool`: Detects and resolves active challenges.
  - Supports Cloudflare Turnstile (behavioral click & iframe injection), reCAPTCHA v2 (audio transcription), and hCaptcha (CapSolver/2Captcha APIs).
- `class LatexCompiler`: Resume compilation service (`compiler.py`).
  - `render_latex(summary: Optional[str] = None, competencies: Optional[str] = None, skills: Optional[str] = None) -> str`: Injects tailored blocks into `templates/resume_template.tex`.
  - `compile_pdf(latex_content: str, output_pdf_path: str) -> bool`: Executes Tectonic with a 15-second timeout and circuit breaker fallback.
- `class CandidateProfile` & `get_candidate_profile()`: Structured candidate background loader (`profile_loader.py`).
- `class UrlResolver`: Canonical ATS URL unwrapper (`url_resolver.py`).
  - `resolve(url: str) -> str`: Follows HTTP redirects and extracts canonical ATS links from aggregators.

## Invariants
- `AutoApplyDispatcher` enforces verified submission statuses: `Applied (Greenhouse API)`, `Applied (Lever API)`, `Applied (Direct Email)`, or `Applied (Web Portal)`. Jobs blocked by candidate logins or failed forms are never falsely marked as applied and return `Requires Manual Apply (...)`.
- `LatexCompiler.compile_pdf` enforces a 15-second subprocess timeout; on timeout, `compilation_failed` is set to `True` to immediately short-circuit subsequent compilation attempts for the run and fall back to `master_resume.pdf`.
- Tailored resume PDFs are written to `output_resumes/Resume_Moniruzzaman_{safe_company}.pdf`.
- `UrlResolver.resolve` must never corrupt direct ATS query parameters (e.g. Workable, Greenhouse, or Lever UTM tags).

## Side Effects
- Spawns headless Chromium processes via Playwright with disk persistence in `PLAYWRIGHT_USER_DATA_DIR`.
- Executes external CLI binaries (`tectonic.exe` or system `tectonic`) via subprocess.
- Reads candidate data from `data/candidate_profile.json` (or `candidate_profile.json`).
- Writes generated resume PDFs and application screenshots to `output_resumes/`.
- Outbound HTTP POST requests to Greenhouse, Lever, and CAPTCHA solving APIs.

## Verification
- Run: `python -m unittest tests/test_auto_apply.py`

