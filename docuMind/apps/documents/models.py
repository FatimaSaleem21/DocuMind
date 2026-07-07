from django.db import models
from pgvector.django import VectorField


class Document(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"
        PROCESSING = "processing"
        READY = "ready"
        FAILED = "failed"

    file = models.FileField(upload_to="documents/")
    original_filename = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    error_message = models.TextField(blank=True, null=True)
    page_count = models.IntegerField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)


class DocumentChunk(models.Model):
    text = models.TextField()
    embedding = VectorField(dimensions=1536)

