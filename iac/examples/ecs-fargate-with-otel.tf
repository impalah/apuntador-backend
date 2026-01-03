# Deployment de apuntador-backend en ECS Fargate con ADOT Collector sidecar
# Infraestructura totalmente gestionada (serverless containers)

##  ECS Cluster
resource "aws_ecs_cluster" "apuntador" {
  name = "apuntador-backend-cluster"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

##  CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/apuntador-backend"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "adot" {
  name              = "/ecs/adot-collector"
  retention_in_days = 7
}

##  Task Definition con sidecar ADOT
resource "aws_ecs_task_definition" "apuntador" {
  family                   = "apuntador-backend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"  # 0.25 vCPU
  memory                   = "512"  # 512 MB
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn
  
  container_definitions = jsonencode([
    # Container 1: Tu aplicación FastAPI
    {
      name      = "apuntador-backend"
      image     = "${var.ecr_repository_url}:latest"
      essential = true
      
      portMappings = [{
        containerPort = 8000
        protocol      = "tcp"
      }]
      
      environment = [
        { name = "OTEL_SERVICE_NAME", value = "apuntador-backend" },
        { name = "OTEL_EXPORTER_OTLP_ENDPOINT", value = "http://localhost:4317" },
        { name = "OTEL_EXPORTER_OTLP_PROTOCOL", value = "grpc" },
        { name = "OTEL_PROPAGATORS", value = "xray" },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "DEBUG", value = tostring(var.debug) },
        { name = "LOG_LEVEL", value = "INFO" },
        { name = "LOG_FORMAT", value = "json" }
      ]
      
      secrets = [
        {
          name      = "SECRET_KEY"
          valueFrom = aws_secretsmanager_secret.secret_key.arn
        },
        {
          name      = "GOOGLE_CLIENT_ID"
          valueFrom = "${aws_secretsmanager_secret.oauth_credentials.arn}:google_client_id::"
        },
        {
          name      = "GOOGLE_CLIENT_SECRET"
          valueFrom = "${aws_secretsmanager_secret.oauth_credentials.arn}:google_client_secret::"
        }
      ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.backend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "backend"
        }
      }
      
      dependsOn = [{
        containerName = "aws-otel-collector"
        condition     = "START"
      }]
    },
    
    # Container 2: ADOT Collector (sidecar)
    {
      name      = "aws-otel-collector"
      image     = "public.ecr.aws/aws-observability/aws-otel-collector:latest"
      essential = true
      
      command = ["--config=/etc/ecs/ecs-default-config.yaml"]
      
      portMappings = [
        { containerPort = 4317, protocol = "tcp" },  # OTLP gRPC
        { containerPort = 4318, protocol = "tcp" }   # OTLP HTTP
      ]
      
      environment = [
        { name = "AWS_REGION", value = var.aws_region }
      ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.adot.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "adot"
        }
      }
    }
  ])
}

##  IAM Roles

# Execution Role (pull images, write logs)
resource "aws_iam_role" "ecs_execution_role" {
  name = "apuntador-ecs-execution-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution_base" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_execution_secrets" {
  name = "secrets-access"
  role = aws_iam_role.ecs_execution_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "secretsmanager:GetSecretValue"
      ]
      Resource = [
        aws_secretsmanager_secret.secret_key.arn,
        aws_secretsmanager_secret.oauth_credentials.arn
      ]
    }]
  })
}

# Task Role (runtime permissions: X-Ray, CloudWatch)
resource "aws_iam_role" "ecs_task_role" {
  name = "apuntador-ecs-task-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_xray" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

resource "aws_iam_role_policy_attachment" "ecs_task_cloudwatch" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
}

##  Networking (VPC, Security Group)
resource "aws_security_group" "ecs_tasks" {
  name        = "apuntador-ecs-tasks-sg"
  description = "Security group for ECS tasks"
  vpc_id      = var.vpc_id
  
  ingress {
    description = "HTTP from ALB"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]  # Ajustar según tu VPC
  }
  
  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

##  ECS Service
resource "aws_ecs_service" "apuntador" {
  name            = "apuntador-backend-service"
  cluster         = aws_ecs_cluster.apuntador.id
  task_definition = aws_ecs_task_definition.apuntador.arn
  desired_count   = 1
  launch_type     = "FARGATE"
  
  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false
  }
  
  load_balancer {
    target_group_arn = aws_lb_target_group.apuntador.arn
    container_name   = "apuntador-backend"
    container_port   = 8000
  }
  
  depends_on = [aws_lb_listener.http]
}

##  Application Load Balancer
resource "aws_lb" "apuntador" {
  name               = "apuntador-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids
}

resource "aws_security_group" "alb" {
  name        = "apuntador-alb-sg"
  description = "Security group for ALB"
  vpc_id      = var.vpc_id
  
  ingress {
    description = "HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  ingress {
    description = "HTTPS from anywhere"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_lb_target_group" "apuntador" {
  name        = "apuntador-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"
  
  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 10
    timeout             = 5
    interval            = 30
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.apuntador.arn
  port              = "80"
  protocol          = "HTTP"
  
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.apuntador.arn
  }
}

##  Outputs
output "alb_dns_name" {
  value       = aws_lb.apuntador.dns_name
  description = "DNS name of the load balancer"
}

output "ecs_cluster_name" {
  value       = aws_ecs_cluster.apuntador.name
  description = "Name of the ECS cluster"
}

output "ecs_service_name" {
  value       = aws_ecs_service.apuntador.name
  description = "Name of the ECS service"
}

##  Variables
variable "ecr_repository_url" {
  description = "URL del repositorio ECR"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-1"
}

variable "debug" {
  description = "Enable debug mode"
  type        = bool
  default     = false
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for ECS tasks"
  type        = list(string)
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for ALB"
  type        = list(string)
}

##  Secrets (ejemplo, crear aparte)
resource "aws_secretsmanager_secret" "secret_key" {
  name = "apuntador/secret-key"
}

resource "aws_secretsmanager_secret" "oauth_credentials" {
  name = "apuntador/oauth-credentials"
}
