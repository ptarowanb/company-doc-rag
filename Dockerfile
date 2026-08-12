FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app \
    && useradd --system --gid app --create-home app

COPY pyproject.toml README.md ./
COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic
COPY evaluation ./evaluation

RUN python -m pip install --upgrade pip \
    && python -m pip install ".[reranker,observability]" \
    && mkdir -p /app/uploads /home/app/.cache \
    && chown -R app:app /app /home/app

USER app

EXPOSE 8000

CMD ["uvicorn", "company_doc_rag.main:create_runtime_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

