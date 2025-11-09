output "vpc_id" {
  value = aws_vpc.this.id
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

