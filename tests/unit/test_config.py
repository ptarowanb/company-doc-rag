import pytest
from pydantic import ValidationError

from company_doc_rag.config import Settings


def test_openai_api_key가_없으면_설정_생성에_실패한다(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_환경변수로_모델을_교체할_수_있다(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_CHAT_MODEL", "chat-test")
    monkeypatch.setenv("OPENAI_EMBEDDING_MODEL", "embedding-test")

    settings = Settings(_env_file=None)

    assert settings.openai_chat_model == "chat-test"
    assert settings.openai_embedding_model == "embedding-test"


def test_스키마와_다른_임베딩_차원을_거부한다(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_EMBEDDING_DIMENSIONS", "3072")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)

