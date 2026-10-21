import os
import unittest
from handlers.email_extractor import JobEmailExtractor
from ai.tailor import ResumeTailor
from services.compiler import LatexCompiler
from routers.email_router import EmailRouter

class TestAutoApplyPipeline(unittest.TestCase):
    
    def test_1_email_extraction(self):
        sample_job = {
            "Title": "Senior Android Engineer",
            "Company": "FinTech Corp",
            "URL": "https://example.com/jobs/android",
            "description": "Please send your resume to careers@fintechcorp.com or hiring@fintechcorp.com to apply."
        }
        res = JobEmailExtractor.analyze_job(sample_job)
        self.assertTrue(res["has_email"])
        self.assertEqual(res["email"], "careers@fintechcorp.com")
        self.assertEqual(res["apply_method"], "EMAIL")

    def test_2_tailor_and_compile(self):
        sample_job = {
            "Title": "Staff Mobile Engineer (Flutter)",
            "Company": "HealthTech Global",
            "description": "We are seeking a Flutter and Dart expert to lead our offline-first medical apps."
        }
        tailor = ResumeTailor()
        tailored = tailor.tailor(sample_job)
        
        self.assertIn("Flutter", tailored["summary"])
        self.assertIn("Staff Mobile Engineer", tailored["email_subject"])
        self.assertIn("HealthTech Global", tailored["email_body_text"])
        self.assertTrue(len(tailored["email_body_text"]) > 100)

        compiler = LatexCompiler()
        rendered_latex = compiler.render_latex(
            summary=tailored["summary"],
            competencies=tailored["competencies"],
            skills=tailored["skills"]
        )
        
        test_pdf = os.path.join("output_resumes", "test_tailored_resume.pdf")
        ok = compiler.compile_pdf(rendered_latex, test_pdf)
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(test_pdf))
        self.assertTrue(os.path.getsize(test_pdf) > 1000)

    def test_3_email_router_dry_run(self):
        compiler = LatexCompiler()
        test_pdf = os.path.join("output_resumes", "test_dryrun_resume.pdf")
        compiler.compile_pdf(compiler.render_latex(), test_pdf)
        self.assertTrue(os.path.exists(test_pdf))
        
        router = EmailRouter(dry_run=True)
        res = router.send_application(
            recipient_email="careers@fintechcorp.com",
            subject="Application: Senior Android Engineer - Md Moniruzzaman",
            body_text="Test body",
            body_html="<p>Test body</p>",
            pdf_path=test_pdf
        )
        self.assertTrue(res["success"])
        self.assertTrue(res["dry_run"])

if __name__ == "__main__":
    unittest.main()
