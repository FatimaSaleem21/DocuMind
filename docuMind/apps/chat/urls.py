from django.urls import path

from docuMind.apps.chat.views import ChatView

urlpatterns = [
    path("chat/", ChatView.as_view(), name="chat"),
]
