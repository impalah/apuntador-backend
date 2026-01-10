####################################################################
# ECS Fargate Deployment with ADOT Collector Sidecar
####################################################################

####################################################################
# ECS Cluster
####################################################################

resource "aws_ecs_cluster" "apuntador" {
  name = "${var.environment}-${var.project}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Environment = var.environment
    Project     = var.project
    CostCenter  = var.cost_center
  }
}

####################################################################
# ECS Cluster Capacity Providers
####################################################################

resource "aws_ecs_cluster_capacity_providers" "apuntador" {
  cluster_name = aws_ecs_cluster.apuntador.name

  capacity_providers = var.enable_fargate_spot ? ["FARGATE", "FARGATE_SPOT"] : ["FARGATE"]

  dynamic "default_capacity_provider_strategy" {
    for_each = var.enable_fargate_spot ? [1] : []
    content {
      capacity_provider = "FARGATE"
      weight            = var.fargate_spot_base_capacity
      base              = var.fargate_spot_min_fargate_tasks
    }
  }

  dynamic "default_capacity_provider_strategy" {
    for_each = var.enable_fargate_spot ? [1] : []
    content {
      capacity_provider = "FARGATE_SPOT"
      weight            = var.fargate_spot_weight
    }
  }
}

####################################################################
# IAM Roles and Policies
####################################################################

# Execution Role (pull images from ECR, write logs to CloudWatch, read secrets)
resource "aws_iam_role" "ecs_execution_role" {
  name = "${var.environment}-${var.project}-ecs-execution-role"
  
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

  tags = {
    Environment = var.environment
    Project     = var.project
  }
}

# Attach base ECS execution policy
resource "aws_iam_role_policy_attachment" "ecs_execution_base" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Task Role (runtime permissions: DynamoDB, S3, Secrets Manager, X-Ray, CloudWatch)
resource "aws_iam_role" "ecs_task_role" {
  name = "${var.environment}-${var.project}-ecs-task-role"
  
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

  tags = {
    Environment = var.environment
    Project     = var.project
  }
}

# Attach X-Ray write access for OpenTelemetry
resource "aws_iam_role_policy_attachment" "ecs_task_xray" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# Policy for DynamoDB access
resource "aws_iam_role_policy" "ecs_task_dynamodb" {
  name = "dynamodb-access"
  role = aws_iam_role.ecs_task_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:DescribeTable",
        "dynamodb:CreateTable"
      ]
      Resource = [
        "arn:aws:dynamodb:${var.region}:*:table/${var.dynamodb_table_name}",
        "arn:aws:dynamodb:${var.region}:*:table/${var.dynamodb_table_name}/*"
      ]
    }]
  })
}

# Policy for S3 access
resource "aws_iam_role_policy" "ecs_task_s3" {
  name = "s3-access"
  role = aws_iam_role.ecs_task_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ]
      Resource = [
        "arn:aws:s3:::${var.s3_bucket_name}",
        "arn:aws:s3:::${var.s3_bucket_name}/*"
      ]
    }]
  })
}

# Policy for Secrets Manager access
resource "aws_iam_role_policy" "ecs_task_secrets" {
  name = "secrets-access"
  role = aws_iam_role.ecs_task_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret",
        "secretsmanager:ListSecrets"
      ]
      Resource = [
        "arn:aws:secretsmanager:${var.region}:*:secret:${var.secrets_prefix}/*"
      ]
    }]
  })
}

####################################################################
# Security Groups
####################################################################

# Security Group for ALB (private, only accessible from VPC Link)
resource "aws_security_group" "alb" {
  name_prefix = "${var.environment}-${var.project}-alb-"
  description = "Security group for Application Load Balancer (private)"
  vpc_id      = module.vpc.vpc_id
  
  ingress {
    description = "HTTP from VPC (API Gateway VPC Link)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = [module.vpc.vpc_cidr_block]
  }
  
  ingress {
    description = "HTTPS from VPC (API Gateway VPC Link)"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [module.vpc.vpc_cidr_block]
  }
  
  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.environment}-${var.project}-alb-sg"
    Environment = var.environment
    Project     = var.project
  }
}

# Security Group for ECS Tasks (private)
resource "aws_security_group" "ecs_tasks" {
  name_prefix = "${var.environment}-${var.project}-ecs-tasks-"
  description = "Security group for ECS Fargate tasks"
  vpc_id      = module.vpc.vpc_id
  
  ingress {
    description     = "HTTP from ALB only"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  
  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.environment}-${var.project}-ecs-tasks-sg"
    Environment = var.environment
    Project     = var.project
  }
}

