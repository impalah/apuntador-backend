#################################################################
# VPC and subnets
#################################################################

# Obtener las AZs disponibles en la región
data "aws_availability_zones" "available" {
  state = "available"
}

module "vpc" {
  source = "../../modules/vpc"

  vpc_name                 = "${var.environment}-${var.project}-vpc"
  cidr                     = "10.0.0.0/16" # 65,536 IPs
  enable_dns_hostnames     = true
  enable_dns_support       = true
  instance_tenancy         = "default"

  # Configuración de subnets usando subnets_configuration
  # 3 subnets públicas (una por AZ) - 251 IPs disponibles cada una
  # 3 subnets privadas (una por AZ) - 251 IPs disponibles cada una
  subnets_configuration = [
    # Subnets públicas
    {
      name              = "public-subnet-az1"
      cidr_block        = "10.0.1.0/24"   # 251 IPs disponibles
      availability_zone = data.aws_availability_zones.available.names[0]
      subnet_type       = "public"
    },
    {
      name              = "public-subnet-az2"
      cidr_block        = "10.0.2.0/24"   # 251 IPs disponibles
      availability_zone = data.aws_availability_zones.available.names[1]
      subnet_type       = "public"
    },
    {
      name              = "public-subnet-az3"
      cidr_block        = "10.0.3.0/24"   # 251 IPs disponibles
      availability_zone = data.aws_availability_zones.available.names[2]
      subnet_type       = "public"
    },
    # Subnets privadas (sin acceso a internet, sin NAT Gateway)
    {
      name              = "private-subnet-az1"
      cidr_block        = "10.0.11.0/24"  # 251 IPs disponibles
      availability_zone = data.aws_availability_zones.available.names[0]
      subnet_type       = "private"
    },
    {
      name              = "private-subnet-az2"
      cidr_block        = "10.0.12.0/24"  # 251 IPs disponibles
      availability_zone = data.aws_availability_zones.available.names[1]
      subnet_type       = "private"
    },
    {
      name              = "private-subnet-az3"
      cidr_block        = "10.0.13.0/24"  # 251 IPs disponibles
      availability_zone = data.aws_availability_zones.available.names[2]
      subnet_type       = "private"
    }
  ]

  tags = {
    Environment = var.environment
    CostCenter  = var.cost_center
    Project     = var.project
    Owner       = var.owner
    Deployment  = "Terraform"
    Date        = formatdate("YYYY-MM-DD", timestamp())
  }
}

#################################################################
# VPC Endpoints (para acceso a servicios AWS sin NAT Gateway)
# Coste estimado: ~$21/mes (3 Interface Endpoints x $7)
#################################################################

# Gateway Endpoint para DynamoDB (GRATIS)
resource "aws_vpc_endpoint" "dynamodb" {
  vpc_id            = module.vpc.vpc_id
  service_name      = "com.amazonaws.${var.region}.dynamodb"
  vpc_endpoint_type = "Gateway"
  
  route_table_ids = [
    for key, rt_id in module.vpc.private_route_table_ids : rt_id
  ]

  tags = {
    Name        = "${var.environment}-${var.project}-dynamodb-endpoint"
    Environment = var.environment
    CostCenter  = var.cost_center
    Project     = var.project
    Owner       = var.owner
  }
}

# Gateway Endpoint para S3 (GRATIS)
# Necesario también para que ECR pueda descargar layers de imágenes desde S3
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = module.vpc.vpc_id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  
  route_table_ids = [
    for key, rt_id in module.vpc.private_route_table_ids : rt_id
  ]

  tags = {
    Name        = "${var.environment}-${var.project}-s3-endpoint"
    Environment = var.environment
    CostCenter  = var.cost_center
    Project     = var.project
    Owner       = var.owner
  }
}

# Security Group para VPC Interface Endpoints
resource "aws_security_group" "vpc_endpoints" {
  name_prefix = "${var.environment}-${var.project}-vpc-endpoints-"
  description = "Security group for VPC Interface Endpoints"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description = "HTTPS from VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.environment}-${var.project}-vpc-endpoints-sg"
    Environment = var.environment
    Project     = var.project
  }
}

# Interface Endpoint para ECR API (~$7/mes)
# Necesario para que ECS pueda autenticarse con ECR
resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id              = module.vpc.vpc_id
  service_name        = "com.amazonaws.${var.region}.ecr.api"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  
  subnet_ids = [
    for key, subnet_id in module.vpc.private_subnet_ids : subnet_id
  ]

  security_group_ids = [aws_security_group.vpc_endpoints.id]

  tags = {
    Name        = "${var.environment}-${var.project}-ecr-api-endpoint"
    Environment = var.environment
    Project     = var.project
  }
}

# Interface Endpoint para ECR Docker (~$7/mes)
# Necesario para que ECS pueda hacer pull de imágenes desde ECR
resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id              = module.vpc.vpc_id
  service_name        = "com.amazonaws.${var.region}.ecr.dkr"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  
  subnet_ids = [
    for key, subnet_id in module.vpc.private_subnet_ids : subnet_id
  ]

  security_group_ids = [aws_security_group.vpc_endpoints.id]

  tags = {
    Name        = "${var.environment}-${var.project}-ecr-dkr-endpoint"
    Environment = var.environment
    Project     = var.project
  }
}

# Interface Endpoint para CloudWatch Logs (~$7/mes)
# Para envío de logs desde ECS tasks
resource "aws_vpc_endpoint" "logs" {
  vpc_id              = module.vpc.vpc_id
  service_name        = "com.amazonaws.${var.region}.logs"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  
  subnet_ids = [
    for key, subnet_id in module.vpc.private_subnet_ids : subnet_id
  ]

  security_group_ids = [aws_security_group.vpc_endpoints.id]

  tags = {
    Name        = "${var.environment}-${var.project}-logs-endpoint"
    Environment = var.environment
    Project     = var.project
  }
}

#################################################################
# Log group
#################################################################

module "backend_services_logs_group" {
  source           = "../../modules/cloudwatch"
  environment      = var.environment
  project          = var.project
  log_group_prefix = "ecs"
  log_group_name   = "${var.environment}-apuntador-backend"
  retention_days   = 7

  tags = {
    Environment = var.environment
    CostCenter  = var.cost_center
    Project     = var.project
    Owner       = var.owner
    Deployment  = lower("Terraform")
    Date        = formatdate("YYYY-MM-DD", timestamp())
  }

}

module "adot_collector_logs_group" {
  source           = "../../modules/cloudwatch"
  environment      = var.environment
  project          = var.project
  log_group_prefix = "ecs"
  log_group_name   = "${var.environment}-adot-collector"
  retention_days   = 7

  tags = {
    Environment = var.environment
    CostCenter  = var.cost_center
    Project     = var.project
    Owner       = var.owner
    Deployment  = lower("Terraform")
    Date        = formatdate("YYYY-MM-DD", timestamp())
  }

}



