import json
from unittest.mock import patch

import httpx
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from openai import RateLimitError
from rest_framework import status
from rest_framework.test import APITestCase
from tenacity import RetryError

from docuMind.apps.chat import ratelimit, views
from docuMind.apps.chat.models import ChatMessage
from docuMind.apps.chat.services import rag
from docuMind.apps.documents.models import Document, DocumentChunk
from docuMind.apps.documents.services import retrieval

FAKE_ANSWER = "The late fee is $35 if payment is received after the due date."


def unit_vector(axis: int) -> list[float]:
    vector = [0.0] * 1536
    vector[axis] = 1.0
    return vector


def make_fake_chat_completion(content):
    message = type("Message", (), {"content": content})()
    choice = type("Choice", (), {"message": message})()
    response = type("Response", (), {"choices": [choice]})()
    return response


def make_fake_stream(tokens):
    def _chunk(token):
        delta = type("Delta", (), {"content": token})()
        choice = type("Choice", (), {"delta": delta})()
        return type("Chunk", (), {"choices": [choice]})()

    return [_chunk(t) for t in tokens]


def make_fake_stream_that_errors(tokens_before_error):
    def _generator():
        for t in tokens_before_error:
            delta = type("Delta", (), {"content": t})()
            choice = type("Choice", (), {"delta": delta})()
            yield type("Chunk", (), {"choices": [choice]})()
        raise ConnectionError("stream dropped")

    return _generator()


def parse_sse(body: str):
    events = []
    for frame in body.strip().split("\n\n"):
        if not frame:
            continue
        lines = frame.split("\n")
        event_line = next(line for line in lines if line.startswith("event: "))
        data_line = next(line for line in lines if line.startswith("data: "))
        events.append((event_line[len("event: "):], json.loads(data_line[len("data: "):])))
    return events


class ChatViewTests(APITestCase):
    def post_question(self, question):
        return self.client.post(reverse("chat"), {"question": question}, format="json")

    def test_empty_question_is_rejected(self):
        response = self.post_question("")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("question", response.data)
        self.assertEqual(ChatMessage.objects.count(), 0)

    def test_question_over_max_length_is_rejected(self):
        response = self.post_question("a" * 2001)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("question", response.data)

    def test_missing_question_is_rejected(self):
        response = self.client.post(reverse("chat"), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch.object(rag.client.chat.completions, "create")
    @patch.object(retrieval, "embed_query")
    def test_no_ready_documents_returns_fallback_without_calling_llm(self, mock_embed_query, mock_create):
        mock_embed_query.return_value = unit_vector(0)

        response = self.post_question("What is the late fee?")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["answer"], "No documents have been processed yet.")
        mock_create.assert_not_called()
        self.assertEqual(ChatMessage.objects.count(), 0)

    @patch.object(rag.client.chat.completions, "create")
    @patch.object(retrieval, "embed_query")
    def test_grounded_answer_is_returned_and_persisted(self, mock_embed_query, mock_create):
        mock_embed_query.return_value = unit_vector(0)
        mock_create.return_value = make_fake_chat_completion(FAKE_ANSWER)

        document = Document.objects.create(
            original_filename="statement.pdf",
            status=Document.Status.READY,
            page_count=1,
        )
        chunk = DocumentChunk.objects.create(
            document=document,
            content="A late fee of $35 will be charged for late payments.",
            chunk_index=0,
            page_number=2,
            embedding=unit_vector(0),
        )

        response = self.post_question("What is the late fee?")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["answer"], FAKE_ANSWER)
        self.assertEqual(response.data["sources"], [2])

        self.assertEqual(ChatMessage.objects.count(), 2)
        user_message, assistant_message = ChatMessage.objects.order_by("created_at")
        self.assertEqual(user_message.role, ChatMessage.Role.USER)
        self.assertEqual(user_message.content, "What is the late fee?")
        self.assertEqual(assistant_message.role, ChatMessage.Role.ASSISTANT)
        self.assertEqual(assistant_message.content, FAKE_ANSWER)
        self.assertEqual(list(assistant_message.source_chunks.all()), [chunk])

    @patch.object(retrieval, "embed_query")
    def test_retrieval_failure_returns_clean_error_not_500(self, mock_embed_query):
        mock_embed_query.side_effect = RuntimeError("embedding service unreachable")

        response = self.post_question("What is the late fee?")

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("error", response.data)
        self.assertNotIn("embedding service unreachable", response.data["error"])
        self.assertEqual(ChatMessage.objects.count(), 0)