####################################################################
# Application Load Balancer
####################################################################

resource "aws_lb" "apuntador" {
  name               = "${var.environment}-${var.project}-alb"
  internal           = true  # ALB privado, solo accesible desde VPC Link
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = [for key, subnet_id in module.vpc.private_subnet_ids : subnet_id]

  enable_deletion_protection = false
  enable_http2              = true
  enable_cross_zone_load_balancing = true

  tags = {
    Name        = "${var.environment}-${var.project}-alb"
    Environment = var.environment
    Project     = var.project
    CostCenter  = var.cost_center
  }
}

resource "aws_lb_target_group" "apuntador" {
  name        = "${var.environment}-${var.project}-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"
  
  health_check {
    enabled             = true
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    matcher             = "200"
  }

  deregistration_delay = 30

  tags = {
    Name        = "${var.environment}-${var.project}-tg"
    Environment = var.environment
    Project     = var.project
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

# TODO: Add HTTPS listener with ACM certificate
# resource "aws_lb_listener" "https" {
#   load_balancer_arn = aws_lb.apuntador.arn
#   port              = "443"
#   protocol          = "HTTPS"
#   ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
#   certificate_arn   = var.acm_certificate_arn
#   
#   default_action {
#     type             = "forward"
#     target_group_arn = aws_lb_target_group.apuntador.arn
#   }
# }

####################################################################
# ECS Task Definition
####################################################################

resource "aws_ecs_task_definition" "apuntador" {
  family                   = "${var.environment}-${var.project}-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn
  
  # Especificar arquitectura explícitamente
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"  # Cambiar a "ARM64" si necesitas Graviton
  }
  
  container_definitions = jsonencode([
    # Container 1: Main FastAPI application
    {
      name      = "apuntador-backend"
      image     = var.api_image
      essential = true
      
      portMappings = [{
        containerPort = 8000
        protocol      = "tcp"
      }]
      
      environment = [
        # Application Configuration
        { name = "HOST", value = "0.0.0.0" },
        { name = "PORT", value = "8000" },
        { name = "DEBUG", value = tostring(var.debug) },
        { name = "SECRET_KEY", value = var.secret_key },
        { name = "ALLOWED_ORIGINS", value = var.allowed_origins },
        { name = "ENABLE_DOCS", value = tostring(var.enable_docs) },
        
        # OpenTelemetry Configuration
        { name = "OTEL_ENABLED", value = "true" },
        { name = "OTEL_SERVICE_NAME", value = "apuntador-api" },
        { name = "OTEL_RESOURCE_ATTRIBUTES", value = "service.version=1.0.0,deployment.environment=${var.environment}" },
        { name = "OTEL_EXPORTER_OTLP_ENDPOINT", value = "http://localhost:4317" },
        { name = "OTEL_EXPORTER_OTLP_PROTOCOL", value = "grpc" },
        { name = "OTEL_PROPAGATORS", value = "xray" },
        { name = "OTEL_PYTHON_DISTRO", value = "aws_distro" },
        { name = "OTEL_PYTHON_CONFIGURATOR", value = "aws_configurator" },
        { name = "OTEL_PYTHON_LOG_CORRELATION", value = "true" },
        { name = "OTEL_TRACES_SAMPLER", value = "parentbased_traceidratio" },
        { name = "OTEL_TRACES_SAMPLER_ARG", value = "0.1" },
        
        # Logging Configuration
        { name = "LOG_LEVEL", value = var.log_level },
        { name = "LOG_FORMAT", value = var.log_format },
        { name = "ENABLE_REQUEST_LOGGING", value = "true" },
        
        # Cloud Provider Configuration
        { name = "ENABLED_CLOUD_PROVIDERS", value = var.enabled_cloud_providers },
        
        # Infrastructure Provider (AWS)
        { name = "INFRASTRUCTURE_PROVIDER", value = "aws" },
        { name = "AWS_REGION", value = var.region },
        { name = "AWS_DYNAMODB_TABLE", value = var.dynamodb_table_name },
        { name = "AWS_S3_BUCKET", value = var.s3_bucket_name },
        { name = "AWS_SECRETS_PREFIX", value = var.secrets_prefix },
        { name = "AUTO_CREATE_RESOURCES", value = tostring(var.auto_create_resources) },
        
        # Google Drive OAuth
        { name = "GOOGLE_CLIENT_ID", value = var.google_client_id },
        { name = "GOOGLE_CLIENT_SECRET", value = var.google_client_secret },
        { name = "GOOGLE_REDIRECT_URI", value = var.google_redirect_uri },
        
        # Dropbox OAuth
        { name = "DROPBOX_CLIENT_ID", value = var.dropbox_client_id },
        { name = "DROPBOX_CLIENT_SECRET", value = var.dropbox_client_secret },
        { name = "DROPBOX_REDIRECT_URI", value = var.dropbox_redirect_uri }
      ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = module.backend_services_logs_group.logs_group_name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "backend"
        }
      }
      
      dependsOn = [{
        containerName = "aws-otel-collector"
        condition     = "START"
      }]
    },
    
    # Container 2: AWS Distro for OpenTelemetry Collector (sidecar)
    {
      name      = "aws-otel-collector"
      image     = var.adot_image
      essential = true
      
      command = ["--config=/etc/ecs/ecs-default-config.yaml"]
      
      portMappings = [
        { containerPort = 4317, protocol = "tcp" },  # OTLP gRPC
        { containerPort = 4318, protocol = "tcp" }   # OTLP HTTP
      ]
      
      environment = [
        { name = "AWS_REGION", value = var.region }
      ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = module.adot_collector_logs_group.logs_group_name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "adot"
        }
      }
    }
  ])

  tags = {
    Environment = var.environment
    Project     = var.project
  }
}

