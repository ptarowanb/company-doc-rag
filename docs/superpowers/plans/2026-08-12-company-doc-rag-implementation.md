# 사내 문서 RAG 시스템 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 한국어 PDF를 비동기로 수집하고 하이브리드 검색·reranker·OpenAI 답변·출처·SSE를 제공하는 로컬 실행형 RAG 백엔드와 검증 가능한 AWS Terraform 구성을 만든다.

**Architecture:** FastAPI 기반 모듈형 모놀리스에서 API와 Celery 작업자를 프로세스로 분리한다. PostgreSQL/pgvector는 문서·청크·벡터를, Redis는 작업 큐와 검색 캐시를 담당하며 외부 서비스는 포트 인터페이스 뒤에 격리한다.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic Settings, SQLAlchemy 2, Alembic, PostgreSQL 16/pgvector, Redis 7, Celery 5, OpenAI Python SDK, PyMuPDF, tiktoken, sentence-transformers, Langfuse, pytest, Ruff, mypy, Docker Compose, Terraform 1.6+

## Global Constraints

- 코드 주석, docstring, README, PR 설명은 한글을 기본으로 작성한다.
- 커밋 제목은 영문 타입과 한글 명령형 요약을 결합한다.
- `.env`와 모든 API 키·자격 증명은 커밋하지 않는다.
- 기본 테스트는 OpenAI, Langfuse, AWS 네트워크를 호출하지 않는다.
- 로컬 기본 서비스는 `api`, `worker`, `postgres`, `redis`다.
- Langfuse 설정이 없어도 no-op 구현으로 정상 동작해야 한다.
- Terraform은 `validate`까지만 수행하고 `apply`하지 않는다.
- 실제 완료 시각을 사용하며 커밋 작성자나 날짜를 조작하지 않는다.

## 파일 구조

```text
src/company_doc_rag/
  api/                 # FastAPI 라우터, 요청·응답, SSE 형식
  application/         # 수집·검색·질의응답 유스케이스
  domain/              # 엔티티, 값 객체, 포트
  infrastructure/      # DB, OpenAI, Redis, 파일, reranker, Langfuse 어댑터
  workers/             # Celery 앱과 문서 수집 작업
  config.py            # 환경변수 설정
  main.py              # FastAPI 조립
tests/
  unit/                # 외부 서비스 없는 단위 테스트
  integration/         # PostgreSQL/Redis가 필요한 테스트
evaluation/            # 검색 품질 평가 데이터와 실행기
infra/terraform/       # AWS 참고 아키텍처 IaC
docs/architecture/     # 로컬·AWS 구조 문서
docs/content/          # LinkedIn·기술 블로그 초안
```

---

### Task 1: 프로젝트 기반, 설정, 헬스체크

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `src/company_doc_rag/__init__.py`
- Create: `src/company_doc_rag/config.py`
- Create: `src/company_doc_rag/main.py`
- Create: `src/company_doc_rag/api/health.py`
- Create: `tests/unit/test_config.py`
- Create: `tests/unit/api/test_health.py`

**Interfaces:**
- Produces: `Settings`, `get_settings()`, `create_app() -> FastAPI`

- [ ] **Step 1: 설정과 헬스체크 실패 테스트 작성**

```python
def test_settings_requires_openai_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)

def test_liveness(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit/test_config.py tests/unit/api/test_health.py -q`
Expected: FAIL because package modules do not exist.

- [ ] **Step 3: 최소 프로젝트 기반 구현**

`Settings`에는 `openai_api_key`, `openai_chat_model`, `openai_embedding_model`, `database_url`, `redis_url`, `upload_dir`, `langfuse_*`를 정의한다. `create_app()`은 lifespan에서 설정을 읽고 `/health/live`를 등록한다.

- [ ] **Step 4: 품질 검사**

Run: `python -m pytest tests/unit/test_config.py tests/unit/api/test_health.py -q && python -m ruff check . && python -m mypy src`
Expected: all tests and checks pass.

