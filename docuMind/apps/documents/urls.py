from django.urls import path

from docuMind.apps.documents.views import DocumentDetailView, DocumentUploadView

urlpatterns = [
    path("documents/", DocumentUploadView.as_view(), name="document-upload"),
    path("documents/<int:pk>/", DocumentDetailView.as_view(), name="document-detail"),
]