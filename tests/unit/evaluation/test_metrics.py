import pytest

from evaluation.run import mrr, ndcg_at_k, recall_at_k


def test_상위_K개에_정답이_포함된_비율을_계산한다() -> None:
    assert recall_at_k(["c2", "c1", "c3"], {"c1", "c4"}, k=2) == 0.5


def test_첫_정답의_역순위를_계산한다() -> None:
    assert mrr(["c2", "c1", "c3"], {"c1"}) == 0.5
    assert mrr(["c2", "c3"], {"c1"}) == 0.0


def test_이상적인_순위와_비교한_nDCG를_계산한다() -> None:
    assert ndcg_at_k(["c2", "c1"], {"c1"}, k=2) == pytest.approx(1 / 1.5849625)