- [ ] **Step 5: 커밋**

```bash
git add pyproject.toml .gitignore .env.example src tests
git commit -m "chore: Python 프로젝트 기반 구성"
```

### Task 2: 문서 도메인과 PDF 청킹

**Files:**
- Create: `src/company_doc_rag/domain/documents.py`
- Create: `src/company_doc_rag/domain/errors.py`
- Create: `src/company_doc_rag/domain/ports.py`
- Create: `src/company_doc_rag/application/chunking.py`
- Create: `src/company_doc_rag/infrastructure/pdf_loader.py`
- Create: `tests/unit/application/test_chunking.py`
- Create: `tests/unit/infrastructure/test_pdf_loader.py`

**Interfaces:**
- Produces: `DocumentStatus`, `PageText`, `ChunkDraft`, `TokenChunker.split(pages) -> list[ChunkDraft]`
- Produces: `PdfLoader.load(path: Path) -> list[PageText]`

- [ ] **Step 1: 청킹 경계 테스트 작성**

```python
def test_chunker_preserves_page_range(fake_tokenizer):
    pages = [PageText(page=1, text="가 " * 8), PageText(page=2, text="나 " * 8)]
    chunks = TokenChunker(max_tokens=10, overlap_tokens=2, tokenizer=fake_tokenizer).split(pages)
    assert chunks[0].page_start == 1
    assert chunks[-1].page_end == 2
    assert all(chunk.token_count <= 10 for chunk in chunks)
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit/application/test_chunking.py -q`
Expected: FAIL because `TokenChunker` is missing.

- [ ] **Step 3: 도메인 타입·PDF 로더·토큰 청커 구현**

텍스트 정규화는 연속 공백만 줄이고 페이지 번호는 1부터 유지한다. 암호화 PDF는 `EncryptedPdfError`, 텍스트가 없는 PDF는 `EmptyDocumentError`로 변환한다. 청커는 문단을 우선 결합하고 긴 문단만 토큰 단위로 분리한다.

- [ ] **Step 4: 테스트와 정적 검사**

Run: `python -m pytest tests/unit/application/test_chunking.py tests/unit/infrastructure/test_pdf_loader.py -q && python -m ruff check src tests`
Expected: PASS.

- [ ] **Step 5: 커밋**

```bash
git add src/company_doc_rag/domain src/company_doc_rag/application/chunking.py src/company_doc_rag/infrastructure/pdf_loader.py tests/unit
git commit -m "feat: PDF 파싱과 토큰 청킹 구현"
```

### Task 3: PostgreSQL/pgvector 저장 계층

