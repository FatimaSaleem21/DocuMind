import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from rest_framework import status
from rest_framework.test import APITestCase

from docuMind.apps.documents.models import Document, DocumentChunk
from docuMind.apps.documents.services.chunking import chunk_text

MEDIA_ROOT = tempfile.mkdtemp()


def make_text_pdf_bytes(num_pages=2):
    buf = io.BytesIO()
    pdf_canvas = canvas.Canvas(buf)
    for i in range(num_pages):
        pdf_canvas.drawString(100, 700, f"This is page {i + 1}")
        pdf_canvas.showPage()
    pdf_canvas.save()
    return buf.getvalue()


def make_blank_pdf_bytes():
    """A PDF with a page but no text layer — stands in for a scanned/image-only PDF."""
    buf = io.BytesIO()
    pdf_canvas = canvas.Canvas(buf)
    pdf_canvas.showPage()
    pdf_canvas.save()
    return buf.getvalue()


def make_zero_page_pdf_bytes():
    buf = io.BytesIO()
    PdfWriter().write(buf)
    return buf.getvalue()


def make_encrypted_pdf_bytes(password="secret123"):
    reader = PdfReader(io.BytesIO(make_text_pdf_bytes(num_pages=1)))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(password)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


class ChunkTextTests(APITestCase):
    def test_chunk_count_and_overlap_for_known_input(self):
        words = [f"word{i}" for i in range(120)]
        text = " ".join(words)

        chunks = chunk_text(text, chunk_size=50, overlap=10)

        self.assertEqual([len(c.split()) for c in chunks], [50, 50, 40])
        self.assertEqual(chunks[0].split()[-10:], chunks[1].split()[:10])
        self.assertEqual(chunks[1].split()[-10:], chunks[2].split()[:10])

    def test_empty_text_produces_no_chunks(self):
        self.assertEqual(chunk_text(""), [])
        self.assertEqual(chunk_text("   "), [])


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class DocumentUploadTests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    def upload(self, file):
        return self.client.post(reverse("document-upload"), {"file": file}, format="multipart")

    def test_valid_pdf_is_accepted(self):
        pdf = SimpleUploadedFile("sample.pdf", b"%PDF-1.4 rest of the file", content_type="application/pdf")

        response = self.upload(pdf)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], Document.Status.PENDING)
        self.assertIn("id", response.data)

    def test_non_pdf_content_type_is_rejected(self):
        txt = SimpleUploadedFile("notes.txt", b"just some text", content_type="text/plain")

        response = self.upload(txt)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", response.data)

    def test_pdf_extension_with_wrong_magic_bytes_is_rejected(self):
        fake = SimpleUploadedFile("fake.pdf", b"not really a pdf", content_type="application/pdf")

        response = self.upload(fake)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_oversized_file_is_rejected(self):
        big_content = b"%PDF-1.4" + b"0" * (20 * 1024 * 1024 + 1)
        big_pdf = SimpleUploadedFile("big.pdf", big_content, content_type="application/pdf")

        response = self.upload(big_pdf)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_file_is_rejected(self):
        empty = SimpleUploadedFile("empty.pdf", b"", content_type="application/pdf")

        response = self.upload(empty)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(
    MEDIA_ROOT=MEDIA_ROOT,
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class DocumentProcessingTests(APITestCase):
    """
    Runs the task synchronously (no live worker/Redis) against real,
    programmatically generated PDFs to prove extraction + status transitions
    work end to end. This does NOT exercise the real async gap covered by
    the manual polling acceptance check.
    """

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    def upload(self, filename, content):
        pdf = SimpleUploadedFile(filename, content, content_type="application/pdf")
        return self.client.post(reverse("document-upload"), {"file": pdf}, format="multipart")

    def test_text_pdf_reaches_ready_with_correct_page_count(self):
        response = self.upload("sample.pdf", make_text_pdf_bytes(num_pages=3))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        document = Document.objects.get(id=response.data["id"])
        self.assertEqual(document.status, Document.Status.READY)
        self.assertEqual(document.page_count, 3)
        self.assertIsNotNone(document.processed_at)

        chunks = DocumentChunk.objects.filter(document=document)
        self.assertGreater(chunks.count(), 0)
        self.assertEqual(
            set(chunks.values_list("page_number", flat=True)),
            set(range(1, document.page_count + 1)),
        )
        self.assertEqual(
            list(chunks.values_list("chunk_index", flat=True)),
            list(range(chunks.count())),
        )

    def test_scanned_pdf_fails_with_clear_message(self):
        response = self.upload("scanned.pdf", make_blank_pdf_bytes())

        document = Document.objects.get(id=response.data["id"])
        self.assertEqual(document.status, Document.Status.FAILED)
        self.assertIn("scanned", document.error_message)

    def test_zero_page_pdf_fails_with_clear_message(self):
        response = self.upload("empty_pages.pdf", make_zero_page_pdf_bytes())

        document = Document.objects.get(id=response.data["id"])
        self.assertEqual(document.status, Document.Status.FAILED)
        self.assertIn("no pages", document.error_message)

    def test_encrypted_pdf_fails_with_clear_message(self):
        response = self.upload("encrypted.pdf", make_encrypted_pdf_bytes())

        document = Document.objects.get(id=response.data["id"])
        self.assertEqual(document.status, Document.Status.FAILED)
        self.assertIn("password-protected", document.error_message)

    def test_detail_endpoint_returns_current_status_and_error_message(self):
        upload_response = self.upload("scanned.pdf", make_blank_pdf_bytes())

        detail_response = self.client.get(reverse("document-detail", args=[upload_response.data["id"]]))

        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["status"], Document.Status.FAILED)
        self.assertIn("scanned", detail_response.data["error_message"])
