resource "aws_vpc_endpoint" "lambda_endpoint" {
  vpc_id            = var.vpc_id
  service_name      = var.endpoint_service_name
  vpc_endpoint_type = var.endpoint_type

  service_name      = "com.amazonaws.${var.region}.lambda"
  vpc_endpoint_type = "Interface"


  security_group_ids = var.security_group_ids
  subnet_ids         = var.vpc_subnets_ids

  private_dns_enabled = true
}