**Files:**
- Create: `src/company_doc_rag/infrastructure/database.py`
- Create: `src/company_doc_rag/infrastructure/models.py`
- Create: `src/company_doc_rag/infrastructure/repositories.py`
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/versions/0001_create_documents_and_chunks.py`
- Create: `tests/unit/infrastructure/test_repositories.py`
- Create: `tests/integration/test_pgvector_repository.py`

**Interfaces:**
- Produces: `DocumentRepository.create/get/list/delete/update_status`
- Produces: `ChunkRepository.replace_for_document/vector_search/keyword_search`
- Consumes: `DocumentStatus`, `ChunkDraft`

- [ ] **Step 1: 저장소 상태 전이와 삭제 테스트 작성**

```python
async def test_document_status_transition(repository):
    document = await repository.create(filename="guide.pdf", sha256="a" * 64, storage_key="id.pdf")
    await repository.update_status(document.id, DocumentStatus.READY)
    assert (await repository.get(document.id)).status is DocumentStatus.READY
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit/infrastructure/test_repositories.py -q`
Expected: FAIL because repositories are missing.

- [ ] **Step 3: SQLAlchemy 모델, Alembic 마이그레이션, 저장소 구현**

`documents.sha256`는 unique, `chunks.document_id`는 cascade delete다. `chunks.embedding`은 설정된 임베딩 차원의 `Vector`, 본문은 trigram GIN, 벡터는 cosine HNSW 인덱스를 사용한다. 검색 메서드는 준비 완료 문서만 반환한다.

- [ ] **Step 4: 단위·통합 테스트**

Run: `python -m pytest tests/unit/infrastructure/test_repositories.py -q`
Run with services: `python -m pytest tests/integration/test_pgvector_repository.py -q`
Expected: unit tests always pass; integration tests pass when test database is configured.

- [ ] **Step 5: 커밋**

```bash
git add src/company_doc_rag/infrastructure alembic.ini alembic tests
git commit -m "feat: pgvector 문서 저장소 구현"
```

### Task 4: OpenAI 임베딩과 문서 수집 유스케이스

**Files:**
- Create: `src/company_doc_rag/infrastructure/openai_client.py`
- Create: `src/company_doc_rag/infrastructure/file_storage.py`
- Create: `src/company_doc_rag/application/ingestion.py`
- Create: `tests/unit/application/test_ingestion.py`
- Create: `tests/unit/infrastructure/test_file_storage.py`

**Interfaces:**
- Produces: `OpenAIEmbedder.embed(texts: Sequence[str]) -> list[list[float]]`
- Produces: `LocalFileStorage.save/delete/open`
- Produces: `IngestDocument.execute(document_id: UUID) -> None`
- Consumes: `PdfLoader`, `TokenChunker`, document/chunk repositories

- [ ] **Step 1: 수집 멱등성과 실패 상태 테스트 작성**

```python
async def test_ingestion_is_idempotent(ingest, chunks):
    await ingest.execute(DOCUMENT_ID)
    await ingest.execute(DOCUMENT_ID)
    assert chunks.replace_count == 1

