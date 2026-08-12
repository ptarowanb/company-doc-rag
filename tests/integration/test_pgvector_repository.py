import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.mark.integration
@pytest.mark.asyncio
async def test_PostgreSQL에_vector_확장이_활성화되어_있다() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL이 설정되지 않아 pgvector 통합 테스트를 건너뜁니다.")
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            )
            assert result.scalar_one() == "vector"
    finally:
        await engine.dispose()