class ChatStreamViewTests(APITestCase):
    def post_question(self, question):
        return self.client.post(reverse("chat-stream"), {"question": question}, format="json")

    def test_empty_question_is_rejected_without_streaming(self):
        response = self.post_question("")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("question", response.data)
        self.assertNotEqual(response.get("Content-Type"), "text/event-stream")

    @patch.object(rag.client.chat.completions, "create")
    @patch.object(retrieval, "embed_query")
    def test_no_ready_documents_streams_fallback_without_calling_llm(self, mock_embed_query, mock_create):
        mock_embed_query.return_value = unit_vector(0)

        response = self.post_question("What is the late fee?")
        body = b"".join(response.streaming_content).decode()
        events = parse_sse(body)

        self.assertEqual(response["Content-Type"], "text/event-stream")
        self.assertEqual(events[0], ("token", {"content": "No documents have been processed yet."}))
        self.assertEqual(events[-1], ("done", {"sources": []}))
        mock_create.assert_not_called()
        self.assertEqual(ChatMessage.objects.count(), 0)

    @patch.object(rag.client.chat.completions, "create")
    @patch.object(retrieval, "embed_query")
    def test_grounded_answer_streams_tokens_and_persists(self, mock_embed_query, mock_create):
        mock_embed_query.return_value = unit_vector(0)
        mock_create.return_value = make_fake_stream(["The ", "late ", "fee is $35."])

        document = Document.objects.create(
            original_filename="statement.pdf",
            status=Document.Status.READY,
            page_count=1,
        )
        chunk = DocumentChunk.objects.create(
            document=document,
            content="A late fee of $35 will be charged for late payments.",
            chunk_index=0,
            page_number=2,
            embedding=unit_vector(0),
        )

        response = self.post_question("What is the late fee?")
        body = b"".join(response.streaming_content).decode()
        events = parse_sse(body)

        token_events = [e for e in events if e[0] == "token"]
        self.assertEqual([e[1]["content"] for e in token_events], ["The ", "late ", "fee is $35."])
        self.assertEqual(events[-1], ("done", {"sources": [2]}))

        self.assertEqual(ChatMessage.objects.count(), 2)
        user_message, assistant_message = ChatMessage.objects.order_by("created_at")
        self.assertEqual(user_message.content, "What is the late fee?")
        self.assertEqual(assistant_message.content, "The late fee is $35.")
        self.assertEqual(list(assistant_message.source_chunks.all()), [chunk])

    @patch.object(rag.client.chat.completions, "create")
    @patch.object(retrieval, "embed_query")
    def test_mid_stream_error_yields_error_event_without_persisting(self, mock_embed_query, mock_create):
        mock_embed_query.return_value = unit_vector(0)
        mock_create.return_value = make_fake_stream_that_errors(["partial "])

        document = Document.objects.create(
            original_filename="statement.pdf",
            status=Document.Status.READY,
            page_count=1,
        )
        DocumentChunk.objects.create(
            document=document,
            content="A late fee of $35 will be charged for late payments.",
            chunk_index=0,
            page_number=2,
            embedding=unit_vector(0),
        )

        response = self.post_question("What is the late fee?")
        body = b"".join(response.streaming_content).decode()
        events = parse_sse(body)

        self.assertEqual(events[0], ("token", {"content": "partial "}))
        self.assertEqual(events[-1][0], "error")
        self.assertEqual(ChatMessage.objects.count(), 0)

    @patch.object(retrieval, "embed_query")
    def test_retrieval_failure_yields_error_event_not_500(self, mock_embed_query):
        mock_embed_query.side_effect = RuntimeError("embedding service unreachable")

        response = self.post_question("What is the late fee?")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/event-stream")

        body = b"".join(response.streaming_content).decode()
        events = parse_sse(body)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0][0], "error")
        self.assertNotIn("embedding service unreachable", events[0][1]["message"])
        self.assertEqual(ChatMessage.objects.count(), 0)