async def test_ingestion_marks_failed(ingest, documents, loader):
    loader.error = EmptyDocumentError()
    with pytest.raises(EmptyDocumentError):
        await ingest.execute(DOCUMENT_ID)
    assert documents.status is DocumentStatus.FAILED
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit/application/test_ingestion.py -q`
Expected: FAIL because use case is missing.

- [ ] **Step 3: 파일 저장소, 배치 임베딩, 수집 유스케이스 구현**

파일명은 UUID와 `.pdf`만으로 생성한다. 임베딩 요청은 설정된 배치 크기로 나누고 SDK의 transient error만 지수 백오프로 최대 3회 재시도한다. 이미 `READY`인 문서는 다시 처리하지 않는다.

- [ ] **Step 4: 테스트**

Run: `python -m pytest tests/unit/application/test_ingestion.py tests/unit/infrastructure/test_file_storage.py -q`
Expected: PASS.

- [ ] **Step 5: 커밋**

```bash
git add src/company_doc_rag/application/ingestion.py src/company_doc_rag/infrastructure/openai_client.py src/company_doc_rag/infrastructure/file_storage.py tests/unit
git commit -m "feat: OpenAI 임베딩 수집 파이프라인 구현"
```

### Task 5: 하이브리드 검색, RRF, reranker

**Files:**
- Create: `src/company_doc_rag/domain/search.py`
- Create: `src/company_doc_rag/application/search.py`
- Create: `src/company_doc_rag/infrastructure/reranker.py`
- Create: `tests/unit/application/test_search.py`
- Create: `tests/unit/infrastructure/test_reranker.py`

**Interfaces:**
- Produces: `reciprocal_rank_fusion(rankings, k=60) -> list[SearchHit]`
- Produces: `HybridSearch.execute(question, document_ids=None) -> list[SearchHit]`
- Produces: `CrossEncoderReranker.rerank(query, hits, limit) -> list[SearchHit]`

- [ ] **Step 1: RRF 결합 순위 테스트 작성**

```python
def test_rrf_rewards_hits_found_by_both_retrievers():
    vector = [hit("a"), hit("b")]
    keyword = [hit("b"), hit("c")]
    fused = reciprocal_rank_fusion([vector, keyword], k=60)
    assert fused[0].chunk_id == "b"
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit/application/test_search.py -q`
Expected: FAIL because RRF is missing.

- [ ] **Step 3: 병렬 후보 검색, RRF, lazy-load reranker 구현**

벡터·키워드 검색은 각각 상위 20개를 가져오고, RRF 상위 12개만 reranker에 전달하며 최종 5개를 반환한다. sentence-transformers 모델은 첫 요청에서 로드하며 테스트에서는 `Reranker` 포트의 가짜 구현을 주입한다.

- [ ] **Step 4: 테스트**

Run: `python -m pytest tests/unit/application/test_search.py tests/unit/infrastructure/test_reranker.py -q`
Expected: PASS.

- [ ] **Step 5: 커밋**

```bash
git add src/company_doc_rag/domain/search.py src/company_doc_rag/application/search.py src/company_doc_rag/infrastructure/reranker.py tests/unit
git commit -m "feat: 하이브리드 검색과 reranker 구현"
```

### Task 6: 근거 기반 답변, 출처, SSE API

**Files:**
- Create: `src/company_doc_rag/domain/answers.py`
- Create: `src/company_doc_rag/application/answering.py`
- Create: `src/company_doc_rag/api/schemas.py`
- Create: `src/company_doc_rag/api/query.py`
- Modify: `src/company_doc_rag/infrastructure/openai_client.py`
- Modify: `src/company_doc_rag/main.py`
- Create: `tests/unit/application/test_answering.py`
- Create: `tests/unit/api/test_query.py`

**Interfaces:**
- Produces: `AnswerQuestion.execute(question, document_ids) -> Answer`
- Produces: `AnswerQuestion.stream(question, document_ids) -> AsyncIterator[AnswerEvent]`
- Produces SSE events: `metadata`, `token`, `sources`, `done`, `error`
- Consumes: `HybridSearch`, `OpenAIAnswerGenerator`

- [ ] **Step 1: 근거 없음과 SSE 순서 테스트 작성**

```python
async def test_answer_without_evidence_does_not_call_llm(answerer, generator):
    answer = await answerer.execute("없는 규정은?")
    assert answer.text == "관련 문서에서 답을 찾지 못했습니다."
    assert generator.calls == 0

def test_stream_event_order(client):
    events = parse_sse(client.stream("POST", "/api/v1/query/stream", json={"question": "휴가 규정?"}))
    assert [event.name for event in events] == ["metadata", "token", "sources", "done"]
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit/application/test_answering.py tests/unit/api/test_query.py -q`
Expected: FAIL because answer use case and route are missing.

- [ ] **Step 3: 출처 프롬프트와 스트리밍 API 구현**

컨텍스트는 `[출처 1] 문서명, p.3` 형식으로 조립한다. 생성 결과와 별도로 구조화한 `Source`를 반환해 모델이 출처 메타데이터를 조작하지 못하게 한다. 연결 해제 시 OpenAI 스트림을 닫는다.

- [ ] **Step 4: 테스트**

Run: `python -m pytest tests/unit/application/test_answering.py tests/unit/api/test_query.py -q`
Expected: PASS.

- [ ] **Step 5: 커밋**

```bash
git add src/company_doc_rag tests/unit
git commit -m "feat: 출처 기반 답변과 SSE 스트리밍 구현"
```

### Task 7: 문서 API, Celery 작업자, Redis 캐시

**Files:**
- Create: `src/company_doc_rag/api/documents.py`
- Create: `src/company_doc_rag/application/documents.py`
- Create: `src/company_doc_rag/infrastructure/cache.py`
- Create: `src/company_doc_rag/workers/celery_app.py`
- Create: `src/company_doc_rag/workers/tasks.py`
- Modify: `src/company_doc_rag/main.py`
- Create: `tests/unit/api/test_documents.py`
- Create: `tests/unit/workers/test_tasks.py`
- Create: `tests/unit/infrastructure/test_cache.py`

**Interfaces:**
- Produces document routes from the design API contract
- Produces: `SearchCache.get/set/bump_generation`
- Produces: `ingest_document(document_id: str)` Celery task
- Consumes: `IngestDocument`, repositories, `LocalFileStorage`

- [ ] **Step 1: 업로드 검증과 작업 멱등성 테스트 작성**

```python
def test_rejects_non_pdf(client):
    response = client.post("/api/v1/documents", files={"file": ("x.txt", b"x", "text/plain")})
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"

