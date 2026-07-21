from django.contrib import admin

from docuMind.apps.chat.models import ChatMessage


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "role", "created_at")
