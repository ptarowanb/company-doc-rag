from collections.abc import Sequence
from pathlib import Path
from typing import Protocol
from uuid import UUID

from company_doc_rag.domain.documents import ChunkDraft, Document, DocumentStatus, PageText
from company_doc_rag.domain.errors import DomainError
from company_doc_rag.domain.observability import NoOpTracer, Tracer
from company_doc_rag.domain.ports import DocumentLoader, Embedder


class _DocumentRepository(Protocol):
    async def get(self, document_id: UUID) -> Document: ...

    async def update_status(
        self,
        document_id: UUID,
        status: DocumentStatus,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None: ...


class _ChunkRepository(Protocol):
    async def replace_for_document(
        self,
        document_id: UUID,
        drafts: Sequence[ChunkDraft],
        embeddings: Sequence[Sequence[float]],
    ) -> None: ...


class _FileStorage(Protocol):
    def path_for(self, storage_key: str) -> Path: ...


class _Chunker(Protocol):
    def split(self, pages: Sequence[PageText]) -> list[ChunkDraft]: ...


class _CacheGeneration(Protocol):
    async def bump_generation(self) -> int: ...


class IngestDocument:
    """PDF 파싱부터 임베딩 저장까지 문서 수집 상태를 조정한다."""

    def __init__(
        self,
        documents: _DocumentRepository,
        chunks: _ChunkRepository,
        storage: _FileStorage,
        loader: DocumentLoader,
        chunker: _Chunker,
        embedder: Embedder,
        cache: _CacheGeneration | None = None,
        tracer: Tracer | None = None,
    ) -> None:
        self._documents = documents
        self._chunks = chunks
        self._storage = storage
        self._loader = loader
        self._chunker = chunker
        self._embedder = embedder
        self._cache = cache
        self._tracer = tracer or NoOpTracer()

    async def execute(self, document_id: UUID) -> None:
        with self._tracer.trace("document.ingest", {"document_id": str(document_id)}) as span:
            await self._execute(document_id)
            span.set_output({"status": "READY"})

    async def _execute(self, document_id: UUID) -> None:
        document = await self._documents.get(document_id)
        if document.status is DocumentStatus.READY:
            return

        await self._documents.update_status(document_id, DocumentStatus.PROCESSING)
        try:
            pages = self._loader.load(self._storage.path_for(document.storage_key))
            drafts = self._chunker.split(pages)
            embeddings = await self._embedder.embed([draft.content for draft in drafts])
            await self._chunks.replace_for_document(document_id, drafts, embeddings)
        except DomainError as error:
            await self._documents.update_status(
                document_id,
                DocumentStatus.FAILED,
                error_code=error.code,
                error_message=str(error),
            )
            raise
        except Exception:
            await self._documents.update_status(
                document_id,
                DocumentStatus.FAILED,
                error_code="INGESTION_ERROR",
                error_message="문서 처리 중 오류가 발생했습니다.",
            )
            raise
        await self._documents.update_status(document_id, DocumentStatus.READY)
        if self._cache is not None:
            await self._cache.bump_generation()