def test_task_retries_transient_openai_error(task_runner):
    result = task_runner.run_with(TransientEmbeddingError())
    assert result.retry_count == 1
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit/api/test_documents.py tests/unit/workers/test_tasks.py -q`
Expected: FAIL because routes and task are missing.

- [ ] **Step 3: 문서 CRUD, 큐 작업, 캐시 세대 구현**

업로드 최대 크기는 설정값으로 제한하고 SHA-256 중복은 `409`로 반환한다. Celery는 transient 오류만 재시도하고 도메인 검증 오류는 즉시 `FAILED`로 종료한다. 문서 생성·삭제가 완료되면 Redis 세대를 증가시킨다.

- [ ] **Step 4: 테스트**

Run: `python -m pytest tests/unit/api/test_documents.py tests/unit/workers/test_tasks.py tests/unit/infrastructure/test_cache.py -q`
Expected: PASS.

- [ ] **Step 5: 커밋**

```bash
git add src/company_doc_rag tests/unit
git commit -m "feat: 비동기 문서 API와 Redis 캐시 구현"
```

### Task 8: Langfuse 관측성과 검색 평가

**Files:**
- Create: `src/company_doc_rag/domain/observability.py`
- Create: `src/company_doc_rag/infrastructure/observability.py`
- Modify: `src/company_doc_rag/application/ingestion.py`
- Modify: `src/company_doc_rag/application/search.py`
- Modify: `src/company_doc_rag/application/answering.py`
- Create: `evaluation/dataset.jsonl`
- Create: `evaluation/run.py`
- Create: `tests/unit/infrastructure/test_observability.py`
- Create: `tests/unit/evaluation/test_metrics.py`

**Interfaces:**
- Produces: `Tracer.trace(name, metadata)` context manager
- Produces: `NoOpTracer`, `LangfuseTracer`
- Produces: `recall_at_k`, `mrr`, `ndcg_at_k`

- [ ] **Step 1: no-op 장애 격리와 지표 테스트 작성**

```python
def test_noop_tracer_never_changes_result():
    with NoOpTracer().trace("query", {"question_hash": "abc"}):
        result = 42
    assert result == 42

