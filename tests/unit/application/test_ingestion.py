from pathlib import Path
from uuid import UUID, uuid4

import pytest

from company_doc_rag.application.ingestion import IngestDocument
from company_doc_rag.domain.documents import ChunkDraft, Document, DocumentStatus, PageText
from company_doc_rag.domain.errors import EmptyDocumentError


class 가짜_문서_저장소:
    def __init__(self) -> None:
        self.document = Document(
            id=uuid4(),
            filename="guide.pdf",
            sha256="a" * 64,
            storage_key="document.pdf",
        )

    async def get(self, document_id: UUID) -> Document:
        assert document_id == self.document.id
        return self.document

    async def update_status(
        self,
        document_id: UUID,
        status: DocumentStatus,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        self.document = Document(
            id=document_id,
            filename=self.document.filename,
            sha256=self.document.sha256,
            storage_key=self.document.storage_key,
            status=status,
            error_code=error_code,
            error_message=error_message,
            created_at=self.document.created_at,
        )


class 가짜_청크_저장소:
    def __init__(self) -> None:
        self.replace_count = 0

    async def replace_for_document(self, document_id, drafts, embeddings) -> None:
        self.replace_count += 1


class 가짜_파일_저장소:
    def path_for(self, storage_key: str) -> Path:
        return Path(storage_key)


class 가짜_로더:
    error: Exception | None = None

    def load(self, path: Path) -> list[PageText]:
        if self.error:
            raise self.error
        return [PageText(page_number=1, text="휴가 규정")]


class 가짜_청커:
    def split(self, pages) -> list[ChunkDraft]:
        return [ChunkDraft(index=0, content=pages[0].text, page_start=1, page_end=1, token_count=2)]


class 가짜_임베더:
    async def embed(self, texts) -> list[list[float]]:
        return [[0.1, 0.2] for _ in texts]


def 수집기를_만든다():
    documents = 가짜_문서_저장소()
    chunks = 가짜_청크_저장소()
    loader = 가짜_로더()
    ingest = IngestDocument(
        documents=documents,
        chunks=chunks,
        storage=가짜_파일_저장소(),
        loader=loader,
        chunker=가짜_청커(),
        embedder=가짜_임베더(),
    )
    return ingest, documents, chunks, loader


@pytest.mark.asyncio
async def test_준비된_문서는_다시_수집하지_않는다() -> None:
    ingest, documents, chunks, _ = 수집기를_만든다()

    await ingest.execute(documents.document.id)
    await ingest.execute(documents.document.id)

    assert chunks.replace_count == 1
    assert documents.document.status is DocumentStatus.READY


@pytest.mark.asyncio
async def test_도메인_오류가_발생하면_실패_상태와_코드를_저장한다() -> None:
    ingest, documents, _, loader = 수집기를_만든다()
    loader.error = EmptyDocumentError("본문이 없습니다.")

    with pytest.raises(EmptyDocumentError):
        await ingest.execute(documents.document.id)

    assert documents.document.status is DocumentStatus.FAILED
    assert documents.document.error_code == "EMPTY_DOCUMENT"

