from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

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


class ChatViewTests(APITestCase):
    def post_question(self, question):
        return self.client.post(reverse("chat"), {"question": question}, format="json")

    def test_empty_question_is_rejected(self):
        response = self.post_question("")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertEqual(ChatMessage.objects.count(), 0)

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
