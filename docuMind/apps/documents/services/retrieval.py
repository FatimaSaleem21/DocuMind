from __future__ import annotations

from pgvector.django import CosineDistance

from docuMind.apps.documents.models import Document, DocumentChunk
from docuMind.apps.documents.services.embeddings import embed_query


def retrieve_relevant_chunks(
    query: str, session_id: str, document_id: int | None = None, top_k: int = 5
) -> list[DocumentChunk]:
    query_embedding = embed_query(query)

    # Scope to the caller's own documents so one visitor never retrieves
    # another's uploaded content.
    queryset = DocumentChunk.objects.filter(
        document__status=Document.Status.READY,
        document__session_id=session_id,
    )
    if document_id is not None:
        queryset = queryset.filter(document_id=document_id)

    return list(
        queryset
        .annotate(distance=CosineDistance("embedding", query_embedding))
        .order_by("distance")[:top_k]
    )