def make_rate_limit_error():
    response = httpx.Response(
        status_code=429,
        request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
    )
    return RateLimitError("rate limited", response=response, body=None)


class ChatResilienceTests(TestCase):
    @patch("time.sleep")
    @patch.object(rag.client.chat.completions, "create")
    def test_transient_error_is_retried_and_eventually_raises(self, mock_create, mock_sleep):
        mock_create.side_effect = make_rate_limit_error()

        with self.assertRaises(RetryError):
            rag._create_chat_completion([{"role": "user", "content": "hi"}])

        self.assertEqual(mock_create.call_count, 3)

    @patch("time.sleep")
    @patch.object(rag.client.chat.completions, "create")
    def test_transient_error_on_stream_open_is_retried(self, mock_create, mock_sleep):
        mock_create.side_effect = make_rate_limit_error()

        with self.assertRaises(RetryError):
            rag._open_chat_stream([{"role": "user", "content": "hi"}])

        self.assertEqual(mock_create.call_count, 3)


class ChatStreamRateLimitTests(APITestCase):
    def post_question(self, question):
        return self.client.post(reverse("chat-stream"), {"question": question}, format="json")

    @patch.object(views, "over_daily_limit", return_value=True)
    def test_over_daily_limit_returns_429_without_streaming(self, mock_limit):
        response = self.post_question("What is the late fee?")

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertNotEqual(response.get("Content-Type"), "text/event-stream")
        self.assertIn("detail", response.data)
        mock_limit.assert_called_once()


class FakeRedis:
    """Minimal in-memory stand-in for the counter operations the limiter uses."""

    def __init__(self):
        self.counts = {}
        self.expiries = {}

    def incr(self, key):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    def expire(self, key, ttl):
        self.expiries[key] = ttl


class DailyLimitCounterTests(TestCase):
    def _request(self, ip="1.2.3.4"):
        request = RequestFactory().post("/api/chat/stream/")
        request.META["HTTP_X_FORWARDED_FOR"] = f"{ip}, 10.0.0.1"
        return request

    def test_client_ip_uses_first_forwarded_address(self):
        self.assertEqual(ratelimit.client_ip(self._request("203.0.113.9")), "203.0.113.9")

    @override_settings(CHAT_DAILY_IP_LIMIT=3)
    def test_blocks_once_the_limit_is_exceeded(self):
        fake = FakeRedis()
        with patch.object(ratelimit.redis.Redis, "from_url", return_value=fake):
            results = [ratelimit.over_daily_limit(self._request()) for _ in range(4)]

        self.assertEqual(results, [False, False, False, True])
        # TTL is set exactly once, on the first request of the day.
        self.assertEqual(len(fake.expiries), 1)
        self.assertEqual(next(iter(fake.expiries.values())), ratelimit.SECONDS_PER_DAY)

    @override_settings(CHAT_DAILY_IP_LIMIT=0)
    def test_disabled_when_limit_non_positive(self):
        with patch.object(ratelimit.redis.Redis, "from_url") as mock_from_url:
            self.assertFalse(ratelimit.over_daily_limit(self._request()))
            mock_from_url.assert_not_called()

    @override_settings(CHAT_DAILY_IP_LIMIT=5)
    def test_fails_open_when_redis_unreachable(self):
        with patch.object(ratelimit.redis.Redis, "from_url", side_effect=ratelimit.redis.RedisError("down")):
            self.assertFalse(ratelimit.over_daily_limit(self._request()))


class BuildPromptTests(TestCase):
    def test_prompt_includes_context_and_question(self):
        document = Document.objects.create(original_filename="doc.pdf", status=Document.Status.READY)
        chunk = DocumentChunk.objects.create(
            document=document,
            content="Late fees are $35.",
            chunk_index=0,
            page_number=2,
        )

        prompt = rag.build_prompt("What is the late fee?", [chunk])

        self.assertIn("[Source: page 2]", prompt)
        self.assertIn("Late fees are $35.", prompt)
        self.assertIn("Question: What is the late fee?", prompt)
