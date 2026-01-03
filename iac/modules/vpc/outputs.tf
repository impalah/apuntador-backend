output "vpc_id" {
  value = aws_vpc.this.id
}

output "vpc_cidr_block" {
  description = "The CIDR block of the VPC"
  value       = aws_vpc.this.cidr_block
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = { for key, subnet in aws_subnet.private-subnet : key => subnet.id }
}

output "private_subnet_azs" {
  description = "AZs of the private subnets"
  value       = { for key, subnet in aws_subnet.private-subnet : key => subnet.availability_zone }
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = { for key, subnet in aws_subnet.public-subnet : key => subnet.id }
}

output "public_subnet_azs" {
  description = "AZs of the public subnets"
  value       = { for key, subnet in aws_subnet.public-subnet : key => subnet.availability_zone }
}

output "private_route_table_ids" {
  description = "IDs of the private route tables"
  value       = { for key, rt in aws_route_table.private-subnet-route-table : key => rt.id }
}

output "public_route_table_ids" {
  description = "IDs of the public route tables"
  value       = { for key, rt in aws_route_table.public-subnet-route-table : key => rt.id }
}

