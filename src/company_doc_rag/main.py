from fastapi import FastAPI

from company_doc_rag.api.health import router as health_router
from company_doc_rag.api.query import router as query_router
from company_doc_rag.application.answering import AnswerQuestion
from company_doc_rag.config import Settings, get_settings


def create_app(
    settings: Settings | None = None,
    answer_question: AnswerQuestion | None = None,
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
    app.include_router(health_router)
    app.include_router(query_router)
    return app
