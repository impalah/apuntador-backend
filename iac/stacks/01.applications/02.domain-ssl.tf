####################################################################
# ACM Certificate for API Domain
####################################################################

# Check if certificate already exists
data "aws_acm_certificate" "existing_certificate" {
  count       = var.domain_name != null && var.certificate_arn == null ? 1 : 0
  domain      = "*.apuntador.io"
  statuses    = ["ISSUED"]
  most_recent = true
}

# Create ACM certificate for *.apuntador.io only if it doesn't exist
resource "aws_acm_certificate" "api_certificate" {
  count             = var.domain_name != null && var.certificate_arn == null && try(data.aws_acm_certificate.existing_certificate[0].arn, null) == null ? 1 : 0
  domain_name       = "*.apuntador.io"
  validation_method = "DNS"

  subject_alternative_names = [
    "apuntador.io"
  ]

  tags = merge(
    {
      Name        = "${var.environment}-${var.project}-certificate"
      Environment = var.environment
      Project     = var.project
    },
    var.tags
  )

  lifecycle {
    create_before_destroy = true
  }
}

# DNS validation records for ACM certificate
# Solo crear si el certificado fue creado (no si ya existía)
resource "aws_route53_record" "certificate_validation" {
  for_each = var.domain_name != null && var.certificate_arn == null && try(data.aws_acm_certificate.existing_certificate[0].arn, null) == null && length(aws_acm_certificate.api_certificate) > 0 ? {
    for dvo in aws_acm_certificate.api_certificate[0].domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  } : {}

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = var.route53_zone_id
}

# Wait for certificate validation to complete
resource "aws_acm_certificate_validation" "api_certificate" {
  count                   = var.domain_name != null && var.certificate_arn == null && try(data.aws_acm_certificate.existing_certificate[0].arn, null) == null ? 1 : 0
  certificate_arn         = try(aws_acm_certificate.api_certificate[0].arn, "")
  validation_record_fqdns = [for record in aws_route53_record.certificate_validation : record.fqdn]

  timeouts {
    create = "10m"
  }
}

####################################################################
# VPC Link and API Gateway HTTP API
####################################################################

# VPC Link to connect API Gateway to private ALB
resource "aws_apigatewayv2_vpc_link" "apuntador" {
  name               = "${var.environment}-${var.project}-vpc-link"
  security_group_ids = []
  subnet_ids         = [for key, subnet_id in module.vpc.private_subnet_ids : subnet_id]

  tags = merge(
    {
      Name        = "${var.environment}-${var.project}-vpc-link"
      Environment = var.environment
      Project     = var.project
    },
    var.tags
  )
}

# API Gateway HTTP API
resource "aws_apigatewayv2_api" "apuntador" {
  name          = "${var.environment}-${var.project}-api"
  protocol_type = "HTTP"
  description   = "API Gateway for Apuntador OAuth Backend via VPC Link"

  # CORS Configuration - DISABLED
  # API Gateway no soporta esquemas personalizados (capacitor://, tauri://, ionic://)
  # FastAPI CORSMiddleware maneja todo el CORS incluyendo OPTIONS
  # cors_configuration {
  #   allow_origins     = var.cors_allowed_origins
  #   allow_methods     = var.cors_allowed_methods
  #   allow_headers     = var.cors_allowed_headers
  #   expose_headers    = var.cors_expose_headers
  #   max_age           = var.cors_max_age
  #   allow_credentials = var.cors_allow_credentials
  # }

  tags = merge(
    {
      Name        = "${var.environment}-${var.project}-api"
      Environment = var.environment
      Project     = var.project
    },
    var.tags
  )
}

# API Gateway Integration with private ALB via VPC Link
resource "aws_apigatewayv2_integration" "alb_integration" {
  api_id             = aws_apigatewayv2_api.apuntador.id
  integration_type   = "HTTP_PROXY"
  integration_method = "ANY"
  integration_uri    = aws_lb_listener.http.arn
  connection_type    = "VPC_LINK"
  connection_id      = aws_apigatewayv2_vpc_link.apuntador.id
  
  payload_format_version = "1.0"
  timeout_milliseconds   = 30000

  request_parameters = {
    "overwrite:path" = "$request.path"
  }

  depends_on = [
    aws_apigatewayv2_vpc_link.apuntador,
    aws_lb_listener.http
  ]
}

# Default route - forward all traffic to ALB
resource "aws_apigatewayv2_route" "default_route" {
  api_id    = aws_apigatewayv2_api.apuntador.id
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.alb_integration.id}"

  depends_on = [
    aws_apigatewayv2_integration.alb_integration
  ]
}

# Health check route (optional, for direct health checks)
resource "aws_apigatewayv2_route" "health_route" {
  api_id    = aws_apigatewayv2_api.apuntador.id
  route_key = "GET /health"
  target    = "integrations/${aws_apigatewayv2_integration.alb_integration.id}"

  depends_on = [
    aws_apigatewayv2_integration.alb_integration
  ]
}

