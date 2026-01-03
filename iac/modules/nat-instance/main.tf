# NAT Instance Module
# Provides internet connectivity for private subnets using a cost-effective EC2 instance

data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-kernel-*-arm64"]
  }

  filter {
    name   = "architecture"
    values = ["arm64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Security Group for NAT Instance
resource "aws_security_group" "nat_instance" {
  name_prefix = "${var.name_prefix}-nat-instance-"
  description = "Security group for NAT instance"
  vpc_id      = var.vpc_id

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic to internet"
  }

  # Allow inbound traffic from private subnets
  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = var.private_subnet_cidrs
    description = "Allow all inbound traffic from private subnets"
  }

  # Allow SSH from specific CIDR (optional, for debugging)
  dynamic "ingress" {
    for_each = var.ssh_allowed_cidr != "" ? [1] : []
    content {
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = [var.ssh_allowed_cidr]
      description = "Allow SSH for administration"
    }
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-nat-instance-sg"
    }
  )
}

# IAM Role for NAT Instance (allows SSM Session Manager)
resource "aws_iam_role" "nat_instance" {
  name_prefix = "${var.name_prefix}-nat-instance-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# Attach SSM managed policy (for Session Manager access)
resource "aws_iam_role_policy_attachment" "nat_instance_ssm" {
  role       = aws_iam_role.nat_instance.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Instance Profile
resource "aws_iam_instance_profile" "nat_instance" {
  name_prefix = "${var.name_prefix}-nat-instance-"
  role        = aws_iam_role.nat_instance.name

  tags = var.tags
}

# Launch Template for NAT Instance
resource "aws_launch_template" "nat_instance" {
  name_prefix   = "${var.name_prefix}-nat-instance-"
  image_id      = data.aws_ami.amazon_linux_2023.id
  instance_type = var.instance_type

  iam_instance_profile {
    arn = aws_iam_instance_profile.nat_instance.arn
  }

  network_interfaces {
    associate_public_ip_address = true
    delete_on_termination       = true
    security_groups             = [aws_security_group.nat_instance.id]
    # Disable source/destination check (required for NAT functionality)
  }

  user_data = base64encode(templatefile("${path.module}/user-data.sh", {
    enable_monitoring = var.enable_cloudwatch_metrics
  }))

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required" # IMDSv2 only
    http_put_response_hop_limit = 1
  }

  monitoring {
    enabled = var.enable_detailed_monitoring
  }

  tag_specifications {
    resource_type = "instance"
    tags = merge(
      var.tags,
      {
        Name = "${var.name_prefix}-nat-instance"
      }
    )
  }

  tags = var.tags
}

# Auto Scaling Group (for high availability)
resource "aws_autoscaling_group" "nat_instance" {
  name_prefix         = "${var.name_prefix}-nat-instance-"
  vpc_zone_identifier = var.public_subnet_ids
  desired_capacity    = var.enable_high_availability ? length(var.public_subnet_ids) : 1
  max_size            = var.enable_high_availability ? length(var.public_subnet_ids) : 1
  min_size            = 1
  health_check_type   = "EC2"
  health_check_grace_period = 60

  launch_template {
    id      = aws_launch_template.nat_instance.id
    version = "$Latest"
  }

  tag {
    key                 = "Name"
    value               = "${var.name_prefix}-nat-instance"
    propagate_at_launch = true
  }

  dynamic "tag" {
    for_each = var.tags
    content {
      key                 = tag.key
      value               = tag.value
      propagate_at_launch = true
    }
  }
}

# Disable source/destination check on NAT instances
resource "null_resource" "disable_source_dest_check" {
  depends_on = [aws_autoscaling_group.nat_instance]

  provisioner "local-exec" {
    command = <<-EOT
      # Wait for instance to be running
      sleep 30
      
      # Get instance IDs from ASG
      INSTANCE_IDS=$(aws autoscaling describe-auto-scaling-groups \
        --auto-scaling-group-names ${aws_autoscaling_group.nat_instance.name} \
        --query 'AutoScalingGroups[0].Instances[*].InstanceId' \
        --output text)
      
      # Disable source/dest check for each instance
      for INSTANCE_ID in $INSTANCE_IDS; do
        aws ec2 modify-instance-attribute \
          --instance-id $INSTANCE_ID \
          --no-source-dest-check
      done
    EOT
  }

  triggers = {
    asg_name = aws_autoscaling_group.nat_instance.name
  }
}
