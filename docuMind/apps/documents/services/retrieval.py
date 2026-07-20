from __future__ import annotations

from pgvector.django import CosineDistance

from docuMind.apps.documents.models import Document, DocumentChunk
from docuMind.apps.documents.services.embeddings import embed_query


def retrieve_relevant_chunks(query: str, document_id: int | None = None, top_k: int = 5) -> list[DocumentChunk]:
    query_embedding = embed_query(query)

    queryset = DocumentChunk.objects.filter(document__status=Document.Status.READY)
    if document_id is not None:
        queryset = queryset.filter(document_id=document_id)

    return list(
        queryset
        .annotate(distance=CosineDistance("embedding", query_embedding))
        .order_by("distance")[:top_k]
    )
