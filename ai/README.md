# ai

## Overview
The `ai` component package provides automated AI-driven resume tailoring and cover letter generation. It analyzes scraped job titles, company metadata, and descriptions to produce customized LaTeX resume sections (Professional Summary, Core Competencies, Technical Skills) and personalized application email pitches. It supports Google Gemini and OpenAI with deterministic heuristic fallback when API credentials are unavailable or network calls fail.

## Interface
- `class ResumeTailor`: Main tailoring engine.
  - `__init__(gemini_api_key: Optional[str] = None, openai_api_key: Optional[str] = None)`: Initializes client with API keys or environment variables (`GEMINI_API_KEY`, `OPENAI_API_KEY`).
  - `tailor(job: Dict[str, Any]) -> Dict[str, Any]`: Generates tailored content matching the job dictionary. Returns keys:
    - `summary`: Tailored LaTeX string for the professional summary.
    - `competencies`: Tailored LaTeX `\item` list of 8 key competencies.
    - `skills`: Tailored LaTeX technical skills categorized block.
    - `email_subject`: Optimized email subject line for job applications.
    - `email_body_text`: Plain-text customized pitch email.
    - `email_body_html`: HTML-formatted email pitch with portfolio links.
- Constants:
  - `DEFAULT_SUMMARY`: Base mobile engineering summary LaTeX block.
  - `DEFAULT_COMPETENCIES`: Default 8-item competency bullet list in LaTeX.
  - `DEFAULT_SKILLS`: Default technical skills grouping in LaTeX.

## Invariants
- `tailor()` must always return a dictionary containing all 6 required keys (`summary`, `competencies`, `skills`, `email_subject`, `email_body_text`, `email_body_html`) with non-empty string values.
- Fallback chain must never throw unhandled exceptions: Attempts Gemini API first, falls back to OpenAI API, and defaults to deterministic keyword heuristics (`_heuristic_tailor`).
- Generated LaTeX snippets must escape reserved characters (e.g. `\&`, `\%`, `\$`) and format bold spans using `\textbf{...}`.

## Side Effects
- Makes outbound HTTPS POST requests to Google Generative Language API (`https://generativelanguage.googleapis.com`) when `GEMINI_API_KEY` is present.
- Makes outbound HTTPS POST requests to OpenAI API (`https://api.openai.com`) when `OPENAI_API_KEY` is present.
- No local filesystem modifications.

## Verification
- Run: `python -m unittest tests/test_auto_apply.py`

