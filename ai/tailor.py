import os
import json
import re
import requests
from typing import Dict, Any, Optional

DEFAULT_SUMMARY = (
    "Seasoned Senior Mobile Application Engineer with 7+ years of experience in "
    "\\textbf{system design \\& architecture}, specializing in \\textbf{scalable mobile systems} "
    "and \\textbf{high-performance applications} across fintech, e-commerce, and healthtech. "
    "Expert in delivering dual-platform depth—bridging native iOS/Android ecosystems and cross-platform "
    "frameworks—to deliver applications that are technically sound and aligned with business outcomes. "
    "Proven track record in driving engineering standards, mentoring teams, and delivering PCI-DSS compliant, "
    "secure payment ecosystems for global markets."
)

DEFAULT_COMPETENCIES = (
    "        \\item Mobile System Architecture \\& Design\n"
    "        \\item Technical Team Leadership \\& Mentoring\n"
    "        \\item Agile/Scrum Methodology \\& Sprint Planning\n"
    "        \\item FinTech Security \\& Compliance (PCI-DSS)\n"
    "        \\item API Design \\& Backend Integration\n"
    "        \\item Performance Profiling \\& Optimization\n"
    "        \\item CI/CD Automation \\& Release Engineering\n"
    "        \\item Unit, Integration \\& UI Testing (TDD)"
)

DEFAULT_SKILLS = (
    "\\textbf{Languages:} Kotlin, Java, Swift, Dart, C\\#, JavaScript, SQL, Bash \\\\\n"
    "\\textbf{Android:} Jetpack Compose, Coroutines, Flow, Hilt, Dagger2, Room, WorkManager, Jetpack Navigation \\\\\n"
    "\\textbf{iOS \\& Cross-Platform:} SwiftUI, Flutter, React Native, Xamarin, BLoC, Redux, Provider \\\\\n"
    "\\textbf{Architecture:} MVVM, MVI, Clean Architecture, SOLID Principles, Design Patterns, Modularization \\\\\n"
    "\\textbf{Infrastructure \\& Tools:} Git, CI/CD (GitHub Actions, Bitrise, Jenkins), Fastlane, Firebase, REST, GraphQL \\\\\n"
    "\\textbf{Testing \\& Quality:} JUnit, Mockito, Espresso, TDD, Static Analysis (Detekt, Lint), SonarQube \\\\\n"
    "\\textbf{Database \\& Cloud:} AWS (S3), SQLite, Realm, Drift, Firestore, Room, ProGuard/R8 (App Security)"
)

