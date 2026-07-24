import json
import logging

from django.db.transaction import non_atomic_requests
from django.http import StreamingHttpResponse
from django.utils.decorators import method_decorator
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from docuMind.apps.chat.models import ChatMessage
from docuMind.apps.chat.ratelimit import over_daily_limit
from docuMind.apps.chat.serializers import ChatRequestSerializer, ChatResponseSerializer
from docuMind.apps.chat.services.rag import generate_answer, generate_answer_stream
from docuMind.apps.documents.services.retrieval import retrieve_relevant_chunks
from docuMind.apps.documents.session import session_id_from_request

logger = logging.getLogger(__name__)

GENERIC_RETRIEVAL_ERROR = "We're having trouble searching your documents right now. Please try again shortly."
GENERIC_ANSWER_ERROR = "We're having trouble generating an answer right now. Please try again shortly."


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

        try:
            chunks = retrieve_relevant_chunks(question, session_id=session_id_from_request(request))
        except Exception:
            logger.exception("Failed to retrieve chunks for chat question")
            return Response({"error": GENERIC_RETRIEVAL_ERROR}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

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

        # Per-IP daily cap to protect the OpenAI bill on a public demo. Returned
        # as a plain JSON 429 (not an SSE event) so the frontend's non-OK branch
        # renders it as a normal error before it starts reading the stream.
        if over_daily_limit(request):
            return Response(
                {"detail": "Daily request limit reached. Please try again tomorrow."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        try:
            chunks = retrieve_relevant_chunks(question, session_id=session_id_from_request(request))
            retrieval_failed = False
        except Exception:
            logger.exception("Failed to retrieve chunks for chat question")
            chunks = None
            retrieval_failed = True

        def event_stream():
            if retrieval_failed:
                yield f"event: error\ndata: {json.dumps({'message': GENERIC_RETRIEVAL_ERROR})}\n\n"
                return

            if not chunks:
                yield f"event: token\ndata: {json.dumps({'content': 'No documents have been processed yet.'})}\n\n"
                yield f"event: done\ndata: {json.dumps({'sources': []})}\n\n"
                return

            full_answer = ""
            try:
                for token in generate_answer_stream(question, chunks):
                    full_answer += token
                    yield f"event: token\ndata: {json.dumps({'content': token})}\n\n"
            except Exception:
                logger.exception("Failed to generate answer for chat question")
                yield f"event: error\ndata: {json.dumps({'message': GENERIC_ANSWER_ERROR})}\n\n"
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
