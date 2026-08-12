output "alb_dns_name" {
  description = "API ALB DNS 이름"
  value       = aws_lb.api.dns_name
}

output "document_bucket_name" {
  description = "원본 문서용 S3 버킷 이름"
  value       = aws_s3_bucket.documents.id
}

output "ecr_repository_url" {
  description = "애플리케이션 ECR 저장소 URL"
  value       = aws_ecr_repository.app.repository_url
}

output "secret_arns_to_populate" {
  description = "apply 후 값을 별도로 등록해야 하는 Secrets Manager ARN"
  value = {
    openai_api_key      = aws_secretsmanager_secret.openai_api_key.arn
    database_url        = aws_secretsmanager_secret.database_url.arn
    langfuse_public_key = aws_secretsmanager_secret.langfuse_public_key.arn
    langfuse_secret_key = aws_secretsmanager_secret.langfuse_secret_key.arn
  }
}

