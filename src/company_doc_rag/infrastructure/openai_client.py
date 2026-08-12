import asyncio
from collections.abc import Sequence
from typing import Protocol, cast

from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    InternalServerError,
    RateLimitError,
)

from company_doc_rag.domain.errors import TransientEmbeddingError


class _EmbeddingItem(Protocol):
    embedding: list[float]


class _EmbeddingResponse(Protocol):
    data: list[_EmbeddingItem]


class _EmbeddingsEndpoint(Protocol):
    async def create(
        self,
        *,
        input: Sequence[str],
        model: str,
        dimensions: int,
    ) -> _EmbeddingResponse: ...


class _OpenAIClient(Protocol):
    embeddings: _EmbeddingsEndpoint


class OpenAIEmbedder:
    """문자열을 배치로 나눠 OpenAI 임베딩을 생성한다."""

    def __init__(
        self,
        model: str,
        dimensions: int,
        api_key: str | None = None,
        client: _OpenAIClient | None = None,
        batch_size: int = 100,
    ) -> None:
        if batch_size < 1:
            raise ValueError("batch_size는 1 이상이어야 합니다.")
        self._client = client or cast(_OpenAIClient, AsyncOpenAI(api_key=api_key))
        self._model = model
        self._dimensions = dimensions
        self._batch_size = batch_size

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = list(texts[start : start + self._batch_size])
            response = await self._create_with_retry(batch)
            embeddings.extend(item.embedding for item in response.data)
        return embeddings

    async def _create_with_retry(self, batch: list[str]) -> _EmbeddingResponse:
        transient_errors = (
            APIConnectionError,
            APITimeoutError,
            RateLimitError,
            InternalServerError,
        )
        for attempt in range(3):
            try:
                return await self._client.embeddings.create(
                    input=batch,
                    model=self._model,
                    dimensions=self._dimensions,
                )
            except transient_errors as error:
                if attempt == 2:
                    raise TransientEmbeddingError(
                        "임베딩 API 호출이 반복해서 실패했습니다."
                    ) from error
                await asyncio.sleep(0.2 * (2**attempt))
        raise AssertionError("도달할 수 없는 재시도 상태입니다.")

