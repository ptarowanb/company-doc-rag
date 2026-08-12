import asyncio
import os
import selectors
from collections.abc import Coroutine
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from company_doc_rag.domain.documents import ChunkDraft, DocumentStatus
from company_doc_rag.infrastructure.repositories import ChunkRepository, DocumentRepository


@pytest.mark.integration
def test_PostgreSQL에_vector_확장이_활성화되어_있다() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL이 설정되지 않아 pgvector 통합 테스트를 건너뜁니다.")
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            )
            assert result.scalar_one() == "vector"
    finally:
        engine.dispose()


def _database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL이 설정되지 않아 pgvector 통합 테스트를 건너뜁니다.")
    return database_url


def _run(coroutine: Coroutine[object, object, None]) -> None:
    def selector_loop() -> asyncio.AbstractEventLoop:
        return asyncio.SelectorEventLoop(selectors.SelectSelector())

    with asyncio.Runner(loop_factory=selector_loop) as runner:
        runner.run(coroutine)


@pytest.mark.integration
def test_실제_PostgreSQL에서_벡터와_키워드로_READY_문서만_검색한다() -> None:
    async def run() -> None:
        engine = create_async_engine(_database_url())
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        documents = DocumentRepository(sessions)
        chunks = ChunkRepository(sessions)
        suffix = uuid4().hex
        ready = await documents.create("ready.pdf", suffix.ljust(64, "a"), f"{suffix}-ready.pdf")
        pending = await documents.create(
            "pending.pdf", suffix[::-1].ljust(64, "b"), f"{suffix}-pending.pdf"
        )
        draft = ChunkDraft(
            index=0,
            content="연차 휴가 규정",
            page_start=1,
            page_end=1,
            token_count=3,
        )
        embedding = [1.0] + [0.0] * 1535
        try:
            await chunks.replace_for_document(ready.id, [draft], [embedding])
            await chunks.replace_for_document(pending.id, [draft], [embedding])
            await documents.update_status(ready.id, DocumentStatus.READY)

            vector_hits = await chunks.vector_search(embedding, limit=10)
            keyword_hits = await chunks.keyword_search("휴가 규정", limit=10)

            assert ready.id in {hit.document_id for hit in vector_hits}
            assert ready.id in {hit.document_id for hit in keyword_hits}
            assert pending.id not in {hit.document_id for hit in vector_hits}
            assert pending.id not in {hit.document_id for hit in keyword_hits}
        finally:
            await documents.delete(ready.id)
            await documents.delete(pending.id)
            await engine.dispose()

    _run(run())


@pytest.mark.integration
def test_동시_청크_교체에도_문서별_인덱스가_중복되지_않는다() -> None:
    async def run() -> None:
        engine = create_async_engine(_database_url())
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        documents = DocumentRepository(sessions)
        chunks = ChunkRepository(sessions)
        suffix = uuid4().hex
        document = await documents.create(
            "concurrent.pdf", suffix.ljust(64, "c"), f"{suffix}-concurrent.pdf"
        )
        draft = ChunkDraft(index=0, content="동시성 검사", page_start=1, page_end=1, token_count=2)
        embedding = [1.0] + [0.0] * 1535
        try:
            await asyncio.gather(
                chunks.replace_for_document(document.id, [draft], [embedding]),
                chunks.replace_for_document(document.id, [draft], [embedding]),
            )

            saved = await chunks.list_for_document(document.id)

            assert [(chunk.index, chunk.content) for chunk in saved] == [(0, "동시성 검사")]
        finally:
            await documents.delete(document.id)
            await engine.dispose()

    _run(run())
