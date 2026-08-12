import argparse
import json
import math
from collections.abc import Sequence, Set
from dataclasses import dataclass
from pathlib import Path


def recall_at_k(predicted: Sequence[str], relevant: Set[str], k: int) -> float:
    """전체 정답 중 상위 K개 결과가 찾은 비율을 계산한다."""

    if not relevant:
        return 0.0
    return len(set(predicted[:k]) & relevant) / len(relevant)


def mrr(predicted: Sequence[str], relevant: Set[str]) -> float:
    """첫 정답이 나타난 순위의 역수를 계산한다."""

    for rank, item in enumerate(predicted, start=1):
        if item in relevant:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(predicted: Sequence[str], relevant: Set[str], k: int) -> float:
    """이진 관련도를 사용해 상위 K개 순위의 nDCG를 계산한다."""

    dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank, item in enumerate(predicted[:k], start=1)
        if item in relevant
    )
    ideal_count = min(len(relevant), k)
    ideal = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_count + 1))
    return dcg / ideal if ideal else 0.0


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    question: str
    relevant_ids: frozenset[str]


def load_jsonl(path: Path) -> list[dict[str, object]]:
    """UTF-8 JSON Lines 파일을 읽는다."""

    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def evaluate(dataset_path: Path, results_path: Path, k: int = 5) -> dict[str, float]:
    """질문별 검색 결과를 정답 데이터셋과 비교한다."""

    cases = {
        str(item["question"]): frozenset(str(value) for value in item["relevant_ids"])
        for item in load_jsonl(dataset_path)
    }
    results = {
        str(item["question"]): [str(value) for value in item["retrieved_ids"]]
        for item in load_jsonl(results_path)
    }
    recalls = [
        recall_at_k(results.get(question, []), relevant, k) for question, relevant in cases.items()
    ]
    reciprocal_ranks = [
        mrr(results.get(question, []), relevant) for question, relevant in cases.items()
    ]
    ndcgs = [
        ndcg_at_k(results.get(question, []), relevant, k) for question, relevant in cases.items()
    ]
    count = len(cases) or 1
    return {
        f"recall@{k}": sum(recalls) / count,
        "mrr": sum(reciprocal_ranks) / count,
        f"ndcg@{k}": sum(ndcgs) / count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="검색 결과 품질을 계산합니다.")
    parser.add_argument("--dataset", type=Path, default=Path("evaluation/dataset.jsonl"))
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("-k", type=int, default=5)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.dataset, args.results, args.k), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
