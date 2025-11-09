
resource "aws_ecr_repository" "repository" {
  encryption_configuration {
    encryption_type = var.encryption_type
  }

  image_scanning_configuration {
    scan_on_push = var.scan_on_push
  }

  image_tag_mutability = var.image_tag_mutability
  name                 = var.name
}

locals {
  policy_content = var.public ? file("${path.module}/ecr_public_policy.json") : var.policy
}

resource "aws_ecr_repository_policy" "repository_policy" {
  count      = local.policy_content != null ? 1 : 0
  repository = aws_ecr_repository.repository.name
  policy     = local.policy_content
}

resource "aws_ecr_lifecycle_policy" "repository_lifecycle_policy" {
  count      = var.lifecycle_policy != null ? 1 : 0
  policy     = var.lifecycle_policy
  repository = aws_ecr_repository.repository.name
}

