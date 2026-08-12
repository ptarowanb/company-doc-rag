variable "project_name" {
  description = "리소스 이름과 태그에 사용할 프로젝트명"
  type        = string
  default     = "company-doc-rag"
}

variable "environment" {
  description = "배포 환경명"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS 리전"
  type        = string
  default     = "ap-northeast-2"
}

variable "vpc_cidr" {
  description = "VPC CIDR"
  type        = string
  default     = "10.40.0.0/16"
}

variable "container_image" {
  description = "ECS가 실행할 ECR 이미지 URI와 태그"
  type        = string
}

variable "allowed_cidr_blocks" {
  description = "ALB HTTP 접근을 허용할 CIDR 목록"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "db_instance_class" {
  description = "RDS 인스턴스 등급. apply 시 시간당 비용이 발생한다."
  type        = string
  default     = "db.t4g.micro"
}

variable "redis_node_type" {
  description = "ElastiCache 노드 등급. apply 시 시간당 비용이 발생한다."
  type        = string
  default     = "cache.t4g.micro"
}

variable "api_desired_count" {
  description = "API ECS 태스크 수"
  type        = number
  default     = 1
}

variable "worker_desired_count" {
  description = "worker ECS 태스크 수"
  type        = number
  default     = 1
}

variable "enable_nat_gateway" {
  description = "사설 ECS의 외부 API 호출용 NAT Gateway 생성 여부. 생성 시 고정 비용이 발생한다."
  type        = bool
  default     = true
}

variable "deletion_protection" {
  description = "ALB와 RDS 삭제 방지 활성화 여부"
  type        = bool
  default     = false
}

variable "skip_final_snapshot" {
  description = "RDS 삭제 시 최종 스냅샷 생략 여부. 운영 환경에서는 false를 권장한다."
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "CloudWatch 로그 보존 일수"
  type        = number
  default     = 14
}

