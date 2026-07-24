from __future__ import annotations

from django.conf import settings
from openai import APIConnectionError, APITimeoutError, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from docuMind.apps.documents.models import DocumentChunk
from docuMind.apps.documents.services.embeddings import client

SYSTEM_PROMPT = """You are a financial document assistant. Answer the question
using only the provided context. If the answer isn't in the context, say so
clearly rather than guessing."""


def build_prompt(question: str, chunks: list[DocumentChunk]) -> str:
    context = "\n\n".join(f"[Source: page {c.page_number}]\n{c.content}" for c in chunks)
    return f"Context:\n{context}\n\nQuestion: {question}"


@retry(
    retry=retry_if_exception_type((RateLimitError, APITimeoutError, APIConnectionError)),
    wait=wait_exponential(multiplier=1, min=1, max=20),
    stop=stop_after_attempt(3),
)
def _create_chat_completion(messages: list[dict]) -> str:
    response = client.chat.completions.create(
        model=settings.CHAT_MODEL, messages=messages, timeout=settings.CHAT_TIMEOUT_SECONDS
    )
    return response.choices[0].message.content


def generate_answer(question: str, chunks: list[DocumentChunk]) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_prompt(question, chunks)},
    ]
    return _create_chat_completion(messages)


@retry(
    retry=retry_if_exception_type((RateLimitError, APITimeoutError, APIConnectionError)),
    wait=wait_exponential(multiplier=1, min=1, max=20),
    stop=stop_after_attempt(3),
)
def _open_chat_stream(messages: list[dict]):
    return client.chat.completions.create(
        model=settings.CHAT_MODEL, messages=messages, stream=True, timeout=settings.CHAT_TIMEOUT_SECONDS
    )


def generate_answer_stream(question: str, chunks: list[DocumentChunk]):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_prompt(question, chunks)},
    ]
    stream = _open_chat_stream(messages)
    for event in stream:
        delta = event.choices[0].delta.content
        if delta:
            yield delta
