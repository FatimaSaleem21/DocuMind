from celery import shared_task
from django.utils import timezone
from pdfminer.pdfdocument import PDFPasswordIncorrect

from docuMind.apps.documents.models import Document, DocumentChunk
from docuMind.apps.documents.services.chunking import chunk_text
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

        chunk_objects = []
        chunk_index = 0
        for page_number, page_text in enumerate(pages, start=1):
            for chunk_content in chunk_text(page_text):
                chunk_objects.append(DocumentChunk(
                    document=doc,
                    content=chunk_content,
                    chunk_index=chunk_index,
                    page_number=page_number,
                ))
                chunk_index += 1
        DocumentChunk.objects.bulk_create(chunk_objects)

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
