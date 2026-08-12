from company_doc_rag.domain.errors import EmptyDocumentError, TransientEmbeddingError
from company_doc_rag.workers.tasks import is_retryable_ingestion_error


def test_일시적_임베딩_오류만_재시도한다() -> None:
    assert is_retryable_ingestion_error(TransientEmbeddingError()) is True
    assert is_retryable_ingestion_error(EmptyDocumentError()) is False

