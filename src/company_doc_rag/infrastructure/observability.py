from collections.abc import Callable, Iterator, Mapping
from contextlib import AbstractContextManager, contextmanager
from importlib import import_module
from types import TracebackType
from typing import Protocol, cast

from company_doc_rag.domain.observability import NoOpSpan, NoOpTracer, Span, Tracer


class _LangfuseSpan(Protocol):
    def update(self, **kwargs: object) -> object: ...


class _LangfuseClient(Protocol):
    def start_as_current_span(
        self,
        *,
        name: str,
    ) -> AbstractContextManager[_LangfuseSpan]: ...


class _SafeSpan:
    def __init__(self, span: _LangfuseSpan) -> None:
        self._span = span

    def set_output(self, output: Mapping[str, object]) -> None:
        try:
            self._span.update(output=dict(output))
        except Exception:
            return None


class LangfuseTracer:
    """Langfuse SDK 장애를 격리하는 추적 어댑터."""

    def __init__(self, client: _LangfuseClient) -> None:
        self._client = client

    @contextmanager
    def trace(self, name: str, metadata: Mapping[str, object]) -> Iterator[Span]:
        try:
            context = self._client.start_as_current_span(name=name)
            raw_span = context.__enter__()
        except Exception:
            yield NoOpSpan()
            return

        try:
            try:
                raw_span.update(metadata=dict(metadata))
            except Exception:
                pass
            yield _SafeSpan(raw_span)
        except BaseException as error:
            self._safe_exit(context, type(error), error, error.__traceback__)
            raise
        else:
            self._safe_exit(context, None, None, None)

    @staticmethod
    def _safe_exit(
        context: AbstractContextManager[_LangfuseSpan],
        error_type: type[BaseException] | None,
        error: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            context.__exit__(error_type, error, traceback)
        except Exception:
            return None


def create_tracer(
    public_key: str | None,
    secret_key: str | None,
    host: str | None,
) -> Tracer:
    """키가 모두 있을 때만 Langfuse를 활성화한다."""

    if not public_key or not secret_key:
        return NoOpTracer()
    try:
        module = import_module("langfuse")
        constructor = cast(Callable[..., _LangfuseClient], module.Langfuse)
        client = constructor(public_key=public_key, secret_key=secret_key, host=host)
    except Exception:
        return NoOpTracer()
    return LangfuseTracer(client)
