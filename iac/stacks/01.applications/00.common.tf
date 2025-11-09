#################################################################
# VPC and subnets
#################################################################




#################################################################
# Log group
#################################################################

# module "services_logs_group" {
#   source           = "../../modules/cloudwatch"
#   environment      = var.environment
#   project          = var.project
#   log_group_prefix = var.log_group_prefix
#   log_group_name   = var.log_group_name

#   tags = {
#     Environment = var.environment
#     CostCenter  = var.cost_center
#     Project     = var.project
#     Owner       = var.owner
#     Deployment  = lower("Terraform")
#     Date        = formatdate("YYYY-MM-DD", timestamp())
#   }

# }


