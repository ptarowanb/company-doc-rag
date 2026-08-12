import asyncio
from collections.abc import Callable, Sequence
from dataclasses import replace
from importlib import import_module
from typing import Protocol, cast

from company_doc_rag.domain.search import SearchHit


class _CrossEncoder(Protocol):
    def predict(self, pairs: Sequence[Sequence[str]]) -> Sequence[float]: ...


class CrossEncoderReranker:
    """다국어 CrossEncoder로 질문과 청크의 관련도를 재계산한다."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        model: _CrossEncoder | None = None,
    ) -> None:
        self._model_name = model_name
        self._model = model

    async def rerank(
        self,
        query: str,
        hits: Sequence[SearchHit],
        limit: int,
    ) -> list[SearchHit]:
        if not hits:
            return []
        return await asyncio.to_thread(self._rerank_sync, query, hits, limit)

    def _rerank_sync(
        self,
        query: str,
        hits: Sequence[SearchHit],
        limit: int,
    ) -> list[SearchHit]:
        pairs = [[query, hit.content] for hit in hits]
        scores = self._get_model().predict(pairs)
        scored = [
            replace(hit, rerank_score=float(score))
            for hit, score in zip(hits, scores, strict=True)
        ]
        return sorted(
            scored,
            key=lambda hit: hit.rerank_score if hit.rerank_score is not None else float("-inf"),
            reverse=True,
        )[:limit]

    def _get_model(self) -> _CrossEncoder:
        if self._model is None:
            try:
                module = import_module("sentence_transformers")
            except ImportError as error:
                raise RuntimeError(
                    "reranker 사용을 위해 'pip install .[reranker]'를 실행하세요."
                ) from error
            constructor = cast(Callable[[str], _CrossEncoder], module.CrossEncoder)
            self._model = constructor(self._model_name)
        return self._model

