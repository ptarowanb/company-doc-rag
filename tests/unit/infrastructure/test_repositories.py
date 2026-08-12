from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from company_doc_rag.domain.documents import ChunkDraft, DocumentStatus
from company_doc_rag.domain.errors import DuplicateDocumentError
from company_doc_rag.infrastructure.models import Base
from company_doc_rag.infrastructure.repositories import ChunkRepository, DocumentRepository


@pytest_asyncio.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    database_engine = create_async_engine("sqlite+aiosqlite://")
    async with database_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield database_engine
    await database_engine.dispose()


@pytest.mark.asyncio
async def test_문서_상태를_변경하고_조회한다(engine: AsyncEngine) -> None:
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    repository = DocumentRepository(sessions)
    document = await repository.create(
        filename="guide.pdf",
        sha256="a" * 64,
        storage_key="document-id.pdf",
    )

    await repository.update_status(document.id, DocumentStatus.READY)

    saved = await repository.get(document.id)
    assert saved.status is DocumentStatus.READY


@pytest.mark.asyncio
async def test_동일한_해시의_문서를_거부한다(engine: AsyncEngine) -> None:
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    repository = DocumentRepository(sessions)
    await repository.create(filename="a.pdf", sha256="a" * 64, storage_key="a.pdf")

    with pytest.raises(DuplicateDocumentError):
        await repository.create(filename="b.pdf", sha256="a" * 64, storage_key="b.pdf")


@pytest.mark.asyncio
async def test_문서의_청크를_원자적으로_교체한다(engine: AsyncEngine) -> None:
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    documents = DocumentRepository(sessions)
    chunks = ChunkRepository(sessions)
    document = await documents.create(filename="a.pdf", sha256="a" * 64, storage_key="a.pdf")
    draft = ChunkDraft(index=0, content="휴가 규정", page_start=3, page_end=3, token_count=2)

    await chunks.replace_for_document(document.id, [draft], [[0.0] * 1536])
    saved = await chunks.list_for_document(document.id)

    assert len(saved) == 1
    assert saved[0].content == "휴가 규정"
    assert saved[0].page_start == 3