def test_recall_at_k():
    assert recall_at_k(["c2", "c1"], {"c1"}, k=2) == 1.0
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit/infrastructure/test_observability.py tests/unit/evaluation/test_metrics.py -q`
Expected: FAIL because tracer and metrics are missing.

- [ ] **Step 3: 선택적 추적과 평가 실행기 구현**

원문 대신 SHA-256 기반 질문 식별자, 후보 수, 순위 점수, 모델명, 토큰 수, 지연 시간만 기본 기록한다. Langfuse 예외는 로깅 후 삼키며 평가 실행기는 벡터 단독·하이브리드·reranker 결과를 같은 데이터셋에서 비교한다.

- [ ] **Step 4: 테스트**

Run: `python -m pytest tests/unit/infrastructure/test_observability.py tests/unit/evaluation/test_metrics.py -q`
Expected: PASS.

- [ ] **Step 5: 커밋**

```bash
git add src/company_doc_rag evaluation tests/unit
git commit -m "feat: Langfuse 추적과 검색 평가 도구 구현"
```

### Task 9: Docker Compose와 로컬 재현 환경

**Files:**
- Create: `Dockerfile`
- Create: `compose.yaml`
- Create: `.dockerignore`
- Create: `scripts/wait_for_services.py`
- Modify: `README.md`
- Create: `tests/smoke/test_compose_config.py`

**Interfaces:**
- Produces: `docker compose up --build` local stack
- Consumes: application module, Alembic migration, `.env`

- [ ] **Step 1: Compose 계약 테스트 작성**

```python
def test_compose_has_required_services(compose_config):
    assert {"api", "worker", "postgres", "redis"} <= set(compose_config["services"])
    assert "OPENAI_API_KEY" in compose_config["services"]["api"]["environment"]
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/smoke/test_compose_config.py -q`
Expected: FAIL because `compose.yaml` is missing.

- [ ] **Step 3: 이미지, 서비스, healthcheck, 볼륨 구현**

API와 worker는 같은 이미지를 사용하고 명령만 분리한다. PostgreSQL은 pgvector 이미지를 사용하며 Redis와 함께 healthcheck를 둔다. README에는 키 설정, 실행, 업로드, 상태 폴링, 일반 질의와 SSE 예시, 종료와 볼륨 삭제 방법을 한글로 작성한다.

- [ ] **Step 4: 구성 검증**

Run: `docker compose config -q && python -m pytest tests/smoke/test_compose_config.py -q`
Expected: PASS without starting paid services.

- [ ] **Step 5: 커밋**

```bash
git add Dockerfile compose.yaml .dockerignore scripts README.md tests/smoke
git commit -m "build: Docker Compose 로컬 실행 환경 구성"
```

### Task 10: AWS 아키텍처와 Terraform

**Files:**
- Create: `infra/terraform/versions.tf`
- Create: `infra/terraform/providers.tf`
- Create: `infra/terraform/variables.tf`
- Create: `infra/terraform/main.tf`
- Create: `infra/terraform/network.tf`
- Create: `infra/terraform/security.tf`
- Create: `infra/terraform/data.tf`
- Create: `infra/terraform/compute.tf`
- Create: `infra/terraform/observability.tf`
- Create: `infra/terraform/outputs.tf`
- Create: `infra/terraform/terraform.tfvars.example`
- Create: `infra/terraform/backend.tf.example`
- Create: `docs/architecture/aws.md`

**Interfaces:**
- Produces: VPC, ALB, ECS API/worker, ECR, S3, RDS, ElastiCache, Secrets Manager, CloudWatch
- Consumes: container image tag and environment variables

- [ ] **Step 1: Terraform 루트 계약 작성**

변수는 `project_name`, `environment`, `aws_region`, `container_image`, `db_instance_class`, `redis_node_type`, `allowed_cidr_blocks`로 제한한다. 기본값은 생성 비용이 낮은 개발 규격으로 두되 `apply`가 비용을 만든다는 설명을 변수와 문서에 표시한다.

- [ ] **Step 2: 네트워크·데이터·컴퓨트 구성 구현**

ALB만 공용 서브넷에 두고 ECS, RDS, Redis는 사설 서브넷에 둔다. 보안 그룹은 ALB→API, API/worker→DB·Redis만 허용한다. S3는 public access block과 암호화를, RDS·Redis는 저장 암호화를 활성화한다. ECS 태스크 비밀값은 Secrets Manager ARN으로 주입한다.

- [ ] **Step 3: 경보와 출력 구현**

ECS CPU, ALB 5xx, RDS CPU·여유 저장 공간 경보를 구성한다. 출력은 ALB DNS, S3 버킷명, ECR URL만 노출하고 비밀값은 출력하지 않는다.

- [ ] **Step 4: 형식·유효성 검사**

Run: `terraform -chdir=infra/terraform fmt -check -recursive`
Run after init without backend: `terraform -chdir=infra/terraform init -backend=false && terraform -chdir=infra/terraform validate`
Expected: PASS; no AWS resources are created.

- [ ] **Step 5: 커밋**

```bash
git add infra/terraform docs/architecture/aws.md
git commit -m "feat: AWS 아키텍처 Terraform 구성"
```

### Task 11: 통합 검증, 포트폴리오 문서, 콘텐츠 연결

**Files:**
- Modify: `README.md`
- Create: `docs/architecture/local.md`
- Create: `docs/content/01-project-overview.md`
- Create: `docs/content/02-hybrid-search.md`
- Create: `docs/content/03-operations-and-aws.md`
- Create: `docs/content/linkedin-post.md`
- Create: `docs/content/benchmark-template.md`
- Create: `CONTRIBUTING.md`

**Interfaces:**
- Produces: GitHub README → 기술 블로그/LinkedIn 원고 → 관련 커밋·구조도·평가 명령 연결

- [ ] **Step 1: 전체 검증 실행**

Run: `python -m pytest -q && python -m ruff check . && python -m mypy src`
Run: `docker compose config -q`
Run: `terraform -chdir=infra/terraform fmt -check -recursive && terraform -chdir=infra/terraform validate`
Expected: all checks pass or external-service tests are explicitly skipped with a reason.

- [ ] **Step 2: README 포트폴리오 서사 완성**

README 상단에 문제, 해결, 아키텍처, 핵심 기술 판단, 로컬 실행, API 예시, 평가 방법, AWS 대응표, 비용 주의, 콘텐츠 링크를 둔다. 구현되지 않은 수치는 쓰지 않고 평가 명령으로 재현 가능한 결과만 넣는다.

- [ ] **Step 3: 기술 블로그·LinkedIn 초안 작성**

각 글은 문제→선택지→실험→결과→배운 점 구조를 사용한다. 벤치마크 표에는 데이터셋 버전, 질의 수, Recall@5, MRR, nDCG@5, 검색 p95를 기록하고 측정 전에는 빈 수치 대신 측정 절차만 제공한다.

- [ ] **Step 4: 비밀값·문서·Git 상태 검사**

Run: `git grep -n -I -E '(sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16})' -- . ':!.env.example'`
Expected: no output.
Run: `git status --short && git log --oneline --decorate -15`
Expected: only intended portfolio documents remain before commit.

- [ ] **Step 5: 커밋**

```bash
git add README.md CONTRIBUTING.md docs
git commit -m "docs: 포트폴리오와 기술 콘텐츠 문서화"
```

### Task 12: 최종 회귀 검증과 원격 반영 준비

**Files:**
- Modify only files required by verification failures.

**Interfaces:**
- Produces: clean, reproducible local repository ready to push

- [ ] **Step 1: 새 환경 설치 검증**

Run: `python -m venv .venv && .venv/Scripts/python -m pip install -e ".[dev]"`
Expected: installation succeeds on supported Python.

- [ ] **Step 2: 전체 테스트 재실행**

Run: `.venv/Scripts/python -m pytest -q`
Run: `.venv/Scripts/python -m ruff check .`
Run: `.venv/Scripts/python -m mypy src`
Expected: PASS.

- [ ] **Step 3: 인프라 정적 검증 재실행**

Run: `docker compose config -q`
Run: `terraform -chdir=infra/terraform fmt -check -recursive && terraform -chdir=infra/terraform validate`
Expected: PASS without creating AWS resources.

- [ ] **Step 4: 필요 수정 커밋**

검증 실패를 수정한 경우에만 관련 파일을 스테이징한다.

```bash
git commit -m "fix: 전체 검증 오류 수정"
```

- [ ] **Step 5: 푸시 전 상태 보고**

Run: `git status --short --branch && git log --oneline --decorate -15`
Expected: 작업 트리가 깨끗하고 각 커밋이 실제 완료 단위를 나타낸다. 원격 push는 사용자의 기존 승인 범위에 따라 수행한다.
