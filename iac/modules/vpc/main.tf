
resource "aws_vpc" "this" {
  assign_generated_ipv6_cidr_block     = var.enable_ipv6
  cidr_block                           = var.cidr
  enable_dns_hostnames                 = var.enable_dns_hostnames
  enable_dns_support                   = var.enable_dns_support
  enable_network_address_usage_metrics = var.enable_network_address_usage_metrics
  instance_tenancy                     = var.instance_tenancy

  tags = merge(
    { "Name" = var.vpc_name },
    var.tags,
    var.vpc_tags,
  )
}

resource "aws_subnet" "private-subnet" {
  for_each                = { for idx, subnet in var.subnets_configuration : idx => subnet if subnet.subnet_type == "private" }
  availability_zone       = each.value.availability_zone
  cidr_block              = each.value.cidr_block
  vpc_id                  = aws_vpc.this.id
  map_public_ip_on_launch = false

  tags = merge(
    { "Name" = format("%s/%s", var.vpc_name, each.value.name) },
    var.tags,
    var.vpc_tags,
  )

}

resource "aws_subnet" "public-subnet" {
  for_each                = { for idx, subnet in var.subnets_configuration : idx => subnet if subnet.subnet_type == "public" }
  availability_zone       = each.value.availability_zone
  cidr_block              = each.value.cidr_block
  vpc_id                  = aws_vpc.this.id
  map_public_ip_on_launch = true

  tags = merge(
    { "Name" = format("%s/%s", var.vpc_name, each.value.name) },
    var.tags,
    var.vpc_tags,
  )

}

resource "aws_route_table" "private-subnet-route-table" {
  for_each = aws_subnet.private-subnet
  vpc_id   = aws_vpc.this.id

  tags = merge(
    { "Name" = format("%s/rt-private-%s", var.vpc_name, each.key) },
    var.tags,
    var.vpc_tags,
  )

}

resource "aws_route_table_association" "private-subnet-route-table-association" {
  for_each       = aws_subnet.private-subnet
  subnet_id      = each.value.id
  route_table_id = aws_route_table.private-subnet-route-table[each.key].id

}

resource "aws_route_table" "public-subnet-route-table" {
  for_each = aws_subnet.public-subnet
  vpc_id   = aws_vpc.this.id

  tags = merge(
    { "Name" = format("%s/rt-public-%s", var.vpc_name, each.key) },
    var.tags,
    var.vpc_tags,
  )

}

resource "aws_route_table_association" "public-subnet-route-table-association" {
  for_each       = aws_subnet.public-subnet
  subnet_id      = each.value.id
  route_table_id = aws_route_table.public-subnet-route-table[each.key].id

}

resource "aws_eip" "nat" {
  count = length(aws_subnet.private-subnet)
  # vpc   = true

  # TODO: Allow to specify the domain (variables.tf)
  domain = "vpc"

  tags = merge(
    { "Name" = format("%s/NAT-EIP%s", var.vpc_name, count.index + 1) },
    var.tags,
    var.vpc_tags,
  )

}





################################################################################
# Internet Gateway
################################################################################

resource "aws_internet_gateway" "internet-gateway" {

  tags = merge(
    { "Name" = format("%s/%s", var.vpc_name, "InternetGateway") },
    var.tags,
    var.vpc_tags,
  )

  vpc_id = aws_vpc.this.id

}


################################################################################
# NAT Gateway
################################################################################

# resource "aws_nat_gateway" "nat_gateway" {
#   for_each      = aws_subnet.private-subnet
#   allocation_id = aws_eip.nat[each.key].id
#   subnet_id     = each.value.id

#   tags = merge(
#     { "Name" = format("%s/%s", var.vpc_name, "NATGateway") },
#     var.tags,
#     var.vpc_tags,
#   )

#   depends_on = [aws_internet_gateway.internet-gateway]



# }





################################################################################
# ROUTES
################################################################################
resource "aws_route" "public-subnet" {
  for_each = aws_subnet.public-subnet
  # Everything to internet gateway
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.internet-gateway.id
  route_table_id         = aws_route_table.public-subnet-route-table[each.key].id
}

resource "aws_route" "private-subnet" {
  for_each = aws_subnet.private-subnet
  # Everything to NAT Gateway
  destination_cidr_block = "0.0.0.0/0"

  # TODO: delete on production
  nat_gateway_id = "nat-038adcbcba9cceb64"
  # nat_gateway_id         = aws_nat_gateway.nat_gateway[each.key].id

  route_table_id = aws_route_table.private-subnet-route-table[each.key].id

  lifecycle {
    ignore_changes = [
      nat_gateway_id
    ]
  }


}


