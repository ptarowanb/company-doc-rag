# LinkedIn 게시물 초안

사내 PDF를 근거와 함께 검색하고 답변하는 RAG 백엔드를 만들었습니다.

이번 프로젝트에서는 단순히 “문서를 벡터 DB에 저장하고 LLM을 호출”하는 데서 멈추지 않고, 실제 서비스에서 문제가 되는 지점을 중심으로 구현했습니다.

- PDF 비동기 수집과 실패 상태 관리
- 페이지 범위를 보존하는 토큰 청킹
- PostgreSQL/pgvector + pg_trgm 하이브리드 검색
- RRF 결합과 다국어 cross-encoder reranker
- LLM 답변과 분리된 구조화 출처
- FastAPI SSE 스트리밍
- Redis 작업 큐·검색 캐시 세대 무효화
- 선택적 Langfuse 추적과 검색 평가 도구
- Docker Compose 로컬 재현
- 비용을 발생시키지 않는 AWS Terraform 정적 검증

가장 중요하게 본 부분은 “그럴듯한 답변”보다 “어떤 근거를 왜 선택했는지 재현할 수 있는가”였습니다. 그래서 벡터 단독, 하이브리드, reranker 결과를 동일한 JSONL 질문 세트에서 Recall@5·MRR·nDCG@5로 비교할 수 있게 만들었습니다.

AWS 공개 데모는 운영 비용 때문에 열지 않았습니다. 대신 로컬 실행 방법, 테스트, AWS 대응 아키텍처와 Terraform `validate` 절차를 저장소에 함께 남겼습니다.

기술 블로그에서는 다음 세 편으로 구현 판단을 정리합니다.

1. 모듈형 RAG 백엔드와 비동기 문서 수집
2. RRF·reranker를 이용한 하이브리드 검색
3. Docker Compose에서 AWS 운영 구조로의 매핑

#Python #FastAPI #RAG #LLM #pgvector #PostgreSQL #Redis #Docker #Terraform #AWS

## 게시 연결 방법

1. GitHub 저장소 README를 먼저 공개하고 로컬 실행·평가 명령이 정상인지 확인한다.
2. LinkedIn 본문에는 저장소 URL 하나와 핵심 아키텍처 이미지를 첨부한다.
3. 기술 블로그 각 편에는 위에 적힌 관련 커밋 해시와 README의 재현 명령을 링크한다.
4. 글을 게시한 뒤 README의 “콘텐츠” 섹션에 실제 글 URL을 추가한다.
5. LinkedIn 게시물 댓글에 블로그 1편 URL을 추가하고 후속 글은 같은 스레드에 연결한다.

