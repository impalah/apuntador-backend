# Deployment de apuntador-backend en AWS Lambda con OpenTelemetry
# SIN necesidad de containers adicionales

## 📦 Stack de Terraform para Lambda + ADOT Layer

resource "aws_lambda_function" "apuntador_backend" {
  function_name = "apuntador-backend"
  role          = aws_iam_role.lambda_role.arn
  
  # Tu imagen Docker existente
  package_type = "Image"
  image_uri    = "${var.ecr_repository_url}:latest"
  
  # ADOT Lambda Layer - Incluye OpenTelemetry + Collector
  # ARN para Python 3.12 en eu-west-1
  layers = [
    "arn:aws:lambda:eu-west-1:901920570463:layer:aws-otel-python-amd64-ver-1-25-0:1"
  ]
  
  # Configuración de recursos
  memory_size = 512
  timeout     = 30
  
  # Variables de entorno para OpenTelemetry
  environment {
    variables = {
      # OpenTelemetry auto-instrumentation
      AWS_LAMBDA_EXEC_WRAPPER = "/opt/otel-instrument"
      
      # Service identification
      OTEL_SERVICE_NAME = "apuntador-backend"
      OTEL_RESOURCE_ATTRIBUTES = "service.version=1.0.0,deployment.environment=production"
      
      # AWS X-Ray propagation
      OTEL_PROPAGATORS = "xray"
      
      # Python specific
      OTEL_PYTHON_DISTRO = "aws_distro"
      OTEL_PYTHON_CONFIGURATOR = "aws_configurator"
      
      # Logging correlation
      OTEL_PYTHON_LOG_CORRELATION = "true"
      
      # Tus variables existentes
      DEBUG                = var.debug
      SECRET_KEY          = var.secret_key
      GOOGLE_CLIENT_ID    = var.google_client_id
      # ... resto de variables
    }
  }
  
  # Tracing configuration (activa X-Ray)
  tracing_config {
    mode = "Active"
  }
}

# Variables necesarias (agregar a tu variables.tf)
variable "ecr_repository_url" {
  description = "URL del repositorio ECR con la imagen Docker"
  type        = string
}

variable "debug" {
  description = "Enable debug mode"
  type        = bool
  default     = false
}

variable "secret_key" {
  description = "Secret key for signing tokens"
  type        = string
  sensitive   = true
}

variable "google_client_id" {
  description = "Google OAuth client ID"
  type        = string
}

# IAM Role para Lambda con permisos X-Ray
resource "aws_iam_role" "lambda_role" {
  name = "apuntador-backend-lambda-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# Política para escribir trazas a X-Ray
resource "aws_iam_role_policy_attachment" "lambda_xray" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# Política básica de Lambda (logs)
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/apuntador-backend"
  retention_in_days = 7
}

# API Gateway integration (si usas API Gateway)
resource "aws_apigatewayv2_integration" "lambda" {
  api_id = aws_apigatewayv2_api.api.id
  
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.apuntador_backend.invoke_arn
  
  payload_format_version = "2.0"
}

# Output
output "function_url" {
  value = aws_lambda_function.apuntador_backend.invoke_arn
}
