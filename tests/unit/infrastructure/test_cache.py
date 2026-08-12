from uuid import UUID

import pytest

from company_doc_rag.domain.search import SearchHit
from company_doc_rag.infrastructure.cache import SearchCache


class 가짜_Redis:
    def __init__(self) -> None:
        self.values: dict[str, str | int] = {}

    async def get(self, key: str):
        return self.values.get(key)

    async def set(self, key: str, value: str, ex: int):
        self.values[key] = value

    async def incr(self, key: str):
        value = int(self.values.get(key, 0)) + 1
        self.values[key] = value
        return value


def 결과() -> SearchHit:
    return SearchHit(
        chunk_id=UUID(int=1),
        document_id=UUID(int=2),
        filename="guide.pdf",
        content="휴가 규정",
        page_start=1,
        page_end=1,
        score=0.1,
        rerank_score=0.9,
    )


@pytest.mark.asyncio
async def test_질문을_정규화해_검색_결과를_재사용한다() -> None:
    cache = SearchCache(가짜_Redis(), ttl_seconds=60)
    await cache.set("  휴가   규정 ", None, [결과()])

    cached = await cache.get("휴가 규정", None)

    assert cached == [결과()]


@pytest.mark.asyncio
async def test_세대를_올리면_이전_검색_결과를_사용하지_않는다() -> None:
    cache = SearchCache(가짜_Redis(), ttl_seconds=60)
    await cache.set("휴가 규정", None, [결과()])

    await cache.bump_generation()

    assert await cache.get("휴가 규정", None) is None

