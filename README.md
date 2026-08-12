# 사내 문서 AI 검색·질의응답 시스템

한국어 PDF를 업로드하면 페이지 정보를 보존해 청킹·임베딩하고, 벡터 검색과 키워드 검색을 결합한 뒤 reranker로 근거를 정제해 출처와 함께 답변하는 RAG 백엔드입니다.

## 핵심 흐름

```text
PDF 업로드 → Celery 비동기 수집 → 토큰 청킹 → OpenAI 임베딩
→ PostgreSQL/pgvector + pg_trgm → RRF → 다국어 reranker
→ OpenAI 답변 → SSE 스트리밍 + 페이지 출처
```

## 로컬 실행

필요한 도구는 Docker Desktop과 OpenAI API 키입니다. AWS나 Langfuse 계정은 없어도 됩니다.

```powershell
Copy-Item .env.example .env
# .env의 OPENAI_API_KEY를 실제 키로 교체
docker compose up --build
```

첫 질의에서 reranker 모델을 내려받기 때문에 응답이 평소보다 늦을 수 있습니다. API 문서는 `http://localhost:8000/docs`, 준비 상태는 `http://localhost:8000/health/ready`에서 확인합니다.

### PDF 업로드

```powershell
curl.exe -X POST http://localhost:8000/api/v1/documents `
  -F "file=@C:\docs\휴가규정.pdf;type=application/pdf"
```

응답의 `id`로 처리 상태를 확인합니다.

```powershell
curl.exe http://localhost:8000/api/v1/documents/{문서-ID}
```

### 일반 질의

```powershell
curl.exe -X POST http://localhost:8000/api/v1/query `
  -H "Content-Type: application/json" `
  -d '{"question":"연차 휴가는 며칠인가요?"}'
```

### SSE 스트리밍 질의

```powershell
curl.exe -N -X POST http://localhost:8000/api/v1/query/stream `
  -H "Content-Type: application/json" `
  -d '{"question":"재택근무 신청 절차를 알려주세요."}'
```

이벤트 순서는 `metadata → token 반복 → sources → done`이며 오류 시 `error`를 반환합니다.

## 검색 품질 평가

예제 결과로 평가 도구를 확인할 수 있습니다.

```powershell
python -m evaluation.run --results evaluation/retrieval-results.example.jsonl
```

실제 실험에서는 동일한 질문 세트로 벡터 단독, 하이브리드, reranker 결과를 각각 저장해 Recall@5, MRR, nDCG@5를 비교합니다.

## Langfuse

`.env`에 `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`를 모두 설정하면 추적이 활성화됩니다. 질문과 문서 원문 대신 질문 해시, 후보 수, 결과 수 같은 메타데이터만 기본 기록하며 Langfuse 장애는 답변 실패로 전파하지 않습니다.

## 종료

```powershell
docker compose down
```

로컬 문서와 DB 데이터를 함께 지우려면 `docker compose down -v`를 사용합니다. 이 명령은 복구할 수 없는 로컬 데이터 삭제이므로 필요한 문서를 먼저 백업하세요.

## 설계 문서

- [시스템 설계](docs/superpowers/specs/2026-08-12-company-doc-rag-design.md)
- [구현 계획](docs/superpowers/plans/2026-08-12-company-doc-rag-implementation.md)
