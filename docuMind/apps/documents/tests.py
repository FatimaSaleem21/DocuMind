import io
import shutil
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from rest_framework import status
from rest_framework.test import APITestCase

from docuMind.apps.documents.models import Document, DocumentChunk
from docuMind.apps.documents.services import embeddings, retrieval
from docuMind.apps.documents.services.chunking import chunk_text

FAKE_EMBEDDING = [0.0] * 1536


def unit_vector(axis: int) -> list[float]:
    vector = [0.0] * 1536
    vector[axis] = 1.0
    return vector

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


class RetrievalTests(TestCase):
    def make_document(self, status_=Document.Status.READY, session_id="sess-1"):
        return Document.objects.create(
            original_filename="doc.pdf",
            status=status_,
            page_count=1,
            session_id=session_id,
        )

    def make_chunk(self, document, embedding, chunk_index=0, content="chunk content"):
        return DocumentChunk.objects.create(
            document=document,
            content=content,
            chunk_index=chunk_index,
            page_number=1,
            embedding=embedding,
        )

    @patch.object(retrieval, "embed_query")
    def test_closest_chunk_ranks_first(self, mock_embed_query):
        mock_embed_query.return_value = unit_vector(0)
        document = self.make_document()
        close = self.make_chunk(document, unit_vector(0), chunk_index=0, content="close chunk")
        orthogonal = self.make_chunk(document, unit_vector(1), chunk_index=1, content="orthogonal chunk")
        opposite = self.make_chunk(document, [-x for x in unit_vector(0)], chunk_index=2, content="opposite chunk")

        results = retrieval.retrieve_relevant_chunks("what is this about?", session_id="sess-1")

        self.assertEqual([r.id for r in results], [close.id, orthogonal.id, opposite.id])

    @patch.object(retrieval, "embed_query")
    def test_document_id_scopes_to_one_document(self, mock_embed_query):
        mock_embed_query.return_value = unit_vector(0)
        document_a = self.make_document()
        document_b = self.make_document()
        chunk_a = self.make_chunk(document_a, unit_vector(0), content="chunk in doc a")
        self.make_chunk(document_b, unit_vector(0), content="chunk in doc b")

        results = retrieval.retrieve_relevant_chunks("query", session_id="sess-1", document_id=document_a.id)

        self.assertEqual([r.id for r in results], [chunk_a.id])

    @patch.object(retrieval, "embed_query")
    def test_chunks_from_non_ready_documents_are_excluded(self, mock_embed_query):
        mock_embed_query.return_value = unit_vector(0)
        ready_document = self.make_document(status_=Document.Status.READY)
        processing_document = self.make_document(status_=Document.Status.PROCESSING)
        ready_chunk = self.make_chunk(ready_document, unit_vector(0), content="ready chunk")
        self.make_chunk(processing_document, unit_vector(0), content="processing chunk")

        results = retrieval.retrieve_relevant_chunks("query", session_id="sess-1")

        self.assertEqual([r.id for r in results], [ready_chunk.id])

    @patch.object(retrieval, "embed_query")
    def test_chunks_are_scoped_to_session(self, mock_embed_query):
        mock_embed_query.return_value = unit_vector(0)
        mine = self.make_document(session_id="mine")
        theirs = self.make_document(session_id="theirs")
        my_chunk = self.make_chunk(mine, unit_vector(0), content="my chunk")
        self.make_chunk(theirs, unit_vector(0), content="their chunk")

        results = retrieval.retrieve_relevant_chunks("query", session_id="mine")

        self.assertEqual([r.id for r in results], [my_chunk.id])


