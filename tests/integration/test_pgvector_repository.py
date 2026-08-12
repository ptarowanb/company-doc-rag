import os

import pytest
from sqlalchemy import create_engine, text


@pytest.mark.integration
def test_PostgreSQL에_vector_확장이_활성화되어_있다() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL이 설정되지 않아 pgvector 통합 테스트를 건너뜁니다.")
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            )
            assert result.scalar_one() == "vector"
    finally:
        engine.dispose()
