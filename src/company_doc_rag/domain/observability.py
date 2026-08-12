import hashlib
from collections.abc import Iterator, Mapping
from contextlib import AbstractContextManager, contextmanager
from typing import Protocol


class Span(Protocol):
    """유스케이스가 추적 결과를 기록하는 최소 인터페이스."""

    def set_output(self, output: Mapping[str, object]) -> None: ...


class Tracer(Protocol):
    """추적 공급자와 무관한 컨텍스트 생성 인터페이스."""

    def trace(
        self,
        name: str,
        metadata: Mapping[str, object],
    ) -> AbstractContextManager[Span]: ...


class NoOpSpan:
    """관측 기능이 꺼졌을 때 사용하는 빈 span."""

    def set_output(self, output: Mapping[str, object]) -> None:
        return None


class NoOpTracer:
    """설정 없이도 애플리케이션 흐름을 유지하는 추적기."""

    @contextmanager
    def trace(self, name: str, metadata: Mapping[str, object]) -> Iterator[Span]:
        yield NoOpSpan()


def text_hash(text: str) -> str:
    """원문 대신 추적에 기록할 안정적인 SHA-256 식별자를 만든다."""

    return hashlib.sha256(text.encode()).hexdigest()