####################################################################
# API Gateway Custom Domain
####################################################################

# Custom domain name for API Gateway
resource "aws_apigatewayv2_domain_name" "api_domain" {
  count       = var.domain_name != null ? 1 : 0
  domain_name = var.domain_name

  domain_name_configuration {
    certificate_arn = var.certificate_arn != null ? var.certificate_arn : try(data.aws_acm_certificate.existing_certificate[0].arn, aws_acm_certificate.api_certificate[0].arn)
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }

  tags = merge(
    {
      Name        = "${var.environment}-${var.project}-api-domain"
      Environment = var.environment
      Project     = var.project
    },
    var.tags
  )

  depends_on = [
    aws_acm_certificate_validation.api_certificate
  ]
}

# API Gateway stage (required for custom domain mapping)
resource "aws_apigatewayv2_stage" "default" {
  count       = var.domain_name != null ? 1 : 0
  api_id      = aws_apigatewayv2_api.apuntador.id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = 5000
    throttling_rate_limit  = 10000
  }

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway_logs[0].arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
      errorMessage   = "$context.error.message"
      integrationError = "$context.integrationErrorMessage"
    })
  }

  tags = merge(
    {
      Name        = "${var.environment}-${var.project}-api-stage"
      Environment = var.environment
      Project     = var.project
    },
    var.tags
  )

  depends_on = [
    aws_cloudwatch_log_group.api_gateway_logs
  ]
}

# Map custom domain to API Gateway stage
resource "aws_apigatewayv2_api_mapping" "api_mapping" {
  count       = var.domain_name != null ? 1 : 0
  api_id      = aws_apigatewayv2_api.apuntador.id
  domain_name = aws_apigatewayv2_domain_name.api_domain[0].id
  stage       = aws_apigatewayv2_stage.default[0].id

  depends_on = [
    aws_apigatewayv2_domain_name.api_domain,
    aws_apigatewayv2_stage.default
  ]
}

####################################################################
# Route 53 DNS Records
####################################################################

# A record pointing to API Gateway
resource "aws_route53_record" "api_a_record" {
  count   = var.domain_name != null ? 1 : 0
  zone_id = var.route53_zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_apigatewayv2_domain_name.api_domain[0].domain_name_configuration[0].target_domain_name
    zone_id                = aws_apigatewayv2_domain_name.api_domain[0].domain_name_configuration[0].hosted_zone_id
    evaluate_target_health = false
  }

  depends_on = [
    aws_apigatewayv2_domain_name.api_domain
  ]
}

# AAAA record (IPv6) pointing to API Gateway
resource "aws_route53_record" "api_aaaa_record" {
  count   = var.domain_name != null ? 1 : 0
  zone_id = var.route53_zone_id
  name    = var.domain_name
  type    = "AAAA"

  alias {
    name                   = aws_apigatewayv2_domain_name.api_domain[0].domain_name_configuration[0].target_domain_name
    zone_id                = aws_apigatewayv2_domain_name.api_domain[0].domain_name_configuration[0].hosted_zone_id
    evaluate_target_health = false
  }

  depends_on = [
    aws_apigatewayv2_domain_name.api_domain
  ]
}

####################################################################
# CloudWatch Log Groups
####################################################################

# Note: Lambda log group is created by the Lambda module itself
# See: modules/lambda/main.tf (aws_cloudwatch_log_group.lambda_log_group)

# API Gateway access logs
resource "aws_cloudwatch_log_group" "api_gateway_logs" {
  count             = var.domain_name != null ? 1 : 0
  name              = "/aws/apigateway/${var.environment}-${var.project}-api"
  retention_in_days = var.api_gateway_log_retention_days

  tags = merge(
    {
      Name        = "${var.environment}-${var.project}-api-gateway-logs"
      Environment = var.environment
      Project     = var.project
    },
    var.tags
  )
}

####################################################################
# Outputs
####################################################################

output "certificate_arn" {
  description = "ARN of the ACM certificate"
  value       = var.certificate_arn != null ? var.certificate_arn : (var.domain_name != null ? try(data.aws_acm_certificate.existing_certificate[0].arn, aws_acm_certificate.api_certificate[0].arn) : null)
}

output "api_domain_name" {
  description = "Custom domain name for API"
  value       = var.domain_name != null ? aws_apigatewayv2_domain_name.api_domain[0].domain_name : null
}

output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = var.domain_name != null ? "https://${var.domain_name}" : aws_apigatewayv2_api.apuntador.api_endpoint
}

output "api_gateway_id" {
  description = "API Gateway ID"
  value       = aws_apigatewayv2_api.apuntador.id
}

output "vpc_link_id" {
  description = "VPC Link ID for API Gateway to ALB connection"
  value       = aws_apigatewayv2_vpc_link.apuntador.id
}

output "cloudwatch_log_group_api_gateway" {
  description = "CloudWatch log group for API Gateway"
  value       = var.domain_name != null ? aws_cloudwatch_log_group.api_gateway_logs[0].name : null
}