class ResumeTailor:
    """Generates tailored resume sections and personalized email pitches using AI or smart heuristics."""

    def __init__(self, gemini_api_key: Optional[str] = None, openai_api_key: Optional[str] = None):
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")

    def tailor(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Produce tailored LaTeX resume content and email application pitch.
        Tries Gemini API -> OpenAI API -> Heuristic Fallback.
        """
        title = job.get("Title", "Senior Mobile Engineer")
        company = job.get("Company", "Company")
        description = job.get("description", "") or ""

        # Try Gemini API if key is present
        if self.gemini_api_key:
            try:
                res = self._call_gemini(title, company, description)
                if res:
                    return res
            except Exception as e:
                print(f"[ResumeTailor] Gemini API tailoring failed: {e}. Falling back...")

        # Try OpenAI API if key is present
        if self.openai_api_key:
            try:
                res = self._call_openai(title, company, description)
                if res:
                    return res
            except Exception as e:
                print(f"[ResumeTailor] OpenAI API tailoring failed: {e}. Falling back...")

        # Heuristic rule-based fallback
        return self._heuristic_tailor(title, company, description)

    def _build_prompt(self, title: str, company: str, description: str) -> str:
        return f"""You are an expert career advisor and technical recruiter tailoring a resume and job application email for:
Candidate: Md Moniruzzaman
Role: Senior Mobile Application Engineer (7+ years experience in Android, iOS, Flutter, React Native, FinTech)
Portfolio: https://moniruz.dev/ | GitHub: https://github.com/filelucker | LinkedIn: https://www.linkedin.com/in/mon000/

Job Target:
Company: {company}
Title: {title}
Description snippet: {description[:1200]}

Please generate a JSON response with the following exact keys:
1. "latex_summary": A professional 3-sentence summary in LaTeX syntax tailored to this role. Emphasize matching skills (e.g. Flutter, Kotlin/Android, React Native, iOS, or FinTech). Use \\textbf{{...}} for bold text and escape special characters like \\&.
2. "latex_competencies": 8 bullet points formatted exactly as:
   "        \\item Competency 1\\n        \\item Competency 2\\n..."
   Prioritizing items most aligned with the job description.
3. "latex_skills": The technical skills block in LaTeX, reordering and highlighting the specific tech stack requested.
4. "email_subject": An effective email subject line, e.g. "Application: {title} - Md Moniruzzaman"
5. "email_body_text": A concise, high-converting 3-paragraph plain text email pitch explaining why Moniruzzaman is a great match for {company}, highlighting relevant live apps (like DGePay for 10k+ merchants, or UNICEF offline-first app), mentioning the attached tailored CV, and asking for a short chat.
6. "email_body_html": An HTML-formatted version of the email with clean styling, links to apps and portfolio, and professional sign-off.

Respond ONLY with valid JSON. Do not include markdown code block formatting like ```json.
"""

    def _call_gemini(self, title: str, company: str, description: str) -> Optional[Dict[str, Any]]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_api_key}"
        prompt = self._build_prompt(title, company, description)
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"}
        }
        resp = requests.post(url, json=payload, timeout=25)
        if resp.status_code == 200:
            data = resp.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return self._parse_llm_json(raw_text, title, company)
        return None

    def _call_openai(self, title: str, company: str, description: str) -> Optional[Dict[str, Any]]:
        url = "https://api.openai.com/v1/chat/completions"
        prompt = self._build_prompt(title, company, description)
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=25)
        if resp.status_code == 200:
            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"].strip()
            return self._parse_llm_json(raw_text, title, company)
        return None

    def _parse_llm_json(self, raw_text: str, title: str, company: str) -> Dict[str, Any]:
        cleaned = raw_text
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        parsed = json.loads(cleaned.strip())
        return {
            "summary": parsed.get("latex_summary", DEFAULT_SUMMARY),
            "competencies": parsed.get("latex_competencies", DEFAULT_COMPETENCIES),
            "skills": parsed.get("latex_skills", DEFAULT_SKILLS),
            "email_subject": parsed.get("email_subject", f"Application: {title} - Md Moniruzzaman"),
            "email_body_text": parsed.get("email_body_text", self._default_email_text(title, company)),
            "email_body_html": parsed.get("email_body_html", self._default_email_html(title, company))
        }

    def _heuristic_tailor(self, title: str, company: str, description: str) -> Dict[str, Any]:
        """Deterministic tailoring based on detected technology keywords."""
        text = f"{title} {description}".lower()

        is_flutter = "flutter" in text or "dart" in text
        is_react_native = "react native" in text or "react" in text
        is_android = "android" in text or "kotlin" in text or "compose" in text
        is_ios = "ios" in text or "swift" in text or "swiftui" in text

        if is_flutter:
            focus_tech = "Flutter \\& Cross-Platform Mobile"
            summary_focus = "specializing in \\textbf{Flutter cross-platform architecture}, offline-first systems, and scalable mobile products"
            key_app_mention = "UNICEF-backed offline-first healthcare apps and multi-platform solutions"
        elif is_react_native:
            focus_tech = "React Native \\& Hybrid Mobile"
            summary_focus = "specializing in \\textbf{React Native mobile architecture}, high-concurrency payment platforms, and modular architectures"
            key_app_mention = "DGePay FinTech platforms supporting 10k+ active merchants"
        elif is_android:
            focus_tech = "Native Android (Kotlin, Jetpack Compose)"
            summary_focus = "specializing in \\textbf{Native Android architecture (Kotlin, Jetpack Compose, Coroutines)}, performance profiling, and modular systems"
            key_app_mention = "scalable digital finance and government utility applications"
        elif is_ios:
            focus_tech = "Native iOS (Swift, SwiftUI)"
            summary_focus = "specializing in \\textbf{Native iOS development (Swift, SwiftUI)}, clean architecture, and secure enterprise apps"
            key_app_mention = "enterprise security and multi-channel payment apps"
        else:
            focus_tech = "Scalable Mobile Systems"
            summary_focus = "specializing in \\textbf{system design \\& architecture}, bridging native iOS/Android ecosystems and cross-platform frameworks"
            key_app_mention = "enterprise FinTech and high-traffic consumer mobile apps"

        summary = (
            f"Seasoned Senior Mobile Application Engineer with 7+ years of experience in \\textbf{{system design \\& architecture}}, "
            f"{summary_focus} across fintech, e-commerce, and enterprise solutions. "
            f"Proven track record delivering PCI-DSS compliant secure payment ecosystems, optimizing performance by up to 50\\%, "
            f"and mentoring engineering teams to ship reliable software."
        )

        return {
            "summary": summary,
            "competencies": DEFAULT_COMPETENCIES,
            "skills": DEFAULT_SKILLS,
            "email_subject": f"Application for {title} - Md Moniruzzaman",
            "email_body_text": self._default_email_text(title, company, focus_tech, key_app_mention),
            "email_body_html": self._default_email_html(title, company, focus_tech, key_app_mention)
        }

    def _default_email_text(self, title: str, company: str, focus_tech: str = "Mobile Engineering", key_app: str = "FinTech and enterprise mobile apps") -> str:
        return f"""Dear Hiring Team at {company},

I am writing to express my strong interest in the {title} position. With over 7 years of software engineering experience specializing in {focus_tech}, I have architected and deployed high-performance mobile systems serving hundreds of thousands of users.

At DG Infotech, I architected the DGePay mobile fintech ecosystem supporting 10k+ merchants with 99.9% uptime and full PCI-DSS compliance, while reducing checkout latency by 50%. Furthermore, I have built offline-first mobile apps for UNICEF and enterprise security applications for global clients.

I have attached my tailored resume for your review. You can also explore my portfolio and interactive project demos at https://moniruz.dev/ or check my code at https://github.com/filelucker.

I would welcome the opportunity to speak with you briefly about how my background aligns with {company}'s engineering goals.

Best regards,

Md Moniruzzaman
Senior Mobile Application Engineer
Dhaka, Bangladesh | +8801721915013
contact@moniruz.dev | https://moniruz.dev/
LinkedIn: https://www.linkedin.com/in/mon000/
"""

    def _default_email_html(self, title: str, company: str, focus_tech: str = "Mobile Engineering", key_app: str = "FinTech and enterprise mobile apps") -> str:
        return f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1f2937; line-height: 1.6; max-width: 650px;">
    <p>Dear Hiring Team at <strong>{company}</strong>,</p>

    <p>I am writing to express my strong interest in the <strong>{title}</strong> position. With over 7 years of software engineering experience specializing in <strong>{focus_tech}</strong>, I have architected and deployed high-performance mobile systems serving hundreds of thousands of users.</p>

    <p>Highlights of what I bring to {company}:</p>
    <ul>
        <li><strong>Scalable FinTech Systems:</strong> Architected the DGePay mobile fintech ecosystem supporting 10k+ merchants with 99.9% uptime and PCI-DSS compliance.</li>
        <li><strong>Performance & Optimization:</strong> Optimized app performance and checkout speeds by 50% while slashing crash rates by 30%.</li>
        <li><strong>Dual-Platform Depth:</strong> Strong native proficiency in Android (Kotlin, Jetpack) and iOS (Swift), paired with Flutter and React Native.</li>
    </ul>

    <p>I have attached my tailored resume for your review. You can also explore my portfolio and live projects at <a href="https://moniruz.dev/" style="color: #0b57d0; text-decoration: none;"><strong>moniruz.dev</strong></a> or review my repositories on <a href="https://github.com/filelucker" style="color: #0b57d0; text-decoration: none;">GitHub</a>.</p>

    <p>I would welcome the opportunity to speak with you briefly about how my background aligns with {company}'s goals.</p>

    <p style="margin-top: 24px;">
        Best regards,<br>
        <strong>Md Moniruzzaman</strong><br>
        <span style="color: #4b5563;">Senior Mobile Application Engineer</span><br>
        <a href="mailto:contact@moniruz.dev" style="color: #0b57d0; text-decoration: none;">contact@moniruz.dev</a> | +8801721915013<br>
        <a href="https://moniruz.dev/" style="color: #0b57d0; text-decoration: none;">Portfolio</a> | 
        <a href="https://www.linkedin.com/in/mon000/" style="color: #0b57d0; text-decoration: none;">LinkedIn</a> | 
        <a href="https://github.com/filelucker" style="color: #0b57d0; text-decoration: none;">GitHub</a>
    </p>
</body>
</html>
"""
