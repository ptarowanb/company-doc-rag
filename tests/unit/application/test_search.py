from uuid import UUID

import pytest

from company_doc_rag.application.search import HybridSearch, reciprocal_rank_fusion
from company_doc_rag.domain.search import SearchHit

A = UUID(int=1)
B = UUID(int=2)
C = UUID(int=3)


def 검색_결과(chunk_id: UUID, score: float = 1.0) -> SearchHit:
    return SearchHit(
        chunk_id=chunk_id,
        document_id=UUID(int=100),
        filename="guide.pdf",
        content=f"내용 {chunk_id.int}",
        page_start=1,
        page_end=1,
        score=score,
    )


def test_두_검색기에_모두_등장한_청크의_RRF_순위가_높다() -> None:
    vector = [검색_결과(A), 검색_결과(B)]
    keyword = [검색_결과(B), 검색_결과(C)]

    fused = reciprocal_rank_fusion([vector, keyword], k=60)

    assert fused[0].chunk_id == B
    assert len(fused) == 3


class 가짜_임베더:
    async def embed(self, texts):
        assert texts == ["휴가 규정"]
        return [[0.1, 0.2]]


class 가짜_검색_저장소:
    async def vector_search(self, query_embedding, limit, document_ids=None):
        assert query_embedding == [0.1, 0.2]
        return [검색_결과(A), 검색_결과(B)]

    async def keyword_search(self, query, limit, document_ids=None):
        assert query == "휴가 규정"
        return [검색_결과(B), 검색_결과(C)]


class 가짜_reranker:
    def __init__(self) -> None:
        self.received: list[SearchHit] = []

    async def rerank(self, query, hits, limit):
        self.received = list(hits)
        return list(hits)[:limit]


@pytest.mark.asyncio
async def test_벡터와_키워드_후보를_결합한_뒤_reranker에_전달한다() -> None:
    reranker = 가짜_reranker()
    search = HybridSearch(
        embedder=가짜_임베더(),
        repository=가짜_검색_저장소(),
        reranker=reranker,
        candidate_limit=20,
        rerank_limit=12,
        final_limit=2,
    )

    results = await search.execute("휴가 규정")

    assert reranker.received[0].chunk_id == B
    assert len(results) == 2

