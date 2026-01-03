# NAT Instance Module

Cost-effective alternative to AWS NAT Gateway for providing internet connectivity to private subnets.

## Overview

This module deploys an EC2-based NAT instance as a cheaper alternative to AWS NAT Gateway:

- **NAT Gateway cost**: ~$32/month base + $0.045/GB (per AZ)
- **NAT Instance cost**: ~$3.50/month + $0.01/GB (t4g.nano)

**Savings: ~90% cost reduction** for low to moderate traffic workloads.

## Architecture

```
Internet
    ↓
Internet Gateway
    ↓
Public Subnet
    ↓
NAT Instance (t4g.nano) ← Auto Scaling Group
    ↓
Private Subnet(s)
    ↓
ECS Tasks / Lambda / etc.
```

## Features

- **Auto Scaling Group**: Automatic recovery if instance fails
- **ARM64 architecture**: t4g.nano instances (cheapest option)
- **SSM Session Manager**: Secure access without SSH keys
- **IMDSv2 enforced**: Enhanced security
- **CloudWatch integration**: Optional monitoring
- **High availability mode**: Deploy across multiple AZs (optional)

## Usage

```terraform
module "nat_instance" {
  source = "../../modules/nat-instance"
  
  name_prefix = "prod-myapp"
  vpc_id      = module.vpc.vpc_id
  
  public_subnet_ids = [
    module.vpc.public_subnet_ids["0"],
    module.vpc.public_subnet_ids["1"],
    module.vpc.public_subnet_ids["2"]
  ]
  
  private_subnet_cidrs = [
    "10.0.11.0/24",
    "10.0.12.0/24",
    "10.0.13.0/24"
  ]
  
  # Cost optimization
  instance_type            = "t4g.nano"
  enable_high_availability = false # Single instance
  
  tags = {
    Environment = "prod"
    Project     = "myapp"
  }
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| `name_prefix` | Prefix for resource names | `string` | - | yes |
| `vpc_id` | VPC ID where NAT instance will run | `string` | - | yes |
| `public_subnet_ids` | Public subnet IDs for NAT instance | `list(string)` | - | yes |
| `private_subnet_cidrs` | Private subnet CIDRs allowed to route through NAT | `list(string)` | - | yes |
| `instance_type` | EC2 instance type | `string` | `"t4g.nano"` | no |
| `enable_high_availability` | Deploy across multiple AZs | `bool` | `false` | no |
| `enable_cloudwatch_metrics` | Enable CloudWatch monitoring | `bool` | `true` | no |
| `enable_detailed_monitoring` | Enable 1-min CloudWatch metrics (extra cost) | `bool` | `false` | no |
| `ssh_allowed_cidr` | CIDR allowed to SSH (empty = disabled) | `string` | `""` | no |
| `tags` | Tags to apply to all resources | `map(string)` | `{}` | no |

## Outputs

| Name | Description |
|------|-------------|
| `nat_instance_ids` | NAT instance IDs |
| `nat_instance_security_group_id` | Security group ID for NAT instances |
| `autoscaling_group_name` | Auto Scaling Group name |

## Post-Deployment

After deployment, you need to add routes from private subnets to the NAT instance:

```bash
# Get NAT instance ENI ID
NAT_INSTANCE_ID=$(aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names <asg-name> \
  --query 'AutoScalingGroups[0].Instances[0].InstanceId' \
  --output text)

NAT_ENI_ID=$(aws ec2 describe-instances \
  --instance-ids $NAT_INSTANCE_ID \
  --query 'Reservations[0].Instances[0].NetworkInterfaces[0].NetworkInterfaceId' \
  --output text)

# Add route to private route table
aws ec2 create-route \
  --route-table-id <rtb-xxx> \
  --destination-cidr-block 0.0.0.0/0 \
  --network-interface-id $NAT_ENI_ID
```

This is automated in the parent stack with `null_resource.add_nat_routes`.

## Monitoring

Access the NAT instance via SSM Session Manager:

```bash
# Get instance ID
INSTANCE_ID=$(aws autoscaling describe-auto-scaling-groups \
  --auto-scaling-group-names <asg-name> \
  --query 'AutoScalingGroups[0].Instances[0].InstanceId' \
  --output text)

# Start session
aws ssm start-session --target $INSTANCE_ID
```

Check NAT functionality:

```bash
# Verify IP forwarding
sysctl net.ipv4.ip_forward

# Check iptables rules
iptables -t nat -L -n -v

# Monitor traffic
tcpdump -i eth0 -n
```

## Cost Comparison

### Single AZ

| Solution | Monthly Cost | Data Transfer (1TB) | Total |
|----------|--------------|---------------------|-------|
| **NAT Gateway** | $32.40 | $45.00 | **$77.40** |
| **NAT Instance (t4g.nano)** | $3.50 | $10.00 | **$13.50** |
| **Savings** | - | - | **82% ($63.90)** |

### Multi-AZ (3 AZs)

| Solution | Monthly Cost | Data Transfer (1TB) | Total |
|----------|--------------|---------------------|-------|
| **NAT Gateway (3x)** | $97.20 | $135.00 | **$232.20** |
| **NAT Instance HA (3x)** | $10.50 | $30.00 | **$40.50** |
| **Savings** | - | - | **83% ($191.70)** |

## When to Use NAT Instance vs NAT Gateway

### Use NAT Instance when:
- Traffic is low to moderate (< 5GB/day)
- Cost optimization is a priority
- OAuth/API calls to external services (low bandwidth)
- You can tolerate brief downtime during instance replacement

### Use NAT Gateway when:
- High traffic workload (> 100GB/day)
- Zero downtime requirement
- Managed service preference (no maintenance)
- Enterprise compliance requires AWS-managed services

## Limitations

- **Single point of failure** (unless enable_high_availability = true)
- **Performance**: t4g.nano limited to 5 Gbps burst
- **Maintenance**: Requires OS updates (automated via yum-cron)
- **Spot interruption**: Not recommended for Spot Instances in production

## Security

- Source/destination checks disabled (required for NAT)
- IMDSv2 enforced
- Automatic security updates enabled
- SSM Session Manager for access (no SSH keys)
- Security group restricts traffic to VPC CIDR only

## License

MIT