class EmbedChunksBatchingTests(SimpleTestCase):
    @patch.object(embeddings, "_embed_batch")
    def test_texts_are_split_into_batches_of_100(self, mock_embed_batch):
        mock_embed_batch.side_effect = lambda batch: [FAKE_EMBEDDING for _ in batch]
        texts = [f"chunk {i}" for i in range(250)]

        vectors = embeddings.embed_chunks(texts)

        self.assertEqual(mock_embed_batch.call_count, 3)
        batch_sizes = [len(call.args[0]) for call in mock_embed_batch.call_args_list]
        self.assertEqual(batch_sizes, [100, 100, 50])
        self.assertEqual(len(vectors), 250)


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

    def test_list_is_scoped_to_the_requesting_session(self):
        url = reverse("document-upload")
        self.client.post(
            url,
            {"file": SimpleUploadedFile("a.pdf", b"%PDF-1.4 aaa", content_type="application/pdf")},
            format="multipart",
            HTTP_X_SESSION_ID="sess-a",
        )
        self.client.post(
            url,
            {"file": SimpleUploadedFile("b.pdf", b"%PDF-1.4 bbb", content_type="application/pdf")},
            format="multipart",
            HTTP_X_SESSION_ID="sess-b",
        )

        response = self.client.get(url, HTTP_X_SESSION_ID="sess-a")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([doc["original_filename"] for doc in response.data], ["a.pdf"])


def make_fake_embeddings_response(texts):
    response = type("EmbeddingResponse", (), {})()
    response.data = [type("Item", (), {"embedding": list(FAKE_EMBEDDING)})() for _ in texts]
    return response


@override_settings(
    MEDIA_ROOT=MEDIA_ROOT,
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
@patch.object(embeddings.client.embeddings, "create")
class DocumentProcessingTests(APITestCase):
    """
    Runs the task synchronously (no live worker/Redis) against real,
    programmatically generated PDFs to prove extraction + status transitions
    work end to end. This does NOT exercise the real async gap covered by
    the manual polling acceptance check.

    The OpenAI embeddings call is mocked so these tests are free, fast,
    and deterministic — no real network calls or API key required.
    """

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    def upload(self, filename, content):
        pdf = SimpleUploadedFile(filename, content, content_type="application/pdf")
        return self.client.post(reverse("document-upload"), {"file": pdf}, format="multipart")

    def test_text_pdf_reaches_ready_with_correct_page_count(self, mock_create):
        mock_create.side_effect = lambda model, input: make_fake_embeddings_response(input)
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
        self.assertTrue(all(chunk.embedding is not None for chunk in chunks))
        self.assertTrue(all(len(chunk.embedding) == 1536 for chunk in chunks))

    def test_scanned_pdf_fails_with_clear_message(self, mock_create):
        response = self.upload("scanned.pdf", make_blank_pdf_bytes())

        document = Document.objects.get(id=response.data["id"])
        self.assertEqual(document.status, Document.Status.FAILED)
        self.assertIn("scanned", document.error_message)

    def test_zero_page_pdf_fails_with_clear_message(self, mock_create):
        response = self.upload("empty_pages.pdf", make_zero_page_pdf_bytes())

        document = Document.objects.get(id=response.data["id"])
        self.assertEqual(document.status, Document.Status.FAILED)
        self.assertIn("no pages", document.error_message)

    def test_encrypted_pdf_fails_with_clear_message(self, mock_create):
        response = self.upload("encrypted.pdf", make_encrypted_pdf_bytes())

        document = Document.objects.get(id=response.data["id"])
        self.assertEqual(document.status, Document.Status.FAILED)
        self.assertIn("password-protected", document.error_message)

    def test_detail_endpoint_returns_current_status_and_error_message(self, mock_create):
        upload_response = self.upload("scanned.pdf", make_blank_pdf_bytes())

        detail_response = self.client.get(reverse("document-detail", args=[upload_response.data["id"]]))

        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["status"], Document.Status.FAILED)
        self.assertIn("scanned", detail_response.data["error_message"])


class APIDocsTests(APITestCase):
    def test_schema_endpoint_returns_valid_openapi_schema(self):
        response = self.client.get(reverse("schema"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("openapi", response.get("Content-Type", "") + str(response.content[:50]))

    def test_swagger_ui_renders(self):
        response = self.client.get(reverse("swagger-ui"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
