# 기여 규칙

## 개발 환경

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m pytest -q
```

기능과 버그 수정은 실패하는 테스트를 먼저 추가하고, 테스트가 예상한 이유로 실패하는지 확인한 뒤 최소 구현을 작성한다.

## 언어

- 코드 식별자는 Python 관례에 맞춰 영문을 사용한다.
- 주석, docstring, README, 설계·운영 문서는 한글을 기본으로 한다.
- 예외 메시지와 API 사용자 메시지는 한글로 작성한다.

## 커밋 메시지

타입은 영문 축약어, 요약은 한글 명령형으로 작성한다.

```text
feat: PDF 문서 수집 파이프라인 구현
fix: 중복 업로드 원본 파일 정리
refactor: 검색 포트 인터페이스 분리
docs: 로컬 실행 방법 보완
test: RRF 중복 후보 회귀 테스트 추가
chore: 개발 도구 설정 갱신
perf: reranker 후보 수 제한
ci: 정적 검사 워크플로 추가
build: Docker 이미지 구성
```

실제 완료된 작업 단위로 커밋하며 작성자와 날짜를 조작하지 않는다. API 키, `.env`, AWS 자격 증명, 실제 사내 문서는 커밋하지 않는다.

## 검증

```powershell
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m mypy src
$env:OPENAI_API_KEY='test-key'; docker compose config -q
terraform -chdir=infra/terraform fmt -check -recursive
terraform -chdir=infra/terraform validate
```

