import json

from django.db.transaction import non_atomic_requests
from django.http import StreamingHttpResponse
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from docuMind.apps.chat.models import ChatMessage
from docuMind.apps.chat.services.rag import generate_answer, generate_answer_stream
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


@method_decorator(non_atomic_requests, name="dispatch")
class ChatStreamView(APIView):
    def post(self, request):
        question = (request.data.get("question") or "").strip()
        if not question:
            return Response({"error": "question is required"}, status=status.HTTP_400_BAD_REQUEST)

        chunks = retrieve_relevant_chunks(question)

        def event_stream():
            if not chunks:
                yield f"event: token\ndata: {json.dumps({'content': 'No documents have been processed yet.'})}\n\n"
                yield f"event: done\ndata: {json.dumps({'sources': []})}\n\n"
                return

            full_answer = ""
            try:
                for token in generate_answer_stream(question, chunks):
                    full_answer += token
                    yield f"event: token\ndata: {json.dumps({'content': token})}\n\n"
            except Exception as e:
                yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
                return

            sources = [c.page_number for c in chunks]
            ChatMessage.objects.create(role=ChatMessage.Role.USER, content=question)
            assistant_message = ChatMessage.objects.create(role=ChatMessage.Role.ASSISTANT, content=full_answer)
            assistant_message.source_chunks.set(chunks)

            yield f"event: done\ndata: {json.dumps({'sources': sources})}\n\n"

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
