from company_doc_rag.domain.observability import NoOpTracer
from company_doc_rag.infrastructure.observability import LangfuseTracer


def test_NoOp_추적기는_애플리케이션_결과를_바꾸지_않는다() -> None:
    with NoOpTracer().trace("query", {"question_hash": "abc"}) as span:
        span.set_output({"source_count": 2})
        result = 42

    assert result == 42


class 실패하는_Langfuse:
    def start_as_current_span(self, *, name: str):
        raise ConnectionError("Langfuse unavailable")


def test_Langfuse_장애를_사용자_흐름으로_전파하지_않는다() -> None:
    tracer = LangfuseTracer(실패하는_Langfuse())

    with tracer.trace("query", {"question_hash": "abc"}):
        result = "정상 답변"

    assert result == "정상 답변"

