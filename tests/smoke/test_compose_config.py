from pathlib import Path

import yaml


def test_Compose에_필수_서비스와_OpenAI_키가_정의되어_있다() -> None:
    config = yaml.safe_load(Path("compose.yaml").read_text(encoding="utf-8"))

    assert {"api", "worker", "postgres", "redis"} <= set(config["services"])
    assert "OPENAI_API_KEY" in config["services"]["api"]["environment"]
    assert config["services"]["postgres"]["healthcheck"]
    assert config["services"]["redis"]["healthcheck"]


def test_Docker_이미지는_CPU_전용_PyTorch를_설치한다() -> None:
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

    assert "https://download.pytorch.org/whl/cpu" in dockerfile
