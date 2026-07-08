from django.conf import settings
from django.core.exceptions import ValidationError

PDF_MAGIC_NUMBER = b"%PDF-"


def validate_pdf_file(uploaded_file):
    if uploaded_file.size == 0:
        raise ValidationError("Uploaded file is empty.")

    if uploaded_file.size > settings.MAX_UPLOAD_SIZE_BYTES:
        max_mb = settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
        raise ValidationError(f"File exceeds the {max_mb}MB limit.")

    if uploaded_file.content_type != "application/pdf":
        raise ValidationError("Only PDF files are accepted.")

    header = uploaded_file.read(len(PDF_MAGIC_NUMBER))
    uploaded_file.seek(0)
    if header != PDF_MAGIC_NUMBER:
        raise ValidationError("File content does not look like a valid PDF.")
