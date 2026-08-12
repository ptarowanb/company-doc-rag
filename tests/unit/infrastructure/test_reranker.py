from uuid import UUID

import pytest

from company_doc_rag.domain.search import SearchHit
from company_doc_rag.infrastructure.reranker import CrossEncoderReranker


class 가짜_CrossEncoder:
    def predict(self, pairs):
        assert pairs == [["질문", "첫 번째"], ["질문", "두 번째"]]
        return [0.1, 0.9]


def 검색_결과(chunk_id: int, content: str) -> SearchHit:
    return SearchHit(
        chunk_id=UUID(int=chunk_id),
        document_id=UUID(int=100),
        filename="guide.pdf",
        content=content,
        page_start=1,
        page_end=1,
        score=0.01,
    )


@pytest.mark.asyncio
async def test_CrossEncoder_점수로_검색_결과를_재정렬한다() -> None:
    reranker = CrossEncoderReranker(model=가짜_CrossEncoder())
    hits = [검색_결과(1, "첫 번째"), 검색_결과(2, "두 번째")]

    results = await reranker.rerank("질문", hits, limit=2)

    assert [result.chunk_id for result in results] == [UUID(int=2), UUID(int=1)]
    assert results[0].rerank_score == 0.9

