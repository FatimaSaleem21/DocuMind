from django.contrib import admin

from docuMind.apps.documents.models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "original_filename", "status", "uploaded_at")
    list_filter = ("status",)
