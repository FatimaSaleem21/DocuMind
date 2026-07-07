from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from docuMind.apps.documents.models import Document
from docuMind.apps.documents.validators import validate_pdf_file


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = [
            "id",
            "file",
            "original_filename",
            "status",
            "error_message",
            "page_count",
            "uploaded_at",
        ]
        read_only_fields = ["original_filename", "status", "error_message", "page_count", "uploaded_at"]

    def validate_file(self, value):
        try:
            validate_pdf_file(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message)
        return value

    def create(self, validated_data):
        validated_data["original_filename"] = validated_data["file"].name
        return super().create(validated_data)