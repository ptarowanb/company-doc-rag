import asyncio
from uuid import UUID

from company_doc_rag.bootstrap import build_worker_runtime
from company_doc_rag.config import get_settings
from company_doc_rag.domain.errors import TransientEmbeddingError
from company_doc_rag.workers.celery_app import celery_app


def is_retryable_ingestion_error(error: Exception) -> bool:
    """Celery에서 재시도할 수집 오류인지 판별한다."""

    return isinstance(error, TransientEmbeddingError)


@celery_app.task(  # type: ignore[untyped-decorator]
    name="documents.ingest",
    autoretry_for=(TransientEmbeddingError,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def ingest_document(document_id: str) -> None:
    """문서 하나의 수집 파이프라인을 실행한다."""

    async def run() -> None:
        runtime = build_worker_runtime(get_settings())
        try:
            await runtime.ingest.execute(UUID(document_id))
        finally:
            await runtime.close()

    asyncio.run(run())
