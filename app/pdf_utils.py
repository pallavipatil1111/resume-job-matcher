"""Extract text from an uploaded resume PDF."""
import io

import pdfplumber

MAX_PAGES = 5


class PdfError(ValueError):
    """Raised with a message that can be shown to the user."""


def extract_text(data: bytes) -> str:
    if not data.startswith(b"%PDF"):
        raise PdfError("That file isn't a PDF. Upload your resume as a PDF.")
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            if len(pdf.pages) > MAX_PAGES:
                raise PdfError(f"The PDF has {len(pdf.pages)} pages. Upload a resume of {MAX_PAGES} pages or fewer.")
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    except PdfError:
        raise
    except Exception as exc:  # pdfplumber raises several exception types for broken files
        raise PdfError("The PDF couldn't be read. Try exporting it again from your editor.") from exc
    if len(text.strip()) < 50:
        raise PdfError("No text was found in the PDF. It may be a scanned image; export it as a text PDF instead.")
    return text
