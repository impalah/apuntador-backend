################################################################################
# Main function configuration
################################################################################

# Role and policy configurations

resource "aws_iam_role" "lambda_exec_role" {
  name               = format("%s-%s-%s-lambda_exec_role", var.environment, var.project, var.function_name)
  assume_role_policy = file("${path.module}/policies/lambda-role-policy.json")

  # lifecycle {
  #   ignore_changes = [
  #     name,
  #     assume_role_policy
  #   ]
  # }
}


data "aws_iam_policy_document" "lambda_exec_role_policy_document" {
  statement {
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = [
      "arn:aws:logs:*:*:log-group:/aws/lambda/${var.function_name}:*"
    ]
  }

}

resource "aws_iam_role_policy" "lambda_exec_role_policy" {
  name   = format("%s-%s-lambda_exec_policy", var.environment, var.project)
  role   = aws_iam_role.lambda_exec_role.id
  policy = data.aws_iam_policy_document.lambda_exec_role_policy_document.json

  # lifecycle {
  #   ignore_changes = [
  #     id,
  #     name,
  #     role,
  #     policy
  #   ]
  # }

}

# # Role to connect to VPC
# resource "aws_iam_role_policy" "lambda_vpc_access" {
#   name = "lambda_vpc_access"
#   role = aws_iam_role.lambda_exec_role.id

#   policy = file("${path.module}/policies/lambda-exec-role-policy.json")

#   lifecycle {
#     ignore_changes = [
#       name,
#       role,
#       policy
#     ]
#   }
# }

# resource "aws_security_group" "lambda_sg" {
#   name        = format("%s-%s-%s-lambda_sg", var.environment, var.project, var.function_name)
#   description = "Security group for Lambda function to access RDS"
#   vpc_id      = var.vpc_id


#   dynamic "ingress" {
#     for_each = var.ports
#     content {
#       from_port = ingress.value
#       to_port   = ingress.value
#       protocol  = "tcp"
#       cidr_blocks = [
#         "0.0.0.0/0"
#       ]
#       # TODO: only allow from the load balancer
#       # security_groups = [
#       #   "${aws_security_group.ServiceLBSecurityGroup.id}"
#       # ]
#       description = format("Allow from anyone on port %d", ingress.value)
#     }
#   }



#   egress {
#     from_port   = 0
#     to_port     = 0
#     protocol    = "-1"
#     cidr_blocks = ["0.0.0.0/0"]
#   }
# }



# Cloudwatch log group (create BEFORE Lambda function)
resource "aws_cloudwatch_log_group" "lambda_log_group" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = var.log_retention_days
}

# Lambda function from ECR image
resource "aws_lambda_function" "lambda_function" {

  architectures = var.function_architectures

  dynamic "environment" {
    for_each = length(var.env_variables) > 0 ? [var.env_variables] : []
    content {
      variables = environment.value
    }
  }

  ephemeral_storage {
    size = var.function_storage
  }

  function_name                  = var.function_name
  image_uri                      = var.image
  memory_size                    = var.function_memory
  package_type                   = "Image"
  reserved_concurrent_executions = "-1"
  role                           = aws_iam_role.lambda_exec_role.arn
  skip_destroy                   = "false"
  timeout                        = var.function_timeout
  
  # Lambda Layers - NOT supported for container images
  # For container images, include dependencies in the Dockerfile
  # layers                         = var.layers

  tracing_config {
    mode = var.tracing_mode
  }

  # image_config {
  #   command = [var.function_cmd]
  # }

  # vpc_config {
  #   subnet_ids         = var.vpc_subnets_ids
  #   security_group_ids = [aws_security_group.lambda_sg.id]
  # }

  tags = merge(
    # { "Name" = format("%s_%s", var.environment, var.function_name) },
    { "Name" = var.function_name },
    var.tags,
  )

  # Ensure log group exists before Lambda
  depends_on = [
    aws_cloudwatch_log_group.lambda_log_group,
    aws_iam_role_policy.lambda_exec_role_policy
  ]

  # lifecycle {
  #   ignore_changes = [
  #     image_uri,
  #     last_modified,
  #     role,
  #     timeout,
  #     environment,
  #     vpc_config
  #   ]
  # }

}

# resource "aws_lambda_permission" "allow_cloudwatch_to_call_lambda" {
#   statement_id  = format("%s_%s_AllowExecutionFromCloudWatch", var.environment, var.function_name)
#   action        = "lambda:InvokeFunction"
#   function_name = aws_lambda_function.lambda_function.arn
#   principal     = "events.amazonaws.com"
#   source_arn    = aws_cloudwatch_event_rule.lambda_event_rule.arn
# }

# resource "aws_lambda_permission" "allow_sns" {
#   statement_id  = format("%s_%s_AllowExecutionFromSNS", var.environment, var.function_name)
#   action        = "lambda:InvokeFunction"
#   function_name = aws_lambda_function.lambda_function.function_name
#   principal     = "sns.amazonaws.com"
#   source_arn    = var.aws_sns_topic_arn
# }
