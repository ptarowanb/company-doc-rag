from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from company_doc_rag.domain.documents import (
    ChunkDraft,
    Document,
    DocumentStatus,
    StoredChunk,
)
from company_doc_rag.domain.errors import (
    DocumentNotFoundError,
    DuplicateDocumentError,
)
from company_doc_rag.infrastructure.models import ChunkModel, DocumentModel


def _to_document(model: DocumentModel) -> Document:
    return Document(
        id=model.id,
        filename=model.filename,
        sha256=model.sha256,
        storage_key=model.storage_key,
        status=model.status,
        error_code=model.error_code,
        error_message=model.error_message,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _to_chunk(model: ChunkModel) -> StoredChunk:
    return StoredChunk(
        id=model.id,
        document_id=model.document_id,
        index=model.index,
        content=model.content,
        page_start=model.page_start,
        page_end=model.page_end,
        token_count=model.token_count,
    )


class DocumentRepository:
    """문서 모델을 읽고 쓰는 SQLAlchemy 저장소."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def create(self, filename: str, sha256: str, storage_key: str) -> Document:
        model = DocumentModel(filename=filename, sha256=sha256, storage_key=storage_key)
        async with self._sessions() as session:
            session.add(model)
            try:
                await session.commit()
            except IntegrityError as error:
                await session.rollback()
                raise DuplicateDocumentError("동일한 문서가 이미 등록되어 있습니다.") from error
            await session.refresh(model)
        return _to_document(model)

    async def get(self, document_id: UUID) -> Document:
        async with self._sessions() as session:
            model = await session.get(DocumentModel, document_id)
        if model is None:
            raise DocumentNotFoundError("문서를 찾지 못했습니다.")
        return _to_document(model)

    async def list(self) -> list[Document]:
        async with self._sessions() as session:
            models = (
                await session.scalars(
                    select(DocumentModel).order_by(DocumentModel.created_at.desc())
                )
            ).all()
        return [_to_document(model) for model in models]

    async def update_status(
        self,
        document_id: UUID,
        status: DocumentStatus,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        async with self._sessions() as session:
            model = await session.get(DocumentModel, document_id)
            if model is None:
                raise DocumentNotFoundError("문서를 찾지 못했습니다.")
            model.status = status
            model.error_code = error_code
            model.error_message = error_message
            await session.commit()

    async def delete(self, document_id: UUID) -> None:
        async with self._sessions() as session:
            model = await session.get(DocumentModel, document_id)
            if model is None:
                raise DocumentNotFoundError("문서를 찾지 못했습니다.")
            await session.delete(model)
            await session.commit()


class ChunkRepository:
    """문서 청크와 임베딩을 원자적으로 저장한다."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def replace_for_document(
        self,
        document_id: UUID,
        drafts: Sequence[ChunkDraft],
        embeddings: Sequence[Sequence[float]],
    ) -> None:
        if len(drafts) != len(embeddings):
            raise ValueError("청크 수와 임베딩 수가 일치해야 합니다.")
        async with self._sessions() as session, session.begin():
            await session.execute(delete(ChunkModel).where(ChunkModel.document_id == document_id))
            session.add_all(
                [
                    ChunkModel(
                        document_id=document_id,
                        index=draft.index,
                        content=draft.content,
                        page_start=draft.page_start,
                        page_end=draft.page_end,
                        token_count=draft.token_count,
                        embedding=list(embedding),
                    )
                    for draft, embedding in zip(drafts, embeddings, strict=True)
                ]
            )

    async def list_for_document(self, document_id: UUID) -> list[StoredChunk]:
        statement = (
            select(ChunkModel)
            .where(ChunkModel.document_id == document_id)
            .order_by(ChunkModel.index)
        )
        async with self._sessions() as session:
            models = (await session.scalars(statement)).all()
        return [_to_chunk(model) for model in models]
