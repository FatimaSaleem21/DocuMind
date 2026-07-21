from django.db import models

from docuMind.apps.documents.models import DocumentChunk


class ChatMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user"
        ASSISTANT = "assistant"

    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()
    source_chunks = models.ManyToManyField(DocumentChunk, related_name="chat_messages", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
