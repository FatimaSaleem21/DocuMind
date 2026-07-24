from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView
from rest_framework.parsers import MultiPartParser

from docuMind.apps.documents.models import Document
from docuMind.apps.documents.serializers import DocumentSerializer
from docuMind.apps.documents.tasks import process_document

DOCUMENT_EXAMPLE = {
    "id": 1,
    "file": "/media/documents/statement.pdf",
    "original_filename": "statement.pdf",
    "status": "pending",
    "error_message": None,
    "page_count": None,
    "uploaded_at": "2026-07-08T12:00:00Z",
}


@extend_schema_view(
    get=extend_schema(
        description="List all uploaded documents, newest first.",
        examples=[OpenApiExample("Document list", value=[DOCUMENT_EXAMPLE], response_only=True)],
    ),
    post=extend_schema(
        description="Upload a PDF for processing (extraction, chunking, embedding).",
        examples=[OpenApiExample("Uploaded document", value=DOCUMENT_EXAMPLE, response_only=True)],
    ),
)
class DocumentUploadView(ListCreateAPIView):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    parser_classes = [MultiPartParser]

    def perform_create(self, serializer):
        document = serializer.save()
        process_document.delay(document.id)


@extend_schema(
    description="Retrieve a single document's current processing status.",
    examples=[OpenApiExample("Document detail", value=DOCUMENT_EXAMPLE, response_only=True)],
)
class DocumentDetailView(RetrieveAPIView):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
