from rest_framework.generics import CreateAPIView, RetrieveAPIView
from rest_framework.parsers import MultiPartParser

from docuMind.apps.documents.models import Document
from docuMind.apps.documents.serializers import DocumentSerializer
from docuMind.apps.documents.tasks import process_document


class DocumentUploadView(CreateAPIView):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    parser_classes = [MultiPartParser]

    def perform_create(self, serializer):
        document = serializer.save()
        process_document.delay(document.id)


class DocumentDetailView(RetrieveAPIView):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
