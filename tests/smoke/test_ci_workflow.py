from pathlib import Path
from typing import Any

import yaml

WORKFLOW_PATH = Path(".github/workflows/ci.yml")


def _workflow() -> dict[str, Any]:
    assert WORKFLOW_PATH.exists(), "CI 워크플로 파일이 필요합니다."
    parsed = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    return parsed


def _triggers(workflow: dict[str, Any]) -> dict[str, Any]:
    triggers = workflow.get("on", workflow.get(True))
    assert isinstance(triggers, dict)
    return triggers


def _run_commands(job: dict[str, Any]) -> str:
    return "\n".join(str(step.get("run", "")) for step in job["steps"])


def test_CI는_main과_PR에서_최소_권한으로_실행된다() -> None:
    workflow = _workflow()
    triggers = _triggers(workflow)

    assert triggers["push"]["branches"] == ["main"]
    assert "pull_request" in triggers
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["concurrency"]["cancel-in-progress"] is True


def test_CI는_세_품질_게이트를_독립적으로_제공한다() -> None:
    jobs = _workflow()["jobs"]

    assert set(jobs) == {"quality", "postgres-integration", "container-infra"}
    assert all(job["runs-on"] == "ubuntu-latest" for job in jobs.values())
    assert all("needs" not in job for job in jobs.values())


def test_Python_품질_작업은_테스트와_정적_분석과_평가_CLI를_검증한다() -> None:
    commands = _run_commands(_workflow()["jobs"]["quality"])

    assert 'pytest -q -m "not integration and not external"' in commands
    assert "ruff check ." in commands
    assert "mypy src" in commands
    assert "evaluation.run" in commands


def test_PostgreSQL_작업은_pgvector와_migration을_검증한다() -> None:
    job = _workflow()["jobs"]["postgres-integration"]
    commands = _run_commands(job)

    assert job["services"]["postgres"]["image"] == "pgvector/pgvector:pg16"
    assert "TEST_DATABASE_URL" in job["env"]
    assert "alembic upgrade head" in commands
    assert "pytest -q -m integration" in commands


def test_인프라_작업은_Docker와_Terraform을_정적으로_검증한다() -> None:
    commands = _run_commands(_workflow()["jobs"]["container-infra"])

    assert "docker compose config -q" in commands
    assert "docker build" in commands
    assert "torch.version.cuda is None" in commands
    assert "terraform -chdir=infra/terraform fmt -check -recursive" in commands
    assert "terraform -chdir=infra/terraform init -backend=false" in commands
    assert "terraform -chdir=infra/terraform validate" in commands
