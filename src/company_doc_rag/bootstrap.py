from dataclasses import dataclass
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine

from company_doc_rag.application.answering import AnswerQuestion
from company_doc_rag.application.chunking import TokenChunker
from company_doc_rag.application.documents import DocumentService
from company_doc_rag.application.ingestion import IngestDocument
from company_doc_rag.application.search import HybridSearch
from company_doc_rag.config import Settings
from company_doc_rag.infrastructure.cache import SearchCache
from company_doc_rag.infrastructure.database import create_database
from company_doc_rag.infrastructure.file_storage import LocalFileStorage
from company_doc_rag.infrastructure.observability import create_tracer
from company_doc_rag.infrastructure.openai_client import OpenAIAnswerGenerator, OpenAIEmbedder
from company_doc_rag.infrastructure.pdf_loader import PdfLoader
from company_doc_rag.infrastructure.repositories import ChunkRepository, DocumentRepository
from company_doc_rag.infrastructure.reranker import CrossEncoderReranker

SharedComponents = tuple[
    AsyncEngine,
    Redis,
    SearchCache,
    DocumentRepository,
    ChunkRepository,
    LocalFileStorage,
    OpenAIEmbedder,
]


class CeleryDocumentQueue:
    """문서 ID를 Celery 수집 큐에 등록한다."""

    def enqueue(self, document_id: UUID) -> None:
        from company_doc_rag.workers.tasks import ingest_document

        ingest_document.delay(str(document_id))


@dataclass(slots=True)
class ApplicationRuntime:
    """API 프로세스가 공유하는 서비스와 연결 자원."""

    engine: AsyncEngine
    redis: Redis
    documents: DocumentService
    answer_question: AnswerQuestion

    async def close(self) -> None:
        await self.redis.aclose()
        await self.engine.dispose()


@dataclass(slots=True)
class WorkerRuntime:
    """문서 작업자가 한 작업 동안 사용하는 자원."""

    engine: AsyncEngine
    redis: Redis
    ingest: IngestDocument

    async def close(self) -> None:
        await self.redis.aclose()
        await self.engine.dispose()


def _shared_components(settings: Settings) -> SharedComponents:
    engine, sessions = create_database(settings.database_url)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    cache = SearchCache(redis)
    documents = DocumentRepository(sessions)
    chunks = ChunkRepository(sessions)
    storage = LocalFileStorage(settings.upload_dir)
    embedder = OpenAIEmbedder(
        api_key=settings.openai_api_key.get_secret_value(),
        model=settings.openai_embedding_model,
        dimensions=settings.openai_embedding_dimensions,
    )
    return engine, redis, cache, documents, chunks, storage, embedder


def build_application_runtime(settings: Settings) -> ApplicationRuntime:
    engine, redis, cache, documents, chunks, storage, embedder = _shared_components(settings)
    tracer = create_tracer(
        settings.langfuse_public_key.get_secret_value() if settings.langfuse_public_key else None,
        settings.langfuse_secret_key.get_secret_value() if settings.langfuse_secret_key else None,
        settings.langfuse_host,
    )
    search = HybridSearch(
        embedder=embedder,
        repository=chunks,
        reranker=CrossEncoderReranker(),
        cache=cache,
        tracer=tracer,
    )
    answer_question = AnswerQuestion(
        search=search,
        generator=OpenAIAnswerGenerator(
            api_key=settings.openai_api_key.get_secret_value(),
            model=settings.openai_chat_model,
        ),
        tracer=tracer,
    )
    document_service = DocumentService(
        repository=documents,
        storage=storage,
        queue=CeleryDocumentQueue(),
        cache=cache,
        max_upload_bytes=settings.max_upload_bytes,
    )
    return ApplicationRuntime(engine, redis, document_service, answer_question)


def build_worker_runtime(settings: Settings) -> WorkerRuntime:
    engine, redis, cache, documents, chunks, storage, embedder = _shared_components(settings)
    tracer = create_tracer(
        settings.langfuse_public_key.get_secret_value() if settings.langfuse_public_key else None,
        settings.langfuse_secret_key.get_secret_value() if settings.langfuse_secret_key else None,
        settings.langfuse_host,
    )
    ingest = IngestDocument(
        documents=documents,
        chunks=chunks,
        storage=storage,
        loader=PdfLoader(),
        chunker=TokenChunker(),
        embedder=embedder,
        cache=cache,
        tracer=tracer,
    )
    return WorkerRuntime(engine, redis, ingest)
