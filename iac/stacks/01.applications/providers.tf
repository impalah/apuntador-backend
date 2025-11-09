provider "aws" {
  region = var.region

  # default_tags {
  #   tags = {

  #     environment   = var.environment
  #     cost-center   = var.cost_center
  #     project       = var.project
  #     owner         = var.owner
  #     deployment    = lower("Terraform")
  #     creation-date = formatdate("YYYY-MM-DD", timestamp())

  #   }
  # }
  # ignore_tags {
  #   keys = ["cloud", "entorno", "plataforma", "suscripcion"]
  # }
}



