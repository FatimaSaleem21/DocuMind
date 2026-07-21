from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from docuMind.apps.chat.models import ChatMessage
from docuMind.apps.chat.services.rag import generate_answer
from docuMind.apps.documents.services.retrieval import retrieve_relevant_chunks


class ChatView(APIView):
    def post(self, request):
        question = (request.data.get("question") or "").strip()
        if not question:
            return Response({"error": "question is required"}, status=status.HTTP_400_BAD_REQUEST)

        chunks = retrieve_relevant_chunks(question)
        if not chunks:
            return Response({"answer": "No documents have been processed yet."})

        answer = generate_answer(question, chunks)

        ChatMessage.objects.create(role=ChatMessage.Role.USER, content=question)
        assistant_message = ChatMessage.objects.create(role=ChatMessage.Role.ASSISTANT, content=answer)
        assistant_message.source_chunks.set(chunks)

        return Response({"answer": answer, "sources": [c.page_number for c in chunks]})
