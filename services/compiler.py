import os
import re
import shutil
import subprocess
import tempfile
from typing import Optional

TECTONIC_FALLBACK_PATH = r"C:\Users\mzama\AppData\Local\tectonic\tectonic.exe"

def get_tectonic_path() -> str:
    """Find tectonic executable in PATH or fallback path."""
    which_path = shutil.which("tectonic")
    if which_path and os.path.exists(which_path):
        return which_path
    if os.path.exists(TECTONIC_FALLBACK_PATH):
        return TECTONIC_FALLBACK_PATH
    raise FileNotFoundError("Tectonic executable not found in PATH or default install directory.")

def escape_latex(text: str) -> str:
    """Safely escape text for LaTeX insertion while preserving intentional LaTeX tags."""
    if not text:
        return ""
    
    # If the text already contains LaTeX formatting tags (like \textbf, \textit, etc.),
    # we should only escape standalone special characters outside of commands.
    # Replace markdown **bold** with \textbf{...}
    text = re.sub(r'\*\*(.+?)\*\*', r'\\textbf{\1}', text)
    
    # Replace unescaped & that isn't already \&
    text = re.sub(r'(?<!\\)&', r'\&', text)
    # Replace unescaped %
    text = re.sub(r'(?<!\\)%', r'\%', text)
    # Replace unescaped $
    text = re.sub(r'(?<!\\)\$', r'\$', text)
    # Replace unescaped #
    text = re.sub(r'(?<!\\)#', r'\#', text)
    # Replace unescaped _ that isn't inside a command or already \_
    text = re.sub(r'(?<!\\)_', r'\_', text)
    
    return text

class LatexCompiler:
    """Service to render LaTeX templates and compile them to PDF using Tectonic."""

    def __init__(self, template_path: Optional[str] = None):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.template_path = template_path or os.path.join(base_dir, "templates", "resume_template.tex")
        self.tectonic_bin = get_tectonic_path()

    def render_latex(
        self,
        summary: Optional[str] = None,
        competencies: Optional[str] = None,
        skills: Optional[str] = None
    ) -> str:
        """Render the LaTeX template with tailored sections or fallback defaults."""
        with open(self.template_path, "r", encoding="utf-8") as f:
            template = f.read()

        default_summary = (
            "Seasoned Senior Mobile Application Engineer with 7+ years of experience in "
            "\\textbf{system design \\& architecture}, specializing in \\textbf{scalable mobile systems} "
            "and \\textbf{high-performance applications} across fintech, e-commerce, and healthtech. "
            "Expert in delivering dual-platform depth—bridging native iOS/Android ecosystems and cross-platform "
            "frameworks—to deliver applications that are technically sound and aligned with business outcomes. "
            "Proven track record in driving engineering standards, mentoring teams, and delivering PCI-DSS compliant, "
            "secure payment ecosystems for global markets."
        )

        default_competencies = (
            "        \\item Mobile System Architecture \\& Design\n"
            "        \\item Technical Team Leadership \\& Mentoring\n"
            "        \\item Agile/Scrum Methodology \\& Sprint Planning\n"
            "        \\item FinTech Security \\& Compliance (PCI-DSS)\n"
            "        \\item API Design \\& Backend Integration\n"
            "        \\item Performance Profiling \\& Optimization\n"
            "        \\item CI/CD Automation \\& Release Engineering\n"
            "        \\item Unit, Integration \\& UI Testing (TDD)"
        )

        default_skills = (
            "\\textbf{Languages:} Kotlin, Java, Swift, Dart, C\\#, JavaScript, SQL, Bash \\\\\n"
            "\\textbf{Android:} Jetpack Compose, Coroutines, Flow, Hilt, Dagger2, Room, WorkManager, Jetpack Navigation \\\\\n"
            "\\textbf{iOS \\& Cross-Platform:} SwiftUI, Flutter, React Native, Xamarin, BLoC, Redux, Provider \\\\\n"
            "\\textbf{Architecture:} MVVM, MVI, Clean Architecture, SOLID Principles, Design Patterns, Modularization \\\\\n"
            "\\textbf{Infrastructure \\& Tools:} Git, CI/CD (GitHub Actions, Bitrise, Jenkins), Fastlane, Firebase, REST, GraphQL \\\\\n"
            "\\textbf{Testing \\& Quality:} JUnit, Mockito, Espresso, TDD, Static Analysis (Detekt, Lint), SonarQube \\\\\n"
            "\\textbf{Database \\& Cloud:} AWS (S3), SQLite, Realm, Drift, Firestore, Room, ProGuard/R8 (App Security)"
        )

        final_summary = escape_latex(summary) if summary else default_summary
        final_competencies = competencies if competencies else default_competencies
        final_skills = skills if skills else default_skills

        content = template.replace("<<<PROFESSIONAL_SUMMARY>>>", final_summary)
        content = content.replace("<<<CORE_COMPETENCIES>>>", final_competencies)
        content = content.replace("<<<TECHNICAL_SKILLS>>>", final_skills)

        return content

    def compile_pdf(self, latex_content: str, output_pdf_path: str) -> bool:
        """Compile given LaTeX content into a PDF file at output_pdf_path using Tectonic."""
        os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_tex = os.path.join(temp_dir, "resume.tex")
            with open(temp_tex, "w", encoding="utf-8") as f:
                f.write(latex_content)

            cmd = [
                self.tectonic_bin,
                temp_tex,
                "--outdir",
                temp_dir
            ]
            
            try:
                res = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=45,
                    check=True
                )
                generated_pdf = os.path.join(temp_dir, "resume.pdf")
                if os.path.exists(generated_pdf):
                    shutil.copy2(generated_pdf, output_pdf_path)
                    return True
                return False
            except subprocess.CalledProcessError as e:
                err_output = e.stderr.decode('utf-8', errors='ignore')
                print(f"[LatexCompiler] Tectonic compilation failed: {err_output}")
                return False
            except Exception as e:
                print(f"[LatexCompiler] Unexpected error compiling PDF: {e}")
                return False
