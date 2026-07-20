from django.conf import settings
from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

client = OpenAI(api_key=settings.OPENAI_API_KEY)

BATCH_SIZE = 100


@retry(
    retry=retry_if_exception_type((RateLimitError, APITimeoutError, APIConnectionError)),
    wait=wait_exponential(multiplier=1, min=1, max=20),
    stop=stop_after_attempt(3),
)
def _embed_batch(texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(model=settings.EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]


def embed_chunks(texts: list[str]) -> list[list[float]]:
    vectors = []
    for i in range(0, len(texts), BATCH_SIZE):
        vectors.extend(_embed_batch(texts[i:i + BATCH_SIZE]))
    return vectors


def embed_query(text: str) -> list[float]:
    return embed_chunks([text])[0]
