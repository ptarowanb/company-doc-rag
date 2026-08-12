# 기술 블로그 3편: 로컬 RAG를 운영 환경으로 매핑하기

## 로컬에서 먼저 검증한 이유

공개 데모를 상시 운영하면 ALB, NAT Gateway, RDS, ElastiCache 같은 고정 비용이 생긴다. 포트폴리오 목표는 비용을 내는 것보다 재현 가능한 백엔드 설계와 운영 판단을 보여주는 것이므로 Docker Compose를 실행 기준으로 정하고 AWS는 Terraform 정적 검증 범위로 남겼다.

관련 구현 기록:

- `56fc494`: API·worker·pgvector·Redis Docker Compose
- `e386864`: VPC·ECS·RDS·ElastiCache·S3·Secrets Manager·CloudWatch Terraform

## 프로세스와 관리형 서비스 대응

| Docker Compose | AWS 운영 구조 |
|---|---|
| FastAPI | ALB 뒤 ECS Fargate API |
| Celery worker | ECS Fargate worker |
| PostgreSQL/pgvector | 사설 RDS PostgreSQL 16 |
| Redis | 사설 ElastiCache Redis |
| 업로드 볼륨 | S3 저장 어댑터 |
| `.env` | Secrets Manager |
| stdout 로그 | CloudWatch Logs·Alarms |

ALB만 공용 서브넷에 두고 ECS는 사설 애플리케이션 서브넷, DB와 Redis는 별도 데이터 서브넷에 둔다. 데이터 보안 그룹은 ECS 보안 그룹에서 오는 5432·6379 트래픽만 허용한다.

## 관측성과 개인정보 최소화

Langfuse span에는 질문 원문 대신 SHA-256 해시, 대상 문서 수, 검색 결과 수, 출처 수를 기본 기록한다. SDK 오류는 no-op span으로 바뀌어 사용자 답변을 실패시키지 않는다. CloudWatch에는 API·worker 로그 그룹과 ALB 5xx, ECS CPU, RDS CPU·여유 저장 공간 경보를 둔다.

## 적용하지 않은 이유와 검증 범위

다음 명령은 리소스를 만들지 않는다.

```powershell
terraform -chdir=infra/terraform init -backend=false
terraform -chdir=infra/terraform fmt -check -recursive
terraform -chdir=infra/terraform validate
```

실제 배포 전에 S3 파일 저장 어댑터, HTTPS·WAF, 운영용 다중 AZ, 백업 복원 훈련, secret 값 등록, 원격 Terraform state를 추가해야 한다. 이 차이를 문서에 명시해 “검증한 것”과 “설계만 한 것”을 구분했다.

## 비용을 줄이는 의사결정

개발 기본값은 작은 RDS·Redis 노드와 API·worker 각 1개지만 NAT Gateway와 ALB는 여전히 고정 비용이 발생한다. 따라서 상시 데모 대신 로컬 재현 명령, 아키텍처 문서, Terraform validate 결과, 테스트 결과를 포트폴리오 증빙으로 사용한다.

