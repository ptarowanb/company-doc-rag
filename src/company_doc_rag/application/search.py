import asyncio
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import replace
from typing import Protocol
from uuid import UUID

from company_doc_rag.domain.ports import Embedder
from company_doc_rag.domain.search import SearchHit


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[SearchHit]],
    k: int = 60,
) -> list[SearchHit]:
    """서로 다른 검색기의 순위를 점수 척도와 무관하게 결합한다."""

    if k < 1:
        raise ValueError("k는 1 이상이어야 합니다.")
    scores: defaultdict[UUID, float] = defaultdict(float)
    hits: dict[UUID, SearchHit] = {}
    for ranking in rankings:
        seen: set[UUID] = set()
        for rank, hit in enumerate(ranking, start=1):
            if hit.chunk_id in seen:
                continue
            seen.add(hit.chunk_id)
            hits.setdefault(hit.chunk_id, hit)
            scores[hit.chunk_id] += 1.0 / (k + rank)
    return sorted(
        (replace(hit, score=scores[chunk_id]) for chunk_id, hit in hits.items()),
        key=lambda hit: hit.score,
        reverse=True,
    )


class _SearchRepository(Protocol):
    async def vector_search(
        self,
        query_embedding: Sequence[float],
        limit: int,
        document_ids: Sequence[UUID] | None = None,
    ) -> list[SearchHit]: ...

    async def keyword_search(
        self,
        query: str,
        limit: int,
        document_ids: Sequence[UUID] | None = None,
    ) -> list[SearchHit]: ...


class Reranker(Protocol):
    """질문과 청크의 관련도를 다시 계산한다."""

    async def rerank(
        self,
        query: str,
        hits: Sequence[SearchHit],
        limit: int,
    ) -> list[SearchHit]: ...


class HybridSearch:
    """벡터·키워드 검색을 결합하고 최종 근거를 재정렬한다."""

    def __init__(
        self,
        embedder: Embedder,
        repository: _SearchRepository,
        reranker: Reranker,
        candidate_limit: int = 20,
        rerank_limit: int = 12,
        final_limit: int = 5,
    ) -> None:
        self._embedder = embedder
        self._repository = repository
        self._reranker = reranker
        self._candidate_limit = candidate_limit
        self._rerank_limit = rerank_limit
        self._final_limit = final_limit

    async def execute(
        self,
        question: str,
        document_ids: Sequence[UUID] | None = None,
    ) -> list[SearchHit]:
        embeddings = await self._embedder.embed([question])
        vector_hits, keyword_hits = await asyncio.gather(
            self._repository.vector_search(
                embeddings[0],
                self._candidate_limit,
                document_ids,
            ),
            self._repository.keyword_search(
                question,
                self._candidate_limit,
                document_ids,
            ),
        )
        fused = reciprocal_rank_fusion([vector_hits, keyword_hits])
        return await self._reranker.rerank(
            question,
            fused[: self._rerank_limit],
            self._final_limit,
        )

