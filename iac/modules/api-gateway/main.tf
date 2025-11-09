# ###################################################################################
# Step by step API gateway
# ###################################################################################


resource "aws_apigatewayv2_vpc_link" "apigw_vpc_link" {

  count              = length(var.vpc_subnets_ids) > 0 ? 1 : 0
  name               = format("%s-%s-api-vpc-link", replace(var.environment, "_", "-"), lower(var.project), )
  security_group_ids = []
  subnet_ids         = var.vpc_subnets_ids
  tags = merge(
    { "Name" = format("%s-%s-api-vpc-link", replace(var.environment, "_", "-"), lower(var.project), ) },
    var.tags,
  )
}

resource "aws_apigatewayv2_api" "api" {

  # api_key_selection_expression = "$request.header.x-api-key"
  protocol_type = var.protocol_type
  # route_selection_expression   = "$request.method $request.path"
  tags = merge(
    { "Name" = format("%s-%s-api", replace(var.environment, "_", "-"), lower(var.project), ) },
    var.tags,
  )
  name = format("%s-%s-api", replace(var.environment, "_", "-"), lower(var.project), )

}


# resource "aws_apigatewayv2_integration" "apigw_integration" {

#   api_id             = aws_apigatewayv2_api.api.id
#   integration_type   = "HTTP_PROXY"
#   connection_id      = aws_apigatewayv2_vpc_link.apigw_vpc_link.id
#   connection_type    = "VPC_LINK"
#   description        = "VPC Integration"
#   integration_method = "ANY"
#   integration_uri    = var.aws_lb_listener_arn

#   # integration_uri = "arn:aws:elasticloadbalancing:us-east-2:550891793775:listener/app/magendas-magenda-cluster-ELB/6e9056724cdb62af/6cf80197fa414a05"
#   # timeout_milliseconds   = 30000
#   payload_format_version = "1.0"

#   depends_on = [
#     aws_apigatewayv2_api.api
#   ]


# }

resource "aws_apigatewayv2_integration" "apigw_integration" {
  api_id                 = aws_apigatewayv2_api.api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = var.lambda_function_arn
  description            = "Lambda Integration"
  integration_method     = "ANY"
  payload_format_version = "2.0"

  depends_on = [
    aws_apigatewayv2_api.api
  ]
}


resource "aws_lambda_permission" "apigw_lambda" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}



resource "aws_apigatewayv2_route" "apigw_route" {
  api_id = aws_apigatewayv2_api.api.id
  # api_key_required   = false
  # authorization_type = "NONE"
  route_key = "ANY /{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.apigw_integration.id}"

  depends_on = [
    aws_apigatewayv2_integration.apigw_integration
  ]


}

# Stage does not work using Terraform
# aws cli used instead

# resource "aws_apigatewayv2_stage" "ApiGatewayV2Stage" {
#   name = "$default"
#   # stage_variables {}
#   api_id = aws_apigatewayv2_api.api.id
#   default_route_settings {
#     logging_level            = "INFO"
#     detailed_metrics_enabled = false
#   }
#   auto_deploy = true
#   tags        = var.tags

#   depends_on = [
#     aws_apigatewayv2_route.apigw_route
#   ]


#   # Bug in terraform-aws-provider with perpetual diff
#   lifecycle {
#     ignore_changes = [deployment_id]
#   }

# }





# resource "aws_apigatewayv2_deployment" "ApiGatewayV2Deployment" {
#   api_id      = aws_apigatewayv2_api.api.id
#   description = "Automatic deployment triggered by changes to the Api configuration"

#   depends_on = ["aws_apigatewayv2_route.apigw_route", "aws_apigatewayv2_integration.apigw_integration"]

# }







