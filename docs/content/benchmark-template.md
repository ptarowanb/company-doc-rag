# 검색 품질 벤치마크 기록 방법

## 고정 조건

실험마다 다음 정보를 결과 파일과 함께 기록한다.

- Git 커밋 SHA
- 문서 데이터셋 버전과 SHA-256
- 질문 수와 정답 청크 작성 기준
- 임베딩 모델·차원
- 청크 최대 토큰·겹침 토큰
- 벡터·키워드 후보 수
- RRF `k`
- reranker 모델·후보 수·최종 근거 수
- 실행 장비와 측정 시각

## 검색 결과 파일 형식

```json
{"question":"연차 휴가는 며칠인가요?","retrieved_ids":["leave-policy#p3","leave-policy#p1"]}
```

벡터 단독, 하이브리드, reranker 결과를 각각 다른 파일로 저장하고 같은 데이터셋으로 실행한다.

```powershell
python -m evaluation.run --results evaluation/vector-results.jsonl
python -m evaluation.run --results evaluation/hybrid-results.jsonl
python -m evaluation.run --results evaluation/reranked-results.jsonl
```

## 결과 해석 규칙

- 예제 fixture의 1.0 수치는 평가기 검증용이며 실제 검색 성능으로 게시하지 않는다.
- 유료 API를 사용한 실행은 질문 수와 대략적인 토큰 사용량을 함께 기록한다.
- p50·p95는 최소 30회 이상 실행한 검색 시간과 첫 토큰 시간을 분리해 기록한다.
- 개선이 없는 실험도 설정과 결과를 남겨 선택 근거로 사용한다.