####################################################################
# ECS Service
####################################################################

resource "aws_ecs_service" "apuntador" {
  name            = "${var.environment}-${var.project}-service"
  cluster         = aws_ecs_cluster.apuntador.id
  task_definition = aws_ecs_task_definition.apuntador.arn
  desired_count   = var.desired_count
  
  # Remove launch_type when using capacity provider strategy
  # launch_type is mutually exclusive with capacity_provider_strategy
  
  # Capacity Provider Strategy (FARGATE + FARGATE_SPOT mix)
  dynamic "capacity_provider_strategy" {
    for_each = var.enable_fargate_spot ? [1] : []
    content {
      capacity_provider = "FARGATE"
      weight            = var.fargate_spot_base_capacity
      base              = var.fargate_spot_min_fargate_tasks
    }
  }

  dynamic "capacity_provider_strategy" {
    for_each = var.enable_fargate_spot ? [1] : []
    content {
      capacity_provider = "FARGATE_SPOT"
      weight            = var.fargate_spot_weight
    }
  }

  # Fallback to FARGATE when Spot is disabled
  launch_type = var.enable_fargate_spot ? null : "FARGATE"
  
  network_configuration {
    subnets          = [for key, subnet_id in module.vpc.private_subnet_ids : subnet_id]
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = false  # Tasks en subnet privada
  }
  
  load_balancer {
    target_group_arn = aws_lb_target_group.apuntador.arn
    container_name   = "apuntador-backend"
    container_port   = 8000
  }

  # Health check grace period
  health_check_grace_period_seconds = 60

  depends_on = [
    aws_lb_listener.http,
    aws_iam_role_policy.ecs_task_dynamodb,
    aws_iam_role_policy.ecs_task_s3,
    aws_iam_role_policy.ecs_task_secrets,
    aws_ecs_cluster_capacity_providers.apuntador
  ]

  tags = {
    Environment = var.environment
    Project     = var.project
  }
}

####################################################################
# Outputs
####################################################################

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.apuntador.dns_name
}

output "alb_zone_id" {
  description = "Zone ID of the Application Load Balancer"
  value       = aws_lb.apuntador.zone_id
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.apuntador.name
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.apuntador.name
}

output "ecs_task_definition_arn" {
  description = "ARN of the ECS task definition"
  value       = aws_ecs_task_definition.apuntador.arn
}

output "alb_listener_arn" {
  description = "ARN of the ALB HTTP listener"
  value       = aws_lb_listener.http.arn
}

output "alb_security_group_id" {
  description = "Security Group ID of the ALB"
  value       = aws_security_group.alb.id
}

output "ecs_security_group_id" {
  description = "Security Group ID of the ECS tasks"
  value       = aws_security_group.ecs_tasks.id
}


