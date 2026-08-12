import hashlib
import json
from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from company_doc_rag.domain.search import SearchHit


class _Redis(Protocol):
    async def get(self, key: str) -> bytes | str | int | None: ...

    async def set(self, key: str, value: str, *, ex: int) -> object: ...

    async def incr(self, key: str) -> int: ...


class SearchCache:
    """문서 세대가 포함된 키로 검색 결과를 짧게 캐시한다."""

    def __init__(
        self,
        client: _Redis,
        ttl_seconds: int = 300,
        namespace: str = "company-doc-rag",
    ) -> None:
        self._client = client
        self._ttl_seconds = ttl_seconds
        self._generation_key = f"{namespace}:document-generation"
        self._namespace = namespace

    async def get(
        self,
        question: str,
        document_ids: Sequence[UUID] | None,
    ) -> list[SearchHit] | None:
        key = await self._key(question, document_ids)
        raw = await self._client.get(key)
        if raw is None:
            return None
        text = raw.decode() if isinstance(raw, bytes) else str(raw)
        values = json.loads(text)
        return [
            SearchHit(
                chunk_id=UUID(value["chunk_id"]),
                document_id=UUID(value["document_id"]),
                filename=value["filename"],
                content=value["content"],
                page_start=value["page_start"],
                page_end=value["page_end"],
                score=value["score"],
                rerank_score=value["rerank_score"],
            )
            for value in values
        ]

    async def set(
        self,
        question: str,
        document_ids: Sequence[UUID] | None,
        hits: Sequence[SearchHit],
    ) -> None:
        key = await self._key(question, document_ids)
        values = [
            {
                "chunk_id": str(hit.chunk_id),
                "document_id": str(hit.document_id),
                "filename": hit.filename,
                "content": hit.content,
                "page_start": hit.page_start,
                "page_end": hit.page_end,
                "score": hit.score,
                "rerank_score": hit.rerank_score,
            }
            for hit in hits
        ]
        await self._client.set(
            key,
            json.dumps(values, ensure_ascii=False),
            ex=self._ttl_seconds,
        )

    async def bump_generation(self) -> int:
        return await self._client.incr(self._generation_key)

    async def _key(self, question: str, document_ids: Sequence[UUID] | None) -> str:
        raw_generation = await self._client.get(self._generation_key)
        generation = int(raw_generation or 0)
        normalized_question = " ".join(question.casefold().split())
        normalized_ids = sorted(str(document_id) for document_id in document_ids or [])
        payload = json.dumps(
            [generation, normalized_question, normalized_ids],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(payload.encode()).hexdigest()
        return f"{self._namespace}:search:{digest}"

