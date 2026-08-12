from fastapi import FastAPI

from company_doc_rag.api.documents import router as documents_router
from company_doc_rag.api.errors import domain_error_handler
from company_doc_rag.api.health import router as health_router
from company_doc_rag.api.query import router as query_router
from company_doc_rag.application.answering import AnswerQuestion
from company_doc_rag.application.documents import DocumentService
from company_doc_rag.config import Settings, get_settings
from company_doc_rag.domain.errors import DomainError


def create_app(
    settings: Settings | None = None,
    answer_question: AnswerQuestion | None = None,
    document_service: DocumentService | None = None,
) -> FastAPI:
    """의존성을 조립해 FastAPI 애플리케이션을 생성한다."""

    resolved_settings = settings or get_settings()
    app = FastAPI(
        title="사내 문서 AI 검색 API",
        version="0.1.0",
        description="한국어 사내 문서를 검색하고 근거와 함께 답변합니다.",
    )
    app.state.settings = resolved_settings
    app.state.answer_question = answer_question
    app.state.document_service = document_service
    app.add_exception_handler(DomainError, domain_error_handler)
    app.include_router(health_router)
    app.include_router(documents_router)
    app.include_router(query_router)
    return app


def create_runtime_app() -> FastAPI:
    """실제 인프라 어댑터를 조립한 API 애플리케이션을 생성한다."""

    from company_doc_rag.bootstrap import build_application_runtime

    settings = get_settings()
    runtime = build_application_runtime(settings)
    app = create_app(settings, runtime.answer_question, runtime.documents)
    app.state.runtime = runtime
    app.router.add_event_handler("shutdown", runtime.close)
    return app
