from celery import shared_task
from django.utils import timezone
from pdfminer.pdfdocument import PDFPasswordIncorrect

from docuMind.apps.documents.models import Document, DocumentChunk
from docuMind.apps.documents.services.chunking import chunk_text
from docuMind.apps.documents.services.embeddings import embed_chunks
from docuMind.apps.documents.services.pdf_extraction import extract_pages


@shared_task
def process_document(document_id):
    doc = Document.objects.get(id=document_id)
    doc.status = Document.Status.PROCESSING
    doc.save(update_fields=["status"])
    try:
        pages = extract_pages(doc.file.path)
        if not pages:
            raise ValueError("PDF has no pages")
        if not any(page.strip() for page in pages):
            raise ValueError("No extractable text — possibly a scanned PDF")
        doc.page_count = len(pages)

        chunk_texts = []
        chunk_pages = []
        for page_number, page_text in enumerate(pages, start=1):
            for chunk_content in chunk_text(page_text):
                chunk_texts.append(chunk_content)
                chunk_pages.append(page_number)

        vectors = embed_chunks(chunk_texts) if chunk_texts else []

        DocumentChunk.objects.bulk_create([
            DocumentChunk(
                document=doc,
                content=text,
                chunk_index=i,
                page_number=chunk_pages[i],
                embedding=vector,
            )
            for i, (text, vector) in enumerate(zip(chunk_texts, vectors))
        ])

        doc.status = Document.Status.READY
        doc.processed_at = timezone.now()
        doc.save(update_fields=["page_count", "status", "processed_at"])
    except PDFPasswordIncorrect:
        doc.status = Document.Status.FAILED
        doc.error_message = "PDF is password-protected"
        doc.save(update_fields=["status", "error_message"])
    except Exception as e:
        doc.status = Document.Status.FAILED
        doc.error_message = str(e)
        doc.save(update_fields=["status", "error_message"])
