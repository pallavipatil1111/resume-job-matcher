from flask import Flask, jsonify, render_template, request

from .matcher import score_resume
from .pdf_utils import PdfError, extract_text

MAX_UPLOAD_MB = 2
MIN_JOB_CHARS = 80
MIN_RESUME_CHARS = 100
MAX_TEXT_CHARS = 30_000


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/api/score")
    def score():
        job = (request.form.get("job_description") or "").strip()
        resume = (request.form.get("resume_text") or "").strip()
        upload = request.files.get("resume_file")

        if upload and upload.filename:
            try:
                resume = extract_text(upload.read())
            except PdfError as exc:
                return jsonify(error=str(exc), field="resume_file"), 400

        if len(resume) < MIN_RESUME_CHARS:
            return jsonify(error="Add your resume: upload a PDF or paste at least a few lines of text.", field="resume"), 400
        if len(job) < MIN_JOB_CHARS:
            return jsonify(error="Paste the full job description, at least a few sentences.", field="job_description"), 400
        if len(job) > MAX_TEXT_CHARS or len(resume) > MAX_TEXT_CHARS:
            return jsonify(error="That text is too long. Paste only the resume and job description.", field="job_description"), 400

        return jsonify(score_resume(resume, job).to_dict())

    @app.errorhandler(413)
    def too_large(_err):
        return jsonify(error=f"That file is larger than {MAX_UPLOAD_MB} MB. Upload a smaller PDF.", field="resume_file"), 413

    return app


app = create_app()
