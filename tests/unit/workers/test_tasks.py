from company_doc_rag.domain.errors import TransientEmbeddingError
from company_doc_rag.workers.tasks import ingest_document


def test_일시적_임베딩_오류만_재시도한다() -> None:
    assert ingest_document.autoretry_for == (TransientEmbeddingError,)
    assert ingest_document.retry_kwargs == {"max_retries": 3}
    assert ingest_document.retry_backoff is True
    assert ingest_document.retry_jitter is True

