import io
import unittest
from pathlib import Path

from app import create_app

FIXTURES = Path(__file__).parent / "fixtures"
JOB = (FIXTURES / "job_java_backend.txt").read_text()


class ApiTest(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def post(self, **data):
        return self.client.post("/api/score", data=data, content_type="multipart/form-data")

    def test_home_page_loads(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Resume", res.data)

    def test_health(self):
        self.assertEqual(self.client.get("/health").get_json(), {"status": "ok"})

    def test_scores_uploaded_pdf(self):
        pdf = (FIXTURES / "sample_resume.pdf").read_bytes()
        res = self.post(resume_file=(io.BytesIO(pdf), "resume.pdf"), job_description=JOB)
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertIn("score", body)
        self.assertIn("Spring Boot", body["matched_skills"])
        self.assertIn("Docker", body["missing_skills"])

    def test_scores_pasted_text(self):
        res = self.post(resume_text="Java Spring Boot MySQL JUnit Git developer. " * 5, job_description=JOB)
        self.assertEqual(res.status_code, 200)

    def test_rejects_non_pdf_upload(self):
        bad = (FIXTURES / "not_a_pdf.pdf").read_bytes()
        res = self.post(resume_file=(io.BytesIO(bad), "resume.pdf"), job_description=JOB)
        self.assertEqual(res.status_code, 400)
        self.assertIn("isn't a PDF", res.get_json()["error"])

    def test_requires_job_description(self):
        res = self.post(resume_text="Java developer " * 20, job_description="too short")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_json()["field"], "job_description")

    def test_requires_resume(self):
        res = self.post(job_description=JOB)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_json()["field"], "resume")

    def test_rejects_files_over_2mb(self):
        big = b"%PDF" + b"0" * (3 * 1024 * 1024)
        res = self.post(resume_file=(io.BytesIO(big), "big.pdf"), job_description=JOB)
        self.assertEqual(res.status_code, 413)


if __name__ == "__main__":
    unittest.main()
