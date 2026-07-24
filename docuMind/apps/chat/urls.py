from django.urls import path

from docuMind.apps.chat.views import ChatStreamView, ChatView

urlpatterns = [
    path("chat/", ChatView.as_view(), name="chat"),
    path("chat/stream/", ChatStreamView.as_view(), name="chat-stream"),
]
