import json

from django.db.transaction import non_atomic_requests
from django.http import StreamingHttpResponse
from django.utils.decorators import method_decorator
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from docuMind.apps.chat.models import ChatMessage
from docuMind.apps.chat.serializers import ChatRequestSerializer, ChatResponseSerializer
from docuMind.apps.chat.services.rag import generate_answer, generate_answer_stream
from docuMind.apps.documents.services.retrieval import retrieve_relevant_chunks


@extend_schema(
    request=ChatRequestSerializer,
    responses=ChatResponseSerializer,
    examples=[
        OpenApiExample(
            "Grounded answer",
            value={"answer": "The late fee is $35 if payment is received after the due date.", "sources": [2]},
            response_only=True,
        ),
    ],
    description="Ask a question about your uploaded documents and get a single, complete answer.",
)
class ChatView(APIView):
    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        question = serializer.validated_data["question"]

        chunks = retrieve_relevant_chunks(question)
        if not chunks:
            return Response({"answer": "No documents have been processed yet."})

        answer = generate_answer(question, chunks)

        ChatMessage.objects.create(role=ChatMessage.Role.USER, content=question)
        assistant_message = ChatMessage.objects.create(role=ChatMessage.Role.ASSISTANT, content=answer)
        assistant_message.source_chunks.set(chunks)

        return Response({"answer": answer, "sources": [c.page_number for c in chunks]})


@extend_schema(
    request=ChatRequestSerializer,
    responses={200: OpenApiTypes.STR},
    description=(
        "Streams a grounded answer via Server-Sent Events. "
        "Emits `token` events with `{content}`, then a final `done` event "
        "with `{sources: [page_number, ...]}`, or an `error` event on failure."
    ),
)
@method_decorator(non_atomic_requests, name="dispatch")
class ChatStreamView(APIView):
    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        question = serializer.validated_data["question"]

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
